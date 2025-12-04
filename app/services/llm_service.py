# app/services/llm_service.py

from functools import lru_cache
from langchain_openai import ChatOpenAI

from config.settings import settings

@lru_cache
def get_llm(model_name: str = None) -> ChatOpenAI:
    """
    获取一个配置好的 ChatOpenAI 实例。
    使用 lru_cache 确保在整个应用生命周期中只有一个 LLM 客户端实例。
    这对于复用底层 HTTP 连接非常重要。
    
    Args:
        model_name (str, optional): 模型名称，如果未提供则使用默认设置
    """
    model = model_name if model_name else settings.ONE_API_MODEL
    
    return ChatOpenAI(
        model=model,  # 使用配置的模型或指定的模型
        base_url=settings.ONE_API_BASE_URL,
        api_key=settings.ONE_API_KEY,
        temperature=0,
        max_retries=2, # 可选：增加重试
    )

@lru_cache
def get_embedding() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.ONE_API_EMBEDDING_MODEL,  # 使用配置的模型
        base_url=settings.ONE_API_BASE_URL,
        api_key=settings.ONE_API_EMBEDDING_KEY,
    )