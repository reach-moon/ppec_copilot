import json
import logging
from typing import AsyncGenerator, Optional

from fastapi.responses import StreamingResponse
from app.core.agents.hierarchical_planner import run_session_stream
from app.core.graphs.main_graph import get_graph
from app.schemas.graph_state import GraphState

logger = logging.getLogger(__name__)

class ChatAgent:
    """
    聊天Agent，负责处理单个会话的所有请求。
    每个session_id对应一个ChatAgent实例。
    """
    
    def __init__(self, session_id: str):
        """
        初始化ChatAgent。
        
        Args:
            session_id (str): 会话ID
        """
        self.session_id = session_id
        self.graph = get_graph()
        logger.info(f"ChatAgent initialized for session: {session_id}")
    
    async def process_request(self, message: str) -> StreamingResponse:
        """
        处理用户请求并返回流式响应。
        
        Args:
            message (str): 用户消息
            
        Returns:
            StreamingResponse: 流式响应对象
        """
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
            async for ev_name, payload in run_session_stream(initial_state, self.graph):
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
            logger.error(f"Error in ChatAgent event stream for session {self.session_id}: {e}", exc_info=True)
            err = {"error": str(e)}
            yield f"event: error\ndata: {json.dumps(err)}\n\n"