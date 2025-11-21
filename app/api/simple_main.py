# 简化版的 FastAPI 应用入口，用于调试
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI
from contextlib import asynccontextmanager

# Import the chat router
from app.api.endpoints.v1.chat import router as chat_router

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")

# 创建简单的 FastAPI 实例
app = FastAPI(
    title="PPEC Copilot Debug",
    lifespan=lifespan,
)

# Include the chat routes
app.include_router(chat_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")