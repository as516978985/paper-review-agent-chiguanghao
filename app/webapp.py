from __future__ import annotations

import asyncio
import json

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .agent import ReviewAgent
from .config import settings
from .docx_tools import extract_text, inspect_document
from .mcp_client import McpClient
from .memory import MemoryStore
from .skill_runtime import SkillRuntime

memory = MemoryStore(
    settings.mysql_host,
    settings.mysql_port,
    settings.mysql_user,
    settings.mysql_password,
    settings.mysql_database,
)
memory_health = {"ok": False}
mcp_tools: list[dict] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global memory_health, mcp_tools
    try:
        memory_health = await memory.initialize()
    except Exception as exc:
        memory_health = {"ok": False, "detail": str(exc)}
    try:
        async with McpClient(settings.mcp_server) as client:
            mcp_tools = client.tools
    except Exception as exc:
        mcp_tools = [{"name": "连接失败", "description": str(exc)}]
    yield


app = FastAPI(title="论文规范审核 Agent", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(settings.static_dir / "index.html")


@app.get("/api/health")
async def health() -> JSONResponse:
    ok = bool(memory_health.get("ok")) and bool(mcp_tools)
    return JSONResponse({
        "status": "ok" if ok else "degraded",
        "model": settings.llm_model,
        "memory": memory_health,
        "mcp_tools": [item["name"] for item in mcp_tools],
    })


@app.get("/api/config")
async def config() -> JSONResponse:
    format_skill = SkillRuntime(settings.format_skill, "read_format_skill_file")
    citation_skill = SkillRuntime(
        settings.citation_skill, "read_citation_skill_file", with_ratio=True
    )
    return JSONResponse({
        "model": settings.llm_model,
        "mcp_tools": mcp_tools,
        "skills": [
            {"name": format_skill.name, "files": format_skill.files()},
            {"name": citation_skill.name, "files": citation_skill.files()},
        ],
        "memory": memory_health,
    })


@app.post("/api/upload-docx")
async def upload_docx(file: UploadFile) -> JSONResponse:
    if not file.filename or not file.filename.lower().endswith(".docx"):
        return JSONResponse({"error": "只接收 DOCX 文件"}, status_code=400)
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        return JSONResponse({"error": "文件不得超过 10 MB"}, status_code=400)
    try:
        text = extract_text(data)
        analysis = inspect_document(data, settings.format_policy)
        return JSONResponse({
            "filename": file.filename,
            "text": text,
            "format_analysis": analysis,
        })
    except Exception as exc:
        return JSONResponse({"error": f"DOCX 解析失败：{exc}"}, status_code=400)


@app.post("/api/review")
async def review(request: Request) -> StreamingResponse:
    payload = await request.json()
    document_text = str(payload.get("text", ""))
    format_analysis = payload.get("format_analysis") or {}
    review_year = int(payload.get("review_year") or settings.review_year)

    async def stream():
        queue: asyncio.Queue = asyncio.Queue()

        async def emit(event: dict) -> None:
            await queue.put(event)

        async def work() -> None:
            try:
                agent = ReviewAgent(
                    document_text, format_analysis, review_year, memory, emit
                )
                await agent.run()
            except Exception as exc:
                await emit({"type": "error", "detail": str(exc)})
            finally:
                await queue.put(None)

        task = asyncio.create_task(work())
        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        await task

    return StreamingResponse(stream(), media_type="text/event-stream")