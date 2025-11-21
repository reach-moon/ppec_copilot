from typing import List, TypedDict, Optional
from pydantic import BaseModel, Field
import uuid

# --- 核心数据结构 ---

class PlanStep(BaseModel):
    """定义计划中的一个独立步骤"""
    step_id: int = Field(description="步骤的序号，从 1 开始。")
    instruction: str = Field(description="对该步骤任务的清晰、独立的指令描述。")
    status: str = Field(default="pending", description="步骤状态: pending, complete, failed")
    result: Optional[str] = Field(default=None, description="该步骤执行后的结果或错误信息。")


class Plan(BaseModel):
    """定义整个任务计划，它代表了一次完整的用户交互（Turn）"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="本次交互的唯一ID，作为回滚的锚点。")
    goal: str = Field(description="用户的原始最终目标。")
    steps: List[PlanStep] = Field(description="为实现目标而分解出的步骤列表。")
    final_summary: Optional[str] = Field(default=None, description="计划全部完成后，给用户的最终总结性答复。")


# --- LangGraph 状态 ---

class GraphState(TypedDict):
    """
    定义图的状态。
    它代表了一个会话中，正在进行的一次交互（Turn）的实时状态。
    """
    session_id: str
    original_input: str
    message_id: Optional[str]

    # 当前正在处理的 Plan
    plan: Optional[Plan] = None

    # 从 Mem0 中恢复的历史消息，用于 Planner 上下文
    # 注意：这里的 'messages' 字段现在主要用于输入，而不是像之前那样累加
    messages: List[dict]