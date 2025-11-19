# tests/conftest.py
import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Generator
from fastapi.testclient import TestClient
from app.api.main import app

@pytest.fixture(scope="function")
def client() -> Generator:
    """
    创建一个用于测试的同步 HTTP 客户端
    """
    with TestClient(app) as c:
        yield c