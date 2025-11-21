# config/settings.py
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    应用配置模型
    pydantic-settings 会自动从环境变量和 .env 文件中读取配置
    """
    # --- 应用基础配置 ---
    APP_ENV: str = "development"
    PROJECT_NAME: str = "PPEC Copilot"
    API_V1_PREFIX: str = "/api/v1"

    # --- LLM 服务 (one-api) 配置 ---
    ONE_API_BASE_URL: str
    ONE_API_KEY: str
    ONE_API_MODEL: str
    ONE_API_EMBEDDING_KEY: str
    ONE_API_EMBEDDING_MODEL: str
    ONE_API_EMBEDDING_DIMS: int

    # --- Mem0 记忆服务配置 ---
    MEM_0_VECTOR_STORE_PROVIDER: str
    MEM_0_VECTOR_STORE_HOST: str
    MEM_0_VECTOR_STORE_PORT: int

    GRAPH_STORE: str
    GRAPH_STORE_URL: str
    GRAPH_STORE_USER: str
    GRAPH_STORE_PASSWORD: str

    # --- RAGFlow 服务配置 ---
    RAGFLOW_API_URL: str
    RAGFLOW_API_KEY: str

    # --- 日志配置 ---
    LOG_LEVEL: str = "INFO"

    # 模型配置，告诉 pydantic-settings 从 .env 文件加载
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding='utf-8',
        extra='ignore'  # 忽略额外的字段，这样就不会因为 Gunicorn 配置而报错
    )

@lru_cache
def get_settings() -> Settings:
    """
    获取配置实例，使用 lru_cache 确保全局只有一个实例（单例模式）
    """
    return Settings()

# 全局可用的配置实例
settings = get_settings()