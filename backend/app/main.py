from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import init_db
from .logger import setup_logging
from .routers import admin, auth, chat, knowledge
from .services.cache import get_cache
from .services.errors import ProviderUnavailable


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="企业级多知识库 RAG 技术文档助手",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(knowledge.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    labels = {
        "username": "账号",
        "password": "密码",
        "confirm_password": "确认密码",
        "captcha_id": "图形验证码",
        "captcha_code": "图形验证码",
        "name": "名称",
        "content": "内容",
        "question": "问题",
    }
    messages = []
    for item in exc.errors():
        location = [str(part) for part in item.get("loc", []) if part != "body"]
        field = location[-1] if location else ""
        label = labels.get(field, field or "请求参数")
        error_type = item.get("type", "")
        if error_type == "string_too_short":
            messages.append(f"{label}至少需要 {item.get('ctx', {}).get('min_length', 8)} 个字符")
        elif error_type == "string_too_long":
            messages.append(f"{label}长度超过限制")
        elif error_type == "string_pattern_mismatch":
            messages.append(f"{label}格式不正确")
        elif error_type == "missing":
            messages.append(f"{label}不能为空")
        else:
            messages.append(f"{label}：{item.get('msg', '参数不合法')}")
    return JSONResponse(status_code=422, content={"detail": "；".join(dict.fromkeys(messages))})


@app.exception_handler(ProviderUnavailable)
async def provider_unavailable_handler(_: Request, exc: ProviderUnavailable) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "embedding_provider": settings.embedding_provider,
        "reranker_enabled": settings.reranker_enabled,
        "redis_available": get_cache().health(),
    }
