import json
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.endpoints.v1.models import ChatRequest
from app.core.graphs.main_graph import get_graph
from app.schemas.graph_state import GraphState

logger = logging.getLogger(__name__)

# 创建 API 路由器实例
router = APIRouter()


@router.post("/chat")
async def stream_chat(request: ChatRequest):
    graph = get_graph()

    initial_state: GraphState = {
        "session_id": request.session_id,
        "original_input": request.message,
        "messages": [],  # 将由 retrieve_memory 节点填充
        "plan": None,
    }

    async def event_stream():
        # 流式输出 plan 的实时状态
        async for event in graph.astream_events(initial_state, version="v1"):
            # 在这里，我们可以根据 event 的类型，将 Plan 的实时更新情况
            # （如哪个步骤正在执行、哪个步骤已完成）流式推送到前端
            if event["event"] == "on_chain_end" and event["name"] == "execute_step":
                current_plan = event["data"]["output"]["plan"]
                yield f"event: plan_update\ndata: {current_plan.model_dump_json()}\n\n"

            # 当整个流程结束时，推送最终的总结
            if event["event"] == "on_chain_end" and event["name"] == "summarize_step":
                final_plan = event["data"]["output"]["plan"]
                final_response = {
                    "turn_id": final_plan.turn_id,
                    "summary": final_plan.final_summary
                }
                yield f"event: final_response\ndata: {json.dumps(final_response)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")