# app/api/main.py
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from app.api.endpoints.v1 import chat
from app.core.logging_config import setup_logging
from app.core.http_client import lifespan as http_lifespan
from app.core.exceptions import ServiceUnavailableException, InvalidInputException
from app.api.exception_handlers import service_unavailable_handler, invalid_input_handler, generic_exception_handler
from config.settings import settings

# 在应用启动时配置日志
setup_logging()
logger = logging.getLogger(__name__)

# 将多个生命周期管理器合并
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件
    async with http_lifespan(app):
        logger.info(f"--- {settings.PROJECT_NAME} Application Startup ---")
        yield
    # 关闭事件
    logger.info(f"--- {settings.PROJECT_NAME} Application Shutdown ---")

# 创建 FastAPI 实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

# 注册全局异常处理器
app.add_exception_handler(ServiceUnavailableException, service_unavailable_handler)
app.add_exception_handler(InvalidInputException, invalid_input_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# 包含 API 路由
app.include_router(chat.router, prefix=settings.API_V1_PREFIX, tags=["Chat"])

# 提供静态文件服务
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
    
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 提供前端页面
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root():
    chat_html_path = os.path.join(static_dir, "chat.html")
    if os.path.exists(chat_html_path):
        with open(chat_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    else:
        return HTMLResponse(content="<h1>Page not found</h1><p>chat.html not found</p>", status_code=404)

@app.get("/health", tags=["Health Check"])
async def health_check():
    """健康检查接口"""
    return {"status": "ok"}