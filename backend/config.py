"""部署配置；所有模型和数据路径均可通过环境变量替换。"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_MODEL_NAME = "tencent/Hunyuan-1.8B-Instruct"
DEFAULT_TOKENIZER_DIRECTORY = "models/Hunyuan-1.8B-Instruct"


@dataclass(frozen=True)
class Settings:
    root: Path
    data: Path
    embedding_model: Path
    reranker_model: Path
    model_url: str = "http://127.0.0.1:18301/v1"
    model_name: str = DEFAULT_MODEL_NAME
    tokenizer_path: Optional[Path] = None

    @classmethod
    def load(cls):
        root = Path(__file__).resolve().parents[1]
        models = root.parent / "rag-lab/models"
        return cls(
            root=root,
            data=Path(os.getenv("CAPSTONE_DATA", str(root / "data"))),
            embedding_model=Path(
                os.getenv("CAPSTONE_EMBEDDING", str(models / "bge-small-zh-v1.5"))
            ),
            reranker_model=Path(
                os.getenv("CAPSTONE_RERANKER", str(models / "bge-reranker-base"))
            ),
            model_url=os.getenv("CAPSTONE_MODEL_URL", "http://127.0.0.1:18301/v1"),
            model_name=os.getenv("CAPSTONE_MODEL_NAME", DEFAULT_MODEL_NAME),
            tokenizer_path=Path(
                os.getenv(
                    "CAPSTONE_TOKENIZER",
                    str(root.parent / DEFAULT_TOKENIZER_DIRECTORY),
                )
            ),
        )
