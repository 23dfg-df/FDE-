"""FastAPI 边界：输入验证和路由；计算与持久化分别由服务层负责。"""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Settings
from .indexing import Index
from .repository import Repository, now
from .services import ModelAvailabilityError, Service


class Query(BaseModel):
    question: str = Field(min_length=1, max_length=600)
    mode: Literal["bm25", "dense", "hybrid"] = "hybrid"
    top_k: int = Field(default=5, ge=1, le=8)
    rerank: bool = False


class DocumentInput(BaseModel):
    name: str = Field(min_length=4, max_length=104)
    text: str = Field(min_length=1, max_length=100000)


class AskQuery(Query):
    structured: bool = True


class TriageInput(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    model: Literal["base", "incident-triage"] = "base"


class EvaluationInput(BaseModel):
    split: Literal["dev", "test", "all"] = "dev"
    limit: int = Field(default=5, ge=1, le=50)
    mode: Literal["bm25", "dense", "hybrid"] = "hybrid"
    rerank: bool = False


def create_app(settings=None, supplied_service=None):
    configuration = settings or Settings.load()

    @asynccontextmanager
    async def lifespan(app):
        app.state.service = supplied_service or Service(
            configuration, Repository(configuration.data), Index(configuration)
        )
        yield
        # 评测为有界串行任务，重启中断会在读取记录时明确标注。
        for job in app.state.service.jobs.values():
            job["cancel_requested"] = True

    app = FastAPI(title="FDE Capstone — Haystack × vLLM", lifespan=lifespan)

    @app.exception_handler(ValueError)
    async def invalid(request, error):
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @app.exception_handler(RuntimeError)
    async def unavailable(request, error):
        return JSONResponse(status_code=502, content={"detail": str(error)})

    @app.exception_handler(ModelAvailabilityError)
    async def model_unavailable(request, error):
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": str(error), "code": error.code},
        )

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/status")
    def status(request: Request):
        return request.app.state.service.status()

    @app.get("/api/documents")
    def documents(request: Request):
        return {"items": request.app.state.service.index.documents()}

    @app.post("/api/documents", status_code=201)
    def add_document(body: DocumentInput, request: Request):
        service = request.app.state.service
        with service.operation_lock:
            if service.active_job():
                raise HTTPException(409, "评测进行中，请完成后再变更资料")
            try:
                return service.index.add(body.name, body.text)
            except FileExistsError:
                raise HTTPException(
                    409, "同名文件已存在，请使用新的版本文件名"
                ) from None

    @app.post("/api/reindex")
    def reindex(request: Request):
        service = request.app.state.service
        with service.operation_lock:
            if service.active_job():
                raise HTTPException(409, "评测进行中，索引版本已锁定")
            result = service.index.rebuild()
            service.repository.save("index", result)
            return result

    @app.post("/api/retrieve")
    def retrieve(body: Query, request: Request):
        return request.app.state.service.index.retrieve(**body.model_dump())

    @app.post("/api/ask")
    def ask(body: AskQuery, request: Request):
        return request.app.state.service.ask(**body.model_dump())

    @app.get("/api/history")
    def history(request: Request):
        return {"items": request.app.state.service.repository.list()}

    @app.post("/api/triage")
    def triage(body: TriageInput, request: Request):
        return request.app.state.service.triage(**body.model_dump())

    @app.get("/api/evaluation/questions")
    def questions(request: Request):
        return {"items": request.app.state.service.questions()}

    @app.post("/api/evaluation/start", status_code=202)
    def start_evaluation(body: EvaluationInput, request: Request):
        return request.app.state.service.start_evaluation(**body.model_dump())

    @app.get("/api/evaluation/jobs/{job_id}")
    def evaluation(job_id: str, request: Request):
        try:
            return request.app.state.service.evaluation(job_id)
        except FileNotFoundError:
            raise HTTPException(404, "评测记录不存在") from None

    @app.post("/api/evaluation/jobs/{job_id}/cancel")
    def cancel(job_id: str, request: Request):
        service = request.app.state.service
        with service.job_lock:
            job = service.jobs.get(job_id)
            if not job:
                raise HTTPException(404, "没有正在运行的评测")
            job["cancel_requested"] = True
        return {"id": job_id, "status": "cancelling", "note": "当前问题结束后停止"}

    @app.get("/api/evidence")
    def evidence(request: Request):
        return request.app.state.service.evidence()

    @app.get("/api/export")
    def export(request: Request):
        service = request.app.state.service
        return {
            "exported_at": now(),
            "history": service.repository.list(limit=10000),
            "documents": service.index.documents(),
            "index_version": service.index.version,
            "evidence": service.evidence()["items"],
        }

    @app.get("/api/download/{artifact}")
    def download(artifact: Literal["offline", "package", "adapter"]):
        locations = {
            "offline": configuration.root / "outputs/FDE完整项目-离线学习版.html",
            "package": configuration.root
            / "outputs/FDE开源知识库与模型部署-完整实验包.zip",
            "adapter": configuration.root
            / "evidence/training/ticket-qlora-20261115/ticket-adapter.zip",
        }
        path = locations[artifact]
        if not path.is_file():
            raise HTTPException(404, "交付文件尚未打包，请先运行打包脚本")
        return FileResponse(path, filename=path.name)

    app.mount(
        "/",
        StaticFiles(directory=configuration.root / "web", html=True, check_dir=False),
        name="web",
    )
    return app


app = create_app()
