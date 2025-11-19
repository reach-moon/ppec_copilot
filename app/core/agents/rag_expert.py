# app/core/agents/rag_expert.py
import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.schemas.graph_state import GraphState
from app.services.llm_service import get_llm
from app.services.tools.ragflow_tools import ragflow_knowledge_search
from app.core.exceptions import PpecCopilotException

logger = logging.getLogger(__name__)

# --- 新增：查询重写的 Prompt 和 Chain ---
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


async def run_rag_expert_logic(state: GraphState) -> str:
    """
    知识专家 Agent 的执行节点。
    它包含两个步骤：
    1. (如果需要) 利用对话历史重写用户问题，使其成为独立查询。
    2. 调用 RAGFlow Tool 来处理重写后的问题。

    RAG 专家的核心可复用逻辑。
    它只负责执行任务并返回结果字符串，不修改状态。
    """
    logger.info(">>> Executing RAG Expert...")
    user_input = state["user_input"]
    chat_history = state.get("messages", [])  # 从 state 获取历史消息

    final_query = user_input

    # 仅当存在对话历史时，才进行查询重写
    if chat_history:
        logger.info("Conversation history found. Rewriting query for RAGFlow.")
        try:
            # 异步调用查询重写链
            final_query = await query_rewrite_chain.ainvoke({
                "chat_history": "\n".join([f"{msg.type}: {msg.content}" for msg in chat_history]),
                "question": user_input
            })
            logger.info(f"Original query: '{user_input}' | Rewritten query: '{final_query}'")
        except Exception as e:
            logger.error(f"Failed to rewrite query, falling back to original. Error: {e}")
            final_query = user_input  # 如果重写失败，则使用原始问题
    else:
        logger.info("No conversation history. Using original query for RAGFlow.")

    try:
        # 使用最终确定的查询（可能是重写过的）来调用 RAGFlow 工具
        rag_output = await ragflow_knowledge_search.ainvoke({"query": final_query})

        return rag_output

    except PpecCopilotException as e:
        logger.error(f"A known exception occurred while running RAG Expert: {e.message}")
        return e.message

    except Exception as e:
        logger.critical(f"An unexpected error occurred in RAG Expert node: {e}", exc_info=True)
        error_message = "在处理您的知识问答时发生了意料之外的错误。"
        return error_message

async def run_rag_expert_node(state: GraphState) -> GraphState:
    """
    这是 LangGraph 的节点，它现在只是核心逻辑的一个包装器。
    """
    logger.info(">>> Executing RAG Expert Node (Standard Path)...")
    result = await run_rag_expert_logic(state)
    return {**state, "expert_output": result}