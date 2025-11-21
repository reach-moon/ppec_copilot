# app/services/tools/ragflow_tools.py
# import httpx
import logging
from typing import AsyncGenerator, List, Optional
from langchain_core.tools import tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from openai import OpenAI, AsyncOpenAI, APIError
from requests import Timeout

from config.settings import settings
from app.core.exceptions import PpecCopilotException, ServiceUnavailableException
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)

# --- 查询重写的 Prompt 和 Chain ---
rewrite_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """
    你是一个查询优化助手。你的任务是根据下面的对话历史，将用户的 '最新问题' 改写成一个独立的、无需额外上下文就能被理解的完整问题。
    如果 '最新问题' 本身已经是完整的，则无需改写，直接返回原问题即可。
    """),

    ("user",
    """
    这是对话历史:
    ---
    {chat_history}
    ---
    这是用户的最新问题: {question}
    
    请直接返回重写后的完整问题，不要包含任何额外的解释或前缀。
    """),
])

# 获取用于查询重写的 LLM
rewriter_llm = get_llm()
# 构建查询重写的链路
query_rewrite_chain = rewrite_prompt | rewriter_llm | StrOutputParser()


async def _rewrite_query(query: str, chat_history: Optional[List[dict]] = None) -> str:
    """
    重写查询以优化搜索结果
    
    Args:
        query (str): 原始查询
        chat_history (List[dict], optional): 对话历史
        
    Returns:
        str: 重写后的查询
    """
    final_query = query
    
    # 仅当存在对话历史时，才进行查询重写
    if chat_history and len(chat_history) > 0:
        logger.info("Conversation history found. Rewriting query for RAGFlow.")
        try:
            # 异步调用查询重写链
            final_query = await query_rewrite_chain.ainvoke({
                "chat_history": "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in chat_history]),
                "question": query
            })
            logger.info(f"Original query: '{query}' | Rewritten query: '{final_query}'")
        except Exception as e:
            logger.error(f"Failed to rewrite query, falling back to original. Error: {e}")
            final_query = query  # 如果重写失败，则使用原始问题
    else:
        logger.info("No conversation history. Using original query for RAGFlow.")
    
    return final_query


def _extract_content_from_delta(delta) -> str:
    """
    从 delta 对象中提取内容，支持 content 和 reasoning_content 字段
    
    Args:
        delta: OpenAI 的 delta 对象
        
    Returns:
        str: 提取的内容
    """
    content = ""
    if hasattr(delta, 'content') and delta.content:
        content = delta.content
    elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
        content = delta.reasoning_content
    return content


def _extract_content_from_message(message) -> str:
    """
    从 message 对象中提取内容，支持 content 和 reasoning_content 字段
    
    Args:
        message: OpenAI 的 message 对象
        
    Returns:
        str: 提取的内容
    """
    content = ""
    if hasattr(message, 'content') and message.content:
        content = message.content
    elif hasattr(message, 'reasoning_content') and message.reasoning_content:
        content = message.reasoning_content
    return content


@tool
async def ragflow_knowledge_search(query: str, chat_history: List[dict] = None) -> str:
    """
    当需要回答关于 PPEC 平台相关的专业知识、操作指南、最佳实践等问题时，调用此工具从知识库中检索答案。
    
    Args:
        query (str): 用户的查询问题
        chat_history (List[dict], optional): 对话历史，用于优化查询
    """
    logger.info(f"Invoking RAGFlow tool with query: '{query}'")
    
    # 重写查询
    final_query = await _rewrite_query(query, chat_history)

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
                {
                    "role": "system", 
                    "content": "You are a professional technical assistant. Please provide concise and clear answers. When searching for information, do not display your search process or intermediate thoughts. Provide only the final polished answer. If you need to reference sources, include them at the end of your response in a separate section called 'References'."
                },
                {"role": "user", "content": final_query}
            ],
            stream=False,  # 不使用流式传输以简化处理
            extra_body={"reference": True},  # 请求引用信息
            timeout=60.0  # 设置超时时间
        )

        # 提取答案内容
        answer = _extract_content_from_message(completion.choices[0].message)
        if not answer:
            logger.warning(f"RAGFlow returned a successful response but no content was found.")
            return "知识库中没有找到相关答案。"

        logger.info(f"RAGFlow tool successfully returned an answer：{answer[:100]}...")
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


async def ragflow_stream_search(query: str, chat_history: List[dict] = None) -> AsyncGenerator[str, None]:
    """
    流式版本的 RAGFlow 知识搜索工具
    
    Args:
        query (str): 用户的查询问题
        chat_history (List[dict], optional): 对话历史，用于优化查询
    """
    logger.info(f"Invoking RAGFlow streaming tool with query: '{query}'")
    
    # 重写查询
    final_query = await _rewrite_query(query, chat_history)

    try:
        # 使用异步 OpenAI 兼容的客户端
        client = AsyncOpenAI(
            api_key=settings.RAGFLOW_API_KEY,
            base_url=settings.RAGFLOW_API_URL
        )
        
        # 发起流式请求
        completion = await client.chat.completions.create(
            model="model",  # 使用默认模型
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional technical assistant. Please provide concise and clear answers. When searching for information, do not display your search process or intermediate thoughts. Provide only the final polished answer. If you need to reference sources, include them at the end of your response in a separate section called 'References'."
                },
                {"role": "user", "content": final_query}
            ],
            stream=True,  # 启用流式传输
            extra_body={"reference": True},  # 请求引用信息
            timeout=60.0  # 设置超时时间
        )

        # 流式传输响应
        async for chunk in completion:
            # 提取内容
            if chunk.choices and chunk.choices[0].delta:
                content = _extract_content_from_delta(chunk.choices[0].delta)
                if content:
                    yield content
                    
    except APIError as e:
        logger.error(f"RAGFlow service returned an API error: {e}")
        yield "知识问答服务暂时无法访问，请稍后再试。"
    except Timeout as e:
        logger.error(f"RAGFlow service timed out: {e}")
        yield "知识问答服务响应超时，请稍后再试。"
    except Exception as e:
        logger.critical(f"An unexpected error occurred in RAGFlow streaming tool: {e}", exc_info=True)
        yield "调用知识问答服务时发生未知错误。"