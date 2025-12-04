import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette import status

# 导入我们重构后的 Mem0Service
from app.services.tools.mem0_service import Mem0Service

logger = logging.getLogger(__name__)
router = APIRouter()
mem0_service = Mem0Service()  # 假设使用单例


class RevertRequest(BaseModel):
    session_id: str
    message_id: str


@router.post("/revert", status_code=status.HTTP_204_NO_CONTENT)
async def revert_conversation(request: RevertRequest):
    """
    接收外部系统的回滚请求，并对记忆进行精确回滚。

    - session_id: 定位到具体是哪个用户的会话。
    - message_id: 定位到该会话需要回滚到的“时间点”（即哪一次交互）。
    """
    logger.info(f"接收到回滚请求，Session: {request.session_id}, 回滚至 Turn: {request.message_id}")
    try:
        # 调用我们重构后的 revert_to_turn 方法
        # 这个方法会删除 Mem0 中所有在目标 message_id 之后存储的记忆
        await mem0_service.revert_to_turn(
            session_id=request.session_id,
            message_id=request.message_id
        )
        # 成功时返回 204 No Content，表示操作已成功执行
        return
    except ValueError as e:
        # 如果传入的 message_id 在记忆中不存在，则返回 404
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.critical(f"回滚操作发生未处理的错误: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="回滚会话状态失败。")