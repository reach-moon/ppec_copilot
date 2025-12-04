# app/services/mem0_service.py
import logging
from typing import List
from app.schemas.graph_state import Plan
from app.core.mem0_client import get_mem0_client

logger = logging.getLogger(__name__)

class Mem0Service:
    def __init__(self):
        self._client = get_mem0_client()
        logger.info("Mem0 client initialized for Mem0Service from singleton.")

    async def add_completed_plan(self, session_id: str, plan: Plan):
        """
        将一个已完成的计划作为单条记忆存入 Mem0。
        """
        if not plan.final_summary:
            logger.warning(f"Plan {plan.message_id} has no final summary. Not adding to memory.")
            return

        try:
            # 我们将整个 Plan 对象序列化为 JSON 字符串作为元数据
            # 这样可以在检索时完整地恢复它
            plan_json = plan.model_dump_json()

            # 记忆的内容是用户的目标和 AI 的最终总结
            memory_content = f"User Goal: {plan.goal}\nAI Response: {plan.final_summary}"

            self._client.add(
                memory_content,
                user_id=session_id,
                metadata={"plan": plan_json, "message_id": plan.message_id}
            )
            logger.info(f"Added completed plan {plan.message_id} to memory for session {session_id}.")
        except Exception as e:
            logger.error(f"Failed to add plan to memory for session {session_id}: {e}", exc_info=True)

    async def get_memory_history(self, session_id: str) -> List[dict]:
        """

        从 Mem0 检索历史，并转换为 Planner 需要的 "messages" 格式。
        """
        try:
            history = self._client.get_all(user_id=session_id, include_metadata=True)
            messages = []
            for mem in history:
                metadata = mem.get("metadata", {})
                if "plan" in metadata:
                    try:
                        plan_obj = Plan.model_validate_json(metadata["plan"])
                        messages.append({"role": "user", "content": plan_obj.goal})
                        messages.append({"role": "assistant", "content": plan_obj.final_summary})
                    except Exception as e:
                        logger.warning(f"Failed to parse plan from memory metadata: {e}")
            return messages
        except Exception as e:
            logger.error(f"Failed to retrieve memory for session {session_id}: {e}")
            return []

    async def revert_to_turn(self, session_id: str, message_id: str):
        """
        【全新回滚逻辑】
        删除指定 message_id 之后的所有记忆。
        """
        logger.warning(f"Reverting memory for session {session_id} to turn {message_id}")
        try:
            all_memories = self._client.get_all(user_id=session_id, include_metadata=True)
            if not all_memories:
                return

            # 找到目标 message_id 所在的记忆
            target_index = -1
            for i, mem in enumerate(all_memories):
                if mem.get("metadata", {}).get("message_id") == message_id:
                    target_index = i
                    break

            if target_index == -1:
                raise ValueError("Target turn ID not found in memory.")

            # 删除目标索引之后的所有记忆
            ids_to_delete = [mem["id"] for i, mem in enumerate(all_memories) if i > target_index]

            if not ids_to_delete:
                logger.info(f"No memories to delete after turn {message_id}.")
                return

            for mem_id in ids_to_delete:
                self._client.delete(id=mem_id)
            logger.warning(f"Successfully deleted {len(ids_to_delete)} memories after turn {message_id}.")

        except Exception as e:
            logger.error(f"Failed to revert memory for session {session_id}: {e}", exc_info=True)
            raise