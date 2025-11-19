import logging
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage

from app.schemas.graph_state import GraphState, Plan
from app.services.llm_service import get_llm
from app.services.tools.mem0_service import Mem0Service
from app.services.tools.ragflow_tools import ragflow_knowledge_search

# 假设未来会有代码工具
# from app.services.tools.code_tool import code_generator_tool

logger = logging.getLogger(__name__)

# 使用单例模式或依赖注入来获取服务实例
mem0_service = Mem0Service()

# --- 1. 定义工具集 ---
# Executor 将使用这些工具。Planner 会"知道"这些工具的存在。
tools = [ragflow_knowledge_search]  # , code_generator_tool]

# --- 2. 定义各个功能模块 (LLM Chains) ---

# Planner 模块: 负责生成计划
planner_llm = get_llm()
planner_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    你是一个专业的项目规划AI。你的任务是接收用户的最终目标和历史对话，并将其分解成一个清晰、有序、可执行的步骤列表（Plan）。
    每个步骤的指令都应该是独立的、可以被另一个AI执行的。你必须使用下面列出的一个或多个工具来制定计划。
    
    可用工具列表:
    - `ragflow_knowledge_search(query: str)`: 当你需要查询 PPEC 平台相关的知识、文档或操作指南时使用。
    - `code_generator_tool(task_description: str)`: 当你需要生成、解释或验证代码时使用。
    
    根据用户的目标，制定一个能够达成该目标的计划。
    
    请严格按照以下JSON格式输出你的计划，不要添加任何额外的文本或解释：
    
    {{
      "goal": "用户的具体目标",
      "steps": [
        {{
          "step_id": 1,
          "instruction": "第一个步骤的具体指令",
          "status": "pending",
          "result": null
        }},
        {{
          "step_id": 2,
          "instruction": "第二个步骤的具体指令",
          "status": "pending",
          "result": null
        }}
      ]
    }}
    
    重要提示：
    1. 必须严格按照上述JSON格式输出
    2. 不要添加任何额外的文本、解释或标记
    3. 确保生成的JSON是有效的
    4. goal字段应该是用户的具体目标
    5. steps数组应该包含至少一个步骤
    6. 每个步骤必须包含step_id、instruction、status和result四个字段
    """),
    MessagesPlaceholder(variable_name="messages"),
    ("user", "我的目标是: {input}"),
])
planner_runnable = planner_prompt | planner_llm

# Executor 模块: 负责执行单个步骤
executor_llm = get_llm().bind_tools(tools)

# Summarizer 模块: 负责在计划完成后生成最终回复
summarizer_llm = get_llm()
summarizer_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "你是一个总结助手。请根据用户的原始目标和计划执行的所有步骤结果，生成一个友好、完整、最终的答复给用户。直接回答，不要说“好的，这是您的总结”之类的话。"),
    ("user", """原始目标: {goal}
计划和执行结果的摘要:
{plan_steps_summary}

请生成最终的总结性答复："""),
])
summarizer_chain = summarizer_prompt | summarizer_llm


# --- 3. LangGraph 节点函数的具体实现 ---

async def retrieve_memory_step(state: GraphState) -> GraphState:
    """
    【节点 1: retrieve_memory】
    功能: 这是工作流的入口。它的唯一职责是从 Mem0 服务中获取指定 session_id 的历史对话记录。
    这些历史记录将作为上下文，提供给 Planner 以便它能理解连续的对话。
    """
    logger.info(f"--- 节点: 检索记忆 (Session: {state['session_id']}) ---")
    session_id = state["session_id"]
    messages = await mem0_service.get_memory_history(session_id)
    logger.info(f"检索到 {len(messages)} 条历史消息。")
    return {**state, "messages": messages}


async def plan_step(state: GraphState) -> GraphState:
    """
    【节点 2: plan_step】
    功能: 接收用户本轮的输入 (`original_input`) 和历史消息 (`messages`)，调用 Planner LLM 生成一个结构化的 `Plan` 对象。
    这个 `Plan` 包含了唯一的 `turn_id` 和一个待执行的步骤列表。
    """
    logger.info("--- 节点: 制定计划 ---")
    result = await planner_runnable.ainvoke({
        "messages": state["messages"],
        "input": state["original_input"]
    })
    
    # 解析LLM的响应并创建Plan对象
    import json
    import uuid
    from langchain_core.messages import AIMessage
    from app.schemas.graph_state import PlanStep
    
    # 获取LLM响应内容
    content = result.content if isinstance(result, AIMessage) else str(result)
    
    # 尝试解析JSON
    try:
        # 清理内容，提取JSON部分
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]  # 移除 ```json 前缀
        if content.endswith("```"):
            content = content[:-3]  # 移除 ``` 后缀
            
        # 解析JSON
        plan_data = json.loads(content)
        
        # 确保turn_id存在
        if "turn_id" not in plan_data:
            plan_data["turn_id"] = str(uuid.uuid4())
            
        # 确保steps中的每个步骤都有所有必需的字段
        for step in plan_data.get("steps", []):
            if "status" not in step:
                step["status"] = "pending"
            if "result" not in step:
                step["result"] = None
                
        # 创建Plan对象
        plan = Plan(**plan_data)
        logger.info(f"生成计划 (Turn ID: {plan.turn_id})，包含 {len(plan.steps)} 个步骤。")
        return {**state, "plan": plan}
    except json.JSONDecodeError as e:
        logger.error(f"无法解析LLM响应为JSON: {e}")
        logger.error(f"原始响应内容: {content}")
        # 创建一个默认的Plan对象
        plan = Plan(
            turn_id=str(uuid.uuid4()),
            goal=state["original_input"],
            steps=[
                PlanStep(
                    step_id=1,
                    instruction="使用ragflow_knowledge_search工具搜索相关信息",
                    status="pending",
                    result=None
                )
            ]
        )
        logger.info(f"生成默认计划 (Turn ID: {plan.turn_id})，包含 {len(plan.steps)} 个步骤。")
        return {**state, "plan": plan}
    except Exception as e:
        logger.error(f"创建Plan对象时出错: {e}", exc_info=True)
        # 创建一个默认的Plan对象
        plan = Plan(
            turn_id=str(uuid.uuid4()),
            goal=state["original_input"],
            steps=[
                PlanStep(
                    step_id=1,
                    instruction="使用ragflow_knowledge_search工具搜索相关信息",
                    status="pending",
                    result=None
                )
            ]
        )
        logger.info(f"生成默认计划 (Turn ID: {plan.turn_id})，包含 {len(plan.steps)} 个步骤。")
        return {**state, "plan": plan}


async def execute_step(state: GraphState) -> GraphState:
    """
    【节点 3: execute_step】
    功能: 这是执行引擎的核心。它会检查当前 `Plan` 中第一个状态为 `pending` 的步骤，
    然后调用绑定了所有工具的 Executor LLM 来完成该步骤的指令。
    它会处理工具的调用、捕获成功或失败的结果，并更新 `Plan` 中对应步骤的状态和结果。
    """
    logger.info("--- 节点: 执行步骤 ---")
    plan = state["plan"]

    next_step = next((s for s in plan.steps if s.status == "pending"), None)
    if not next_step:
        logger.info("所有步骤均已完成，无需执行。")
        return state

    logger.info(f"开始执行步骤 {next_step.step_id}: '{next_step.instruction}'")

    try:
        # Executor LLM 接收指令，决定调用哪个工具
        response: AIMessage = await executor_llm.ainvoke([("user", next_step.instruction)])

        if response.tool_calls:
            # 假设目前只处理第一个工具调用
            tool_call = response.tool_calls[0]
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # 找到对应的工具并执行
            tool_to_call = next((t for t in tools if t.name == tool_name), None)
            if not tool_to_call:
                raise ValueError(f"Executor 尝试调用一个未知的工具: {tool_name}")

            # 异步执行工具
            observation = await tool_to_call.ainvoke(tool_args)

            next_step.status = "complete"
            next_step.result = str(observation)
            logger.info(f"步骤 {next_step.step_id} 成功完成，结果: {str(observation)[:100]}...")
        else:
            # 如果 LLM 没有调用工具，而是直接给出了回答
            next_step.status = "complete"
            next_step.result = response.content
            logger.info(f"步骤 {next_step.step_id} 完成 (LLM直接回答): {response.content[:100]}...")

    except Exception as e:
        logger.error(f"步骤 {next_step.step_id} 执行失败: {e}", exc_info=True)
        next_step.status = "failed"
        next_step.result = f"执行错误: {e}"

    return {**state, "plan": plan}


async def replan_step(state: GraphState) -> GraphState:
    """
    【节点 4: replan_step】
    功能: 这是一个自愈节点。当 `execute_step` 中有步骤失败时，工作流会进入此节点。
    它会收集当前的失败信息，并再次调用 Planner LLM，要求它生成一个修正后的新计划，以绕过失败或尝试其他方法来达成原始目标。
    """
    logger.warning("--- 节点: 重新规划 ---")
    plan = state["plan"]
    failed_step = next(s for s in plan.steps if s.status == "failed")

    replan_prompt_input = f"""
    我们正在尝试达成以下目标: {plan.goal}

    在执行过程中，第 {failed_step.step_id} 步（指令: '{failed_step.instruction}'）失败了。
    失败原因: {failed_step.result}

    请根据这个失败信息，重新制定一个能够达成原始目标的、完整的、新的计划。
    """

    new_plan = await planner_runnable.ainvoke({
        "messages": state["messages"],
        "input": replan_prompt_input
    })
    logger.warning(f"生成了新的计划 (Turn ID: {new_plan.turn_id}) 来应对失败。")
    # 清空旧的计划，替换为新计划
    return {**state, "plan": new_plan}


async def summarize_step(state: GraphState) -> GraphState:
    """
    【节点 5: summarize_step】
    功能: 当计划中的所有步骤都成功完成后，此节点被激活。
    它会收集所有步骤的执行结果，并调用 Summarizer LLM 生成一个最终的、对用户友好的、总结性的回复。
    """
    logger.info("--- 节点: 生成总结 ---")
    plan = state["plan"]

    steps_summary = "\n".join([
        f"第{s.step_id}步结果: {s.result}" for s in plan.steps
    ])

    final_summary_msg = await summarizer_chain.ainvoke({
        "goal": plan.goal,
        "plan_steps_summary": steps_summary
    })

    plan.final_summary = final_summary_msg.content
    logger.info(f"生成最终总结: {plan.final_summary[:100]}...")
    return {**state, "plan": plan}


async def update_memory_step(state: GraphState) -> GraphState:
    """
    【节点 6: update_memory】
    功能: 这是工作流的最后一个业务节点。它负责调用记忆服务 (`Mem0Service`)，
    将已经包含了最终总结的、完整的 `Plan` 对象作为一个原子单元存入长期记忆中。
    这为未来的对话和回滚操作提供了依据。
    """
    logger.info("--- 节点: 更新记忆 ---")
    session_id = state["session_id"]
    plan = state["plan"]
    if plan and plan.final_summary:
        await mem0_service.add_completed_plan(session_id, plan)
    else:
        logger.warning(f"计划没有最终总结，跳过记忆更新 (Turn ID: {plan.turn_id if plan else 'N/A'})。")
    return state


def should_continue(state: GraphState) -> str:
    """
    【条件路由函数】
    这是整个工作流的决策核心。它检查当前 Plan 的状态，
    并返回一个字符串，该字符串是下一个要跳转到的节点的名称。
    """
    plan = state.get("plan")

    # 决策 1: 如果连计划都还没有，说明是刚开始，必须先去制定计划。
    # 这个判断主要由 set_conditional_entry_point 使用。
    if not plan:
        return "plan_step"

    # 决策 2: 检查计划中是否有任何一个步骤失败了。
    # 如果有，必须立即停止执行，跳转到“重新规划”节点进行自愈。
    if any(s.status == "failed" for s in plan.steps):
        logger.warning(f"检测到失败步骤，正在跳转到重新规划节点...")
        return "replan_step"

    # 决策 3: 检查是否所有步骤都已成功完成。
    # 如果是，说明执行阶段已结束，应该跳转到“总结”节点，准备给用户最终回复。
    if all(s.status == "complete" for s in plan.steps):
        logger.info("所有步骤均已成功完成，正在跳转到总结节点...")
        return "summarize_step"

    # 决策 4: 如果以上条件都不满足，说明计划还在进行中且没有出错。
    # 那么就应该继续跳转到“执行”节点，去处理下一个待办步骤。
    logger.info("计划正在进行中，继续执行下一步骤...")
    return "execute_step"