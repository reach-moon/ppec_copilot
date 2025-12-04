import json
import logging
import uuid
from typing import AsyncGenerator, Optional, Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage

from fastapi.responses import StreamingResponse
from app.core.agents.base_agent import BaseAgent, AgentState
from app.schemas.graph_state import GraphState, Plan, PlanStep
from app.services.llm_service import get_llm
from app.services.tools.ragflow_tools import ragflow_knowledge_search

logger = logging.getLogger(__name__)

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
    - `ragflow_knowledge_search(query: str, chat_history: List[dict] = None)`: 当你需要查询 PPEC 平台相关的知识、文档或操作指南时使用。
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


class PlannerAgent(BaseAgent):
    """
    规划Agent，负责处理单个会话的所有请求。
    每个session_id对应一个PlannerAgent实例。
    这是主要的协调者，负责调度其他子任务Agent。
    """
    
    def __init__(self, session_id: str, agent_manager=None):
        """
        初始化PlannerAgent。
        
        Args:
            session_id (str): 会话ID
            agent_manager: Agent管理器实例
        """
        super().__init__(session_id, "PlannerAgent")
        self.agent_manager = agent_manager
        logger.info(f"PlannerAgent initialized for session: {session_id}")
    
    async def _do_initialize(self) -> None:
        """
        PlannerAgent的初始化逻辑。
        """
        # 可以在这里添加特定的初始化逻辑
        pass
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理任务的主要方法。
        
        Args:
            task (Dict[str, Any]): 任务信息，包含消息等内容
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        if self.state != AgentState.RUNNING:
            raise RuntimeError(f"PlannerAgent is not running, current state: {self.state}")
            
        message = task.get("message", "")
        message_id = task.get("message_id")
        
        if not message:
            return {"error": "No message provided in task"}
        
        # 如果没有提供message_id，则生成一个新的
        if not message_id:
            message_id = str(uuid.uuid4())
            logger.info(f"Generated new message_id: {message_id}")
        
        # 这里可以实现更复杂的任务处理逻辑
        # 例如调度其他子任务Agent来处理特定类型的任务
        return {
            "status": "processed", 
            "message": message,
            "session_id": self.session_id,
            "message_id": message_id
        }
    
    async def process_request(self, message: str, message_id: Optional[str] = None) -> StreamingResponse:
        """
        处理用户请求并返回流式响应。
        
        Args:
            message (str): 用户消息
            message_id (Optional[str]): 交互ID，如果未提供则自动生成
            
        Returns:
            StreamingResponse: 流式响应对象
        """
        if self.state != AgentState.RUNNING:
            raise RuntimeError(f"PlannerAgent is not running, current state: {self.state}")
            
        # 如果没有提供message_id，则生成一个新的
        if not message_id:
            message_id = str(uuid.uuid4())
            logger.info(f"Generated new message_id: {message_id}")
        
        initial_state: GraphState = {
            "session_id": self.session_id,
            "original_input": message,
            "messages": [],  # 将由 retrieve_memory 节点填充
            "plan": None,
        }
        
        return StreamingResponse(
            self._event_stream(initial_state),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable buffering for nginx
            }
        )
    
    async def _event_stream(self, initial_state: GraphState) -> AsyncGenerator[str, None]:
        """
        内部异步生成器函数，用于产生各种事件流。
        通过运行会话流来生成不同类型的事件，并将它们格式化为SSE事件格式。
        
        Args:
            initial_state (GraphState): 初始状态
            
        Yields:
            str: 格式化的SSE事件字符串
        """
        try:
            async for ev_name, payload in self._run_session_stream(initial_state):
                # 处理深度思考事件
                # 格式化思考内容并添加前缀，然后作为 thought_process 事件发送
                if ev_name == "thought" and payload is not None:
                    if isinstance(payload, dict):
                        thought_data = {"type": "deep_thought", **payload}
                        if "content" in thought_data:
                            thought_data["content"] = f"> {thought_data['content']}"
                    else:
                        thought_data = {"type": "deep_thought", "content": f"> {payload}"}
                    yield f"event: thought_process\ndata: {json.dumps(thought_data)}\n\n"
                
                # 处理计划更新事件
                # 直接将计划对象序列化为JSON并作为 plan_update 事件发送
                if ev_name == "plan_update" and payload is not None:
                    yield f"event: plan_update\ndata: {payload.model_dump_json()}\n\n"
                
                # 处理步骤更新事件
                # 将步骤更新信息序列化为JSON并作为 step_update 事件发送
                elif ev_name == "step_update" and payload is not None:
                    yield f"event: step_update\ndata: {json.dumps(payload)}\n\n"
                
                # 处理最终响应事件
                # 将最终响应信息序列化为JSON并作为 final_response 事件发送
                elif ev_name == "final_response" and payload is not None:
                    yield f"event: final_response\ndata: {json.dumps(payload)}\n\n"
                
                # 处理心跳事件
                # 发送空数据以保持连接活跃
                elif ev_name == "heartbeat":
                    yield ""
        except Exception as e:
            logger.error(f"Error in PlannerAgent event stream for session {self.session_id}: {e}", exc_info=True)
            err = {"error": str(e)}
            yield f"event: error\ndata: {json.dumps(err)}\n\n"
    
    async def _run_session_stream(self, initial_state: GraphState):
        """
        运行会话流的核心逻辑。
        """
        state = initial_state
        
        # 检索记忆
        state = await self._retrieve_memory_step(state)
        yield ("thought", {"phase": "retrieve", "content": "开始检索历史记忆"})
        yield ("thought", {"phase": "retrieve", "content": "历史记忆检索完成"})
        
        # 制定计划
        state = await self._plan_step(state)
        plan_obj = state.get("plan")
        if plan_obj:
            yield ("plan_update", plan_obj)
            yield ("thought", {"phase": "plan", "content": f"已生成计划，目标: {plan_obj.goal}，步骤数: {len(plan_obj.steps)}"})
        
        # 执行循环
        while True:
            nxt = self._should_continue(state)
            if nxt == "execute_step":
                pin = state.get("plan")
                if pin:
                    step_id = next((s.step_id for s in pin.steps if s.status == "pending"), None)
                    payload = {"message_id": pin.message_id, "status": "running"}
                    if step_id is not None:
                        payload["step_id"] = step_id
                    yield ("step_update", payload)
                    if step_id is not None:
                        next_step = next((s for s in pin.steps if s.step_id == step_id), None)
                        if next_step:
                            yield ("thought", {"phase": "execute", "content": f"开始执行步骤 {next_step.step_id}: {next_step.instruction}"})
                state = await self._execute_step(state)
                plan_obj = state.get("plan")
                if plan_obj:
                    yield ("plan_update", plan_obj)
                    last_done = next((s for s in plan_obj.steps if s.status == "complete" and s.result), None)
                    if last_done:
                        yield ("thought", {"phase": "execute", "content": f"步骤 {last_done.step_id} 完成"})
                yield ("heartbeat", None)
                continue
            if nxt == "replan_step":
                yield ("thought", {"phase": "replan", "content": "检测到失败，开始重新规划"})
                state = await self._replan_step(state)
                plan_obj = state.get("plan")
                if plan_obj:
                    yield ("plan_update", plan_obj)
                    yield ("thought", {"phase": "plan", "content": f"已生成新的计划，步骤数: {len(plan_obj.steps)}"})
                yield ("heartbeat", None)
                continue
            if nxt == "summarize_step":
                yield ("thought", {"phase": "summarize", "content": "开始生成最终总结"})
                state = await self._summarize_step(state)
                final_plan = state.get("plan")
                if final_plan:
                    yield ("final_response", {"message_id": final_plan.message_id, "summary": final_plan.final_summary})
                    yield ("thought", {"phase": "summarize", "content": "总结生成完成"})
                await self._update_memory_step(state)
                yield ("thought", {"phase": "update", "content": "记忆更新完成"})
                break
            break
    
    async def _retrieve_memory_step(self, state: GraphState) -> GraphState:
        """
        【节点: retrieve_memory】
        功能: 从 Mem0 服务中获取指定 session_id 的历史对话记录。
        """
        logger.info(f"--- 节点: 检索记忆 (Session: {state['session_id']}) ---")
        session_id = state["session_id"]
        
        # 使用MemoryAgent来处理记忆相关的操作
        if self.agent_manager:
            memory_agent = self.agent_manager.get_memory_agent("default")  # 使用默认的MemoryAgent
            # 确保MemoryAgent已初始化并启动
            if not memory_agent.is_ready() and not memory_agent.is_running():
                await memory_agent.initialize()
                await memory_agent.start()
                
            result = await memory_agent.process_task({
                "operation": "retrieve_history",
                "session_id": session_id
            })
            
            messages = result.get("messages", [])
            logger.info(f"检索到 {len(messages)} 条历史消息。")
            return {**state, "messages": messages}
        else:
            return {**state, "messages": []}

    async def _plan_step(self, state: GraphState) -> GraphState:
        """
        【节点: plan_step】
        功能: 接收用户本轮的输入和历史消息，调用 Planner LLM 生成一个结构化的 Plan 对象。
        """
        logger.info("--- 节点: 制定计划 ---")
        try:
            result = await planner_runnable.ainvoke({
                "messages": state["messages"],
                "input": state["original_input"]
            })
        except Exception:
            plan = Plan(
                message_id=str(uuid.uuid4()),
                goal=state["original_input"],
                steps=[
                    PlanStep(step_id=1, instruction="使用ragflow_knowledge_search工具搜索相关信息", status="pending", result=None)
                ]
            )
            return {**state, "plan": plan}
        
        # 解析LLM的响应并创建Plan对象
        import json
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
            
            # 确保message_id存在
            if "message_id" not in plan_data:
                plan_data["message_id"] = str(uuid.uuid4())
                
            # 确保steps中的每个步骤都有所有必需的字段
            for step in plan_data.get("steps", []):
                if "status" not in step:
                    step["status"] = "pending"
                if "result" not in step:
                    step["result"] = None
                    
            # 创建Plan对象
            plan = Plan(**plan_data)
            logger.info(f"生成计划 (Turn ID: {plan.message_id})，包含 {len(plan.steps)} 个步骤。")
            return {**state, "plan": plan}
        except json.JSONDecodeError as e:
            logger.error(f"无法解析LLM响应为JSON: {e}")
            logger.error(f"原始响应内容: {content}")
            # 创建一个默认的Plan对象
            plan = Plan(
                message_id=str(uuid.uuid4()),
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
            logger.info(f"生成默认计划 (Turn ID: {plan.message_id})，包含 {len(plan.steps)} 个步骤。")
            return {**state, "plan": plan}
        except Exception as e:
            logger.error(f"创建Plan对象时出错: {e}", exc_info=True)
            # 创建一个默认的Plan对象
            plan = Plan(
                message_id=str(uuid.uuid4()),
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
            logger.info(f"生成默认计划 (Turn ID: {plan.message_id})，包含 {len(plan.steps)} 个步骤。")
            return {**state, "plan": plan}

    async def _execute_step(self, state: GraphState) -> GraphState:
        """
        【节点: execute_step】
        功能: 执行当前 Plan 中的第一个 "pending" 状态的步骤。
        """
        logger.info("--- 节点: 执行步骤 ---")
        plan: Plan = state["plan"]
        if not plan:
            logger.error("执行步骤时，计划对象为空。")
            return state

        # 找到第一个待处理的步骤
        step_to_execute = next((step for step in plan.steps if step.status == "pending"), None)
        if not step_to_execute:
            logger.info("没有找到待处理的步骤。")
            return state

        logger.info(f"正在执行步骤 {step_to_execute.step_id}: {step_to_execute.instruction}")

        try:
            # 使用 LLM 调用工具执行步骤
            # 这里使用了 LangChain 的 bind_tools 和 invoke 功能
            response = await executor_llm.ainvoke(step_to_execute.instruction)
            logger.debug(f"工具调用响应: {response}")

            # 解析工具调用结果
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # 处理工具调用
                tool_call = response.tool_calls[0]  # 假设只有一个工具调用
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                logger.info(f"调用工具: {tool_name}，参数: {tool_args}")

                # 根据工具名称执行相应的操作
                if tool_name == "ragflow_knowledge_search":
                    # 直接使用RAGFlow工具处理知识检索任务，传递聊天历史记录
                    result = await ragflow_knowledge_search(tool_args["query"], state.get("messages", []))
                    step_result = result
                else:
                    step_result = f"调用了工具 {tool_name}，参数为 {tool_args}"
            else:
                # 没有工具调用，直接使用响应内容
                step_result = response.content if hasattr(response, 'content') else str(response)

            # 更新步骤状态
            step_to_execute.status = "complete"
            step_to_execute.result = step_result

            logger.info(f"步骤 {step_to_execute.step_id} 执行成功。")
            return {**state, "plan": plan}

        except Exception as e:
            logger.error(f"执行步骤 {step_to_execute.step_id} 时出错: {e}", exc_info=True)
            # 标记步骤为失败
            step_to_execute.status = "failed"
            step_to_execute.result = f"执行步骤时发生错误: {str(e)}"
            return {**state, "plan": plan}

    async def _replan_step(self, state: GraphState) -> GraphState:
        """
        【节点: replan_step】
        功能: 当某个步骤执行失败时，重新制定一个修正后的计划。
        """
        logger.info("--- 节点: 重新规划 ---")
        plan: Plan = state["plan"]
        if not plan:
            logger.error("重新规划时，计划对象为空。")
            return state

        # 找到第一个失败的步骤
        failed_step = next((step for step in plan.steps if step.status == "failed"), None)
        if not failed_step:
            logger.warning("没有找到失败的步骤，但触发了重新规划节点。")
            return state

        logger.info(f"正在为失败的步骤 {failed_step.step_id} 重新规划: {failed_step.instruction}")

        # 构建失败分析提示
        failure_analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的项目修复AI。你的任务是分析步骤失败的原因，并提供一个修正计划。"),
            ("user", f"""
    原始目标: {plan.goal}
    失败的步骤: {failed_step.step_id}
    步骤指令: {failed_step.instruction}
    失败原因: {failed_step.result}

    请提供一个新的步骤列表来替代失败的步骤。请严格按照以下JSON格式输出：

    {{
      "new_steps": [
        {{
          "step_id": {failed_step.step_id},
          "instruction": "修正后的第一个步骤指令",
          "status": "pending",
          "result": null
        }}
      ]
    }}
            """),
        ])

        try:
            # 调用LLM进行重新规划
            failure_analysis_chain = failure_analysis_prompt | get_llm()
            analysis_result = await failure_analysis_chain.ainvoke({})

            # 解析重新规划的结果
            content = analysis_result.content if hasattr(analysis_result, 'content') else str(analysis_result)
            
            # 清理并解析JSON
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]  # 移除 ```json 前缀
            if content.endswith("```"):
                content = content[:-3]  # 移除 ``` 后缀
                
            analysis_data = json.loads(content)
            new_steps = analysis_data.get("new_steps", [])
            
            # 替换失败的步骤
            new_step_objects = []
            for step_data in new_steps:
                new_step_objects.append(PlanStep(**step_data))
            
            # 找到失败步骤的索引并替换
            failed_index = next(i for i, step in enumerate(plan.steps) if step.step_id == failed_step.step_id)
            plan.steps[failed_index:failed_index+1] = new_step_objects
            
            logger.info(f"重新规划完成，替换了 {len(new_step_objects)} 个步骤。")
            return {**state, "plan": plan}
            
        except Exception as e:
            logger.error(f"重新规划步骤时出错: {e}", exc_info=True)
            # 如果重新规划失败，添加一个简单的修复步骤
            repair_step = PlanStep(
                step_id=failed_step.step_id + 0.1,  # 使用小数ID表示修复步骤
                instruction=f"修复步骤: 手动处理 '{failed_step.instruction}' 的问题",
                status="pending",
                result=None
            )
            
            # 在失败步骤后插入修复步骤
            failed_index = next(i for i, step in enumerate(plan.steps) if step.step_id == failed_step.step_id)
            plan.steps.insert(failed_index + 1, repair_step)
            
            return {**state, "plan": plan}

    async def _summarize_step(self, state: GraphState) -> GraphState:
        """
        【节点: summarize_step】
        功能: 在所有步骤都成功完成后，生成一个面向用户的、友好的最终总结。
        """
        logger.info("--- 节点: 生成总结 ---")
        plan: Plan = state["plan"]
        if not plan:
            logger.error("生成总结时，计划对象为空。")
            return state

        try:
            # 构建步骤摘要
            steps_summary = "\n".join([
                f"步骤 {step.step_id}: {step.instruction}\n结果: {step.result}"
                for step in plan.steps
            ])

            # 调用总结链
            summary_response = await summarizer_chain.ainvoke({
                "goal": plan.goal,
                "plan_steps_summary": steps_summary
            })

            # 更新计划的最终总结
            plan.final_summary = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
            logger.info("总结生成完成。")
            return {**state, "plan": plan}
            
        except Exception as e:
            logger.error(f"生成总结时出错: {e}", exc_info=True)
            plan.final_summary = "任务已完成，但无法生成详细总结。"
            return {**state, "plan": plan}

    async def _update_memory_step(self, state: GraphState) -> GraphState:
        """
        【节点: update_memory_step】
        功能: 在整个交互完成后，将完成的 Plan 存入 Mem0 长期记忆中。
        """
        logger.info("--- 节点: 更新记忆 ---")
        plan: Plan = state["plan"]
        if not plan:
            logger.error("更新记忆时，计划对象为空。")
            return state

        try:
            # 使用MemoryAgent来存储完成的计划
            if self.agent_manager:
                memory_agent = self.agent_manager.get_memory_agent("default")  # 使用默认的MemoryAgent
                # 确保MemoryAgent已初始化并启动
                if not memory_agent.is_ready() and not memory_agent.is_running():
                    await memory_agent.initialize()
                    await memory_agent.start()
                    
                result = await memory_agent.process_task({
                    "operation": "store_plan",
                    "session_id": state["session_id"],
                    "plan": plan
                })
                
                if result.get("status") == "success":
                    logger.info(f"计划 {plan.message_id} 已成功存入记忆。")
                else:
                    logger.error(f"存储计划到记忆时出错: {result.get('message')}")
            else:
                logger.warning("没有AgentManager实例，无法更新记忆。")
            
        except Exception as e:
            logger.error(f"更新记忆时出错: {e}", exc_info=True)
        
        return state

    def _should_continue(self, state: GraphState) -> str:
        """
        【路由函数】
        功能: 根据当前状态决定下一步应该执行哪个节点。
        """
        logger.debug("--- 路由函数: should_continue ---")
        plan: Plan = state["plan"]
        if not plan:
            logger.warning("计划对象为空，结束流程。")
            return "end"

        # 决策 1: 检查是否有步骤执行失败。
        # 如果有，应该跳转到"重新规划"节点进行自我修复。
        failed_step = next((step for step in plan.steps if step.status == "failed"), None)
        if failed_step:
            logger.info(f"检测到失败步骤 {failed_step.step_id}，正在跳转到重新规划节点...")
            return "replan_step"

        # 决策 2: 检查是否还有待办步骤。
        # 如果有，应该跳转到"执行"节点继续执行下一个步骤。
        pending_step = next((step for step in plan.steps if step.status == "pending"), None)
        if pending_step:
            logger.info(f"检测到待办步骤 {pending_step.step_id}，正在跳转到执行节点...")
            return "execute_step"

        # 决策 3: 检查是否所有步骤都已成功完成。
        # 如果是，说明执行阶段已结束，应该跳转到"总结"节点，准备给用户最终回复。
        if all(s.status == "complete" for s in plan.steps):
            logger.info("所有步骤均已成功完成，正在跳转到总结节点...")
            return "summarize_step"

        # 决策 4: 如果以上条件都不满足，说明计划还在进行中且没有出错。
        # 那么就应该继续跳转到"执行"节点，去处理下一个待办步骤。
        logger.info("计划正在进行中，继续执行下一步骤...")
        return "execute_step"