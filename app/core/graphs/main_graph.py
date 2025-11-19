import logging
from functools import lru_cache
from langgraph.graph import StateGraph, END

from app.schemas.graph_state import GraphState
from app.core.agents.hierarchical_planner import (
    retrieve_memory_step,
    plan_step,
    execute_step,
    replan_step,
    summarize_step,
    update_memory_step,
    should_continue,
)

logger = logging.getLogger(__name__)


def create_workflow() -> StateGraph:
    """
    创建并配置 PPEC Copilot 的核心 LangGraph 工作流。

    这个工作流实现了一个“分层规划与执行”的 Agent 架构。
    它不是一个固定的线性流程，而是一个动态的状态机，其路径由 `should_continue` 函数在每个关键点进行决策。

    工作流的主要路径如下：
    1.  **retrieve_memory**: 获取历史对话作为上下文。
    2.  **plan_step**: 根据用户目标和历史，生成一个详细的步骤计划 (Plan)。
    3.  **execute_step**: 执行计划中的下一个待办步骤。
    4.  **should_continue (决策点)**:
        - 如果有步骤失败，则转到 `replan_step` 进行自我修正。
        - 如果所有步骤都已成功，则转到 `summarize_step` 进行总结。
        - 如果计划仍在进行中，则循环回到 `execute_step` 执行下一步。
    5.  **replan_step**: 当执行失败时，重新制定计划。
    6.  **summarize_step**: 在计划成功完成后，生成对用户友好的最终回复。
    7.  **update_memory_step**: 将完成的交互（Plan）存入长期记忆。
    8.  **END**: 流程结束。

    Returns:
        一个已编译的、可执行的 LangGraph 应用实例。
    """
    logger.info("正在创建 LangGraph 工作流...")

    # 1. 初始化状态图
    workflow = StateGraph(GraphState)

    # 2. 添加所有业务逻辑节点
    logger.debug("添加工作流节点...")
    workflow.add_node("retrieve_memory", retrieve_memory_step)
    workflow.add_node("plan_step", plan_step)
    workflow.add_node("execute_step", execute_step)
    workflow.add_node("replan_step", replan_step)
    workflow.add_node("summarize_step", summarize_step)
    workflow.add_node("update_memory", update_memory_step)

    # 3. 设置工作流的入口点
    workflow.set_entry_point("retrieve_memory")

    # 4. 定义节点之间的固定连接 (Edges)
    logger.debug("定义工作流固定边...")
    # 检索记忆后，必须制定计划
    workflow.add_edge("retrieve_memory", "plan_step")
    # 制定计划后，必须开始执行
    workflow.add_edge("plan_step", "execute_step")
    # 重新规划后，也必须回到执行
    workflow.add_edge("replan_step", "execute_step")
    # 总结完成后，必须更新记忆
    workflow.add_edge("summarize_step", "update_memory")
    # 更新记忆后，整个流程结束
    workflow.add_edge("update_memory", END)

    # 5. 定义条件连接 (Conditional Edges)
    # 这是整个工作流最核心的智能路由部分。
    # 在“执行”节点完成后，调用 `should_continue` 函数来决定下一步的走向。
    logger.debug("定义工作流条件边...")
    workflow.add_conditional_edges(
        "execute_step",
        should_continue,
        {
            # key: should_continue 返回的字符串
            # value: 要跳转到的节点的名称
            "replan_step": "replan_step",
            "summarize_step": "summarize_step",
            "execute_step": "execute_step",  # 实现循环，继续执行下一步
        }
    )

    # 6. 编译工作流
    logger.info("工作流创建完毕，正在编译...")
    return workflow.compile()


@lru_cache
def get_graph() -> StateGraph:
    """
    提供一个全局的、单例的、已编译的 LangGraph 工作流实例。

    使用 @lru_cache 装饰器可以确保 `create_workflow` 和昂贵的编译过程
    在应用的整个生命周期中只执行一次，提高了性能。

    Returns:
        编译好的 StateGraph 实例。
    """
    return create_workflow()