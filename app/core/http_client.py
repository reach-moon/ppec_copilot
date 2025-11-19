# app/core/http_client.py
from contextlib import asynccontextmanager
import httpx
from typing import AsyncGenerator

# 使用一个字典来持有客户端实例，实现单例模式
_clients = {}

@asynccontextmanager
async def lifespan(app):
    """
    FastAPI 的生命周期事件管理器。
    应用启动时创建客户端，应用关闭时关闭客户端。
    """
    # 应用启动
    _clients["default"] = httpx.AsyncClient(timeout=30.0)
    yield
    # 应用关闭
    await _clients["default"].aclose()

def get_http_client() -> httpx.AsyncClient:
    """
    依赖注入函数，用于在 API 路由中获取全局 HTTP 客户端。
    """
    return _clients["default"]