"""用 Haystack 检索组件复现 BM25、向量检索和 RRF 混合检索。"""

import hashlib
import json
import math
import re
import shutil
import threading
import time

from .repository import atomic_json, now


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def model_identity(path):
    files = {}
    for file in sorted(path.rglob("*")):
        if file.is_file() and file.suffix in {
            ".json",
            ".txt",
            ".safetensors",
            ".model",
        }:
            checksum = hashlib.sha256()
            with file.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    checksum.update(block)
            files[str(file.relative_to(path))] = checksum.hexdigest()
    return {"path": str(path), "files": files}


def safe_name(name):
    if not re.fullmatch(
        r"[\w\-.\u4e00-\u9fff ]{1,100}\.(md|txt)", name
    ) or name.startswith("."):
        raise ValueError("文件名须为简单的 .md 或 .txt 名称，不能包含路径")
    return name


def split_document(name, text, max_chars=420, overlap=60):
    """按标题分段，再做有重叠的字符窗口；每块保留来源和行号。"""
    if max_chars < 100 or overlap < 0 or overlap >= max_chars:
        raise ValueError("切分参数无效")
    lines = text.splitlines(keepends=True)
    sections, current, start, title = [], [], 1, name
    for number, line in enumerate(lines, 1):
        if line.startswith("#") and current:
            sections.append((start, title, "".join(current)))
            current, start = [], number
        if line.startswith("#"):
            title = line.lstrip("# ").strip()
        current.append(line)
    if current:
        sections.append((start, title, "".join(current)))
    chunks = []
    for start, title, section in sections:
        offset = 0
        while offset < len(section):
            block = section[offset : offset + max_chars]
            if block.strip():
                first = start + section[:offset].count("\n")
                chunks.append(
                    {
                        "id": f"{name}#{len(chunks) + 1:03d}-{digest(block)[:8]}",
                        "source": name,
                        "title": title,
                        "text": block,
                        "start_line": first,
                        "end_line": first + block.rstrip("\n").count("\n"),
                    }
                )
            if offset + max_chars >= len(section):
                break
            offset += max_chars - overlap
    return chunks


class LocalModels:
    def __init__(self, embedding_path, reranker_path):
        import torch
        from transformers import (
            AutoModel,
            AutoModelForSequenceClassification,
            AutoTokenizer,
        )

        torch.set_num_threads(4)
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            embedding_path, local_files_only=True, trust_remote_code=False
        )
        self.encoder = AutoModel.from_pretrained(
            embedding_path,
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
        ).eval()
        self.rank_tokenizer = AutoTokenizer.from_pretrained(
            reranker_path, local_files_only=True, trust_remote_code=False
        )
        self.ranker = AutoModelForSequenceClassification.from_pretrained(
            reranker_path,
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
        ).eval()

    def embed(self, texts, query=False):
        output = []
        for offset in range(0, len(texts), 8):
            batch = texts[offset : offset + 8]
            if query:
                batch = [
                    "为这个句子生成表示以用于检索相关文章：" + text for text in batch
                ]
            tokens = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            with self.torch.inference_mode():
                vectors = self.encoder(**tokens).last_hidden_state[:, 0]
                output.extend(
                    self.torch.nn.functional.normalize(vectors, p=2, dim=1)
                    .float()
                    .tolist()
                )
        return output

    def rerank(self, question, chunks):
        scores = []
        for offset in range(0, len(chunks), 4):
            pairs = [[question, chunk["text"]] for chunk in chunks[offset : offset + 4]]
            tokens = self.rank_tokenizer(
                pairs,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            with self.torch.inference_mode():
                scores.extend(self.ranker(**tokens).logits.reshape(-1).float().tolist())
        return sorted(
            [
                {
                    **chunk,
                    "retrieval_score": chunk["score"],
                    "rerank_score": float(score),
                    "score": float(score),
                }
                for chunk, score in zip(chunks, scores)
            ],
            key=lambda x: x["score"],
            reverse=True,
        )


class Index:
    def __init__(self, settings, models=None):
        self.settings = settings
        self.lock = threading.RLock()
        self.documents_dir = settings.data / "documents"
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        marker = settings.data / "corpus-initialized.json"
        if not marker.exists():
            for source in sorted((settings.root / "corpus").glob("*.md")):
                if not (self.documents_dir / source.name).exists():
                    shutil.copy2(source, self.documents_dir / source.name)
            atomic_json(marker, {"created_at": now()})
        self.models = models or LocalModels(
            settings.embedding_model, settings.reranker_model
        )
        self.embedding_identity = model_identity(settings.embedding_model)
        self.version, self.chunks, self.pipelines = "", [], {}
        self.rebuild()

    def documents(self):
        output = []
        for path in sorted(self.documents_dir.iterdir()):
            if path.suffix not in {".md", ".txt"} or not path.is_file():
                continue
            text = path.read_text("utf-8")
            title = next(
                (x.lstrip("# ") for x in text.splitlines() if x.startswith("#")),
                path.name,
            )
            output.append(
                {"id": path.name, "title": title, "text": text, "sha256": digest(text)}
            )
        return output

    def add(self, name, text):
        name = safe_name(name)
        with self.lock:
            path = self.documents_dir / name
            with path.open("x", encoding="utf-8") as stream:
                stream.write(text)
        return {"id": name, "sha256": digest(text), "indexed": False}

    def _pipelines(self, chunks):
        from haystack import Document, Pipeline
        from haystack.components.joiners import DocumentJoiner
        from haystack.components.retrievers.in_memory import (
            InMemoryBM25Retriever,
            InMemoryEmbeddingRetriever,
        )
        from haystack.document_stores.in_memory import InMemoryDocumentStore

        store = InMemoryDocumentStore(
            embedding_similarity_function="cosine",
            bm25_tokenization_regex=r"[\u4e00-\u9fff]|[a-zA-Z0-9_/-]+",
            return_embedding=False,
        )
        store.write_documents(
            [
                Document(
                    id=x["id"],
                    content=x["text"],
                    meta={
                        k: v
                        for k, v in x.items()
                        if k not in {"id", "text", "embedding"}
                    },
                    embedding=x["embedding"],
                )
                for x in chunks
            ]
        )
        pipelines = {}
        for mode in ("bm25", "dense", "hybrid"):
            pipeline = Pipeline()
            if mode in {"bm25", "hybrid"}:
                pipeline.add_component(
                    "bm25", InMemoryBM25Retriever(document_store=store)
                )
            if mode in {"dense", "hybrid"}:
                pipeline.add_component(
                    "dense", InMemoryEmbeddingRetriever(document_store=store)
                )
            if mode == "hybrid":
                pipeline.add_component(
                    "fusion", DocumentJoiner(join_mode="reciprocal_rank_fusion")
                )
                pipeline.connect("bm25.documents", "fusion.documents")
                pipeline.connect("dense.documents", "fusion.documents")
            pipelines[mode] = pipeline
        return pipelines

    def rebuild(self):
        with self.lock:
            documents = self.documents()
            if not documents:
                raise ValueError("至少需要一份知识库文档")
            spec = {
                "documents": [
                    {"id": x["id"], "sha256": x["sha256"]} for x in documents
                ],
                "chunk_chars": 420,
                "overlap": 60,
                "embedding_model": self.embedding_identity,
                "schema": 1,
            }
            version = digest(json.dumps(spec, sort_keys=True, ensure_ascii=False))[:20]
            path = self.settings.data / "indexes" / f"{version}.json"
            expected_chunks = [
                chunk
                for document in documents
                for chunk in split_document(document["id"], document["text"])
            ]
            chunks = None
            if path.exists():
                try:
                    saved = json.loads(path.read_text("utf-8"))
                    candidate = saved["chunks"]
                    content = [
                        {k: v for k, v in chunk.items() if k != "embedding"}
                        for chunk in candidate
                    ]
                    serialized = json.dumps(
                        candidate, sort_keys=True, ensure_ascii=False
                    )
                    vectors = [chunk["embedding"] for chunk in candidate]
                    vector_valid = (
                        bool(vectors)
                        and len(vectors[0]) > 0
                        and all(
                            len(vector) == len(vectors[0])
                            and all(
                                isinstance(value, (float, int)) and math.isfinite(value)
                                for value in vector
                            )
                            for vector in vectors
                        )
                    )
                    if (
                        saved["version"] == version
                        and saved["spec"] == spec
                        and saved["documents"] == documents
                        and content == expected_chunks
                        and digest(serialized) == saved.get("integrity_sha256")
                        and vector_valid
                    ):
                        chunks = candidate
                except (ValueError, KeyError, TypeError, AttributeError):
                    pass
            if chunks is None:
                chunks = expected_chunks
                embeddings = self.models.embed([x["text"] for x in chunks])
                if len(embeddings) != len(chunks):
                    raise ValueError("向量数量与片段数量不同")
                for chunk, embedding in zip(chunks, embeddings):
                    chunk["embedding"] = embedding
                atomic_json(
                    path,
                    {
                        "version": version,
                        "spec": spec,
                        "created_at": now(),
                        "documents": documents,
                        "chunks": chunks,
                        "integrity_sha256": digest(
                            json.dumps(chunks, sort_keys=True, ensure_ascii=False)
                        ),
                    },
                )
            pipelines = self._pipelines(chunks)
            for mode, pipeline in pipelines.items():
                destination = self.settings.data / "pipelines" / f"{mode}.yaml"
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(pipeline.dumps(), "utf-8")
            atomic_json(
                self.settings.data / "active-index.json",
                {
                    "version": version,
                    "documents": len(documents),
                    "chunks": len(chunks),
                },
            )
            self.version, self.chunks, self.pipelines = version, chunks, pipelines
            return {
                "version": version,
                "documents": len(documents),
                "chunks": len(chunks),
            }

    def retrieve(self, question, mode="hybrid", top_k=5, rerank=False):
        if mode not in {"bm25", "dense", "hybrid"}:
            raise ValueError("未知检索模式")
        with self.lock:
            start = time.perf_counter()
            inputs = {}
            candidates = max(top_k, 10) if rerank else top_k
            if mode in {"bm25", "hybrid"}:
                inputs["bm25"] = {"query": question, "top_k": candidates}
            if mode in {"dense", "hybrid"}:
                inputs["dense"] = {
                    "query_embedding": self.models.embed([question], query=True)[0],
                    "top_k": candidates,
                }
            embedded = time.perf_counter()
            if mode == "hybrid":
                inputs["fusion"] = {"top_k": candidates}
            result = self.pipelines[mode].run(inputs)
            output = result["fusion" if mode == "hybrid" else mode]["documents"]
            chunks = [
                {"id": x.id, "text": x.content, **x.meta, "score": float(x.score or 0)}
                for x in output
            ]
            retrieved = time.perf_counter()
            if rerank and chunks:
                chunks = self.models.rerank(question, chunks)
            end = time.perf_counter()
            return {
                "chunks": chunks[:top_k],
                "mode": mode,
                "rerank": rerank,
                "index_version": self.version,
                "timings": {
                    "embedding_seconds": round(embedded - start, 4),
                    "retrieval_seconds": round(retrieved - embedded, 4),
                    "rerank_seconds": round(end - retrieved, 4),
                    "total_seconds": round(end - start, 4),
                },
            }
