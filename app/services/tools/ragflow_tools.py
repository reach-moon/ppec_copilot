# app/services/tools/ragflow_tools.py
# import httpx
import logging
from langchain_core.tools import tool
from openai import OpenAI, APIError
from requests import Timeout

from config.settings import settings
from app.core.exceptions import PpecCopilotException, ServiceUnavailableException

logger = logging.getLogger(__name__)


@tool
async def ragflow_knowledge_search(query: str) -> str:
    """
    当需要回答关于 PPEC 平台相关的专业知识、操作指南、最佳实践等问题时，调用此工具从知识库中检索答案。
    """
    logger.info(f"Invoking RAGFlow tool with query: '{query}'")

    try:
        # 使用 OpenAI 兼容的客户端
        client = OpenAI(
            api_key=settings.RAGFLOW_API_KEY,
            base_url=settings.RAGFLOW_API_URL # 提取基础URL
        )
        
        # 发起请求
        completion = client.chat.completions.create(
            model="model",  # 使用默认模型
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query}
            ],
            stream=False,  # 不使用流式传输以简化处理
            extra_body={"reference": True},  # 请求引用信息
            timeout=60.0  # 设置超时时间
        )

        # 提取答案内容
        answer = completion.choices[0].message.content
        if not answer:
            logger.warning(f"RAGFlow returned a successful response but no content was found.")
            return "知识库中没有找到相关答案。"

        logger.info(f"RAGFlow tool successfully returned an answer：f{answer}")
        return answer

    except APIError as e:
        logger.error(f"RAGFlow service returned an API error: {e}")
        raise ServiceUnavailableException("知识问答服务暂时无法访问，请稍后再试。")
    except Timeout as e:
        logger.error(f"RAGFlow service timed out: {e}")
        raise ServiceUnavailableException("知识问答服务响应超时，请稍后再试。")
    except Exception as e:
        logger.critical(f"An unexpected error occurred in RAGFlow tool: {e}", exc_info=True)
        raise PpecCopilotException("调用知识问答服务时发生未知错误。")