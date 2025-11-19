# app/core/mem0_client.py
import logging
import os
from mem0 import Memory
from functools import lru_cache
from config.settings import get_settings

logger = logging.getLogger(__name__)

class Mem0ClientSingleton:
    """
    Mem0 客户端单例类
    """
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Mem0ClientSingleton, cls).__new__(cls)
            # 初始化 Mem0 客户端
            try:
                settings = get_settings()
                
                # 设置环境变量以供 Mem0 使用
                os.environ['OPENAI_API_KEY'] = settings.ONE_API_EMBEDDING_KEY
                os.environ['OPENAI_BASE_URL'] = settings.ONE_API_BASE_URL
                
                # 构建 Mem0 配置
                config = {
                    "llm": {
                        "provider": "openai",
                        "config": {
                            "model": settings.ONE_API_MODEL,
                            "temperature": 0.2,
                            "max_tokens": 20000,
                        },
                    },
                    "embedder": {
                        "provider": "openai",
                        "config": {
                            "model": settings.ONE_API_EMBEDDING_MODEL,
                            "embedding_dims": settings.ONE_API_EMBEDDING_DIMS,
                        },
                    },
                    "vector_store": {
                        "provider": settings.MEM_0_VECTOR_STORE_PROVIDER,
                        "config": {
                            "host": settings.MEM_0_VECTOR_STORE_HOST,
                            "port": settings.MEM_0_VECTOR_STORE_PORT,
                        }
                    },
                    "version": "v1.1"
                }
                
                cls._client = Memory.from_config(config)
                logger.info("Mem0 client initialized successfully with configuration.")
            except Exception as e:
                logger.error(f"Failed to initialize Mem0 client: {e}", exc_info=True)
                cls._client = None
        return cls._instance

    def get_client(self):
        """
        获取 Mem0 客户端实例
        """
        return self._client

@lru_cache(maxsize=1)
def get_mem0_client():
    """
    获取 Mem0 客户端实例的缓存函数（单例模式）
    
    Returns:
        Memory: 配置好的 Mem0 客户端实例
    """
    singleton = Mem0ClientSingleton()
    return singleton.get_client()