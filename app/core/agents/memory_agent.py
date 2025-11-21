import logging
import uuid
from typing import List, Dict, Any
from app.core.agents.base_agent import BaseAgent, AgentState
from app.services.tools.mem0_service import Mem0Service
from app.schemas.graph_state import Plan

logger = logging.getLogger(__name__)

class MemoryAgent(BaseAgent):
    """
    记忆Agent，负责处理与记忆相关的操作。
    包括存储、检索和管理对话历史。
    作为独立的Agent为其他Agent提供记忆服务。
    """
    
    def __init__(self, agent_id: str):
        """
        初始化MemoryAgent。
        
        Args:
            agent_id (str): Agent的唯一标识符
        """
        # 使用agent_id作为session_id参数传递给BaseAgent，但实际标识是agent_id
        super().__init__(agent_id, f"MemoryAgent-{agent_id}")
        self.mem0_service = Mem0Service()
        logger.info(f"MemoryAgent initialized for agent: {agent_id}")
    
    async def _do_initialize(self) -> None:
        """
        MemoryAgent的初始化逻辑。
        """
        # 可以在这里添加特定的初始化逻辑
        pass
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理记忆相关的任务。
        
        Args:
            task (Dict[str, Any]): 任务信息，可能包含操作类型和相关数据
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        if self.state != AgentState.RUNNING:
            raise RuntimeError(f"MemoryAgent is not running, current state: {self.state}")
            
        operation = task.get("operation", "")
        target_session_id = task.get("session_id", "")
        
        if not target_session_id:
            return {"error": "No session_id provided in task"}
        
        if operation == "store_plan":
            return await self._store_plan(target_session_id, task.get("plan"))
        elif operation == "retrieve_history":
            return await self._retrieve_history(target_session_id)
        elif operation == "revert_to_turn":
            return await self._revert_to_turn(target_session_id, task.get("message_id"))
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    async def _store_plan(self, session_id: str, plan: Plan) -> Dict[str, Any]:
        """
        存储完成的计划到记忆中。
        
        Args:
            session_id (str): 会话ID
            plan (Plan): 要存储的计划
            
        Returns:
            Dict[str, Any]: 存储结果
        """
        try:
            await self.mem0_service.add_completed_plan(session_id, plan)
            return {
                "status": "success", 
                "message": f"Plan {plan.message_id} stored successfully",
                "session_id": session_id,
                "message_id": plan.message_id
            }
        except Exception as e:
            logger.error(f"Error storing plan for session {session_id}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    async def _retrieve_history(self, session_id: str) -> Dict[str, Any]:
        """
        检索会话历史。
        
        Args:
            session_id (str): 会话ID
            
        Returns:
            Dict[str, Any]: 检索到的历史消息
        """
        try:
            messages = await self.mem0_service.get_memory_history(session_id)
            return {"status": "success", "messages": messages, "session_id": session_id}
        except Exception as e:
            logger.error(f"Error retrieving history for session {session_id}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    async def _revert_to_turn(self, session_id: str, message_id: str) -> Dict[str, Any]:
        """
        回滚到指定的message_id。
        
        Args:
            session_id (str): 会话ID
            message_id (str): 要回滚到的message_id
            
        Returns:
            Dict[str, Any]: 回滚结果
        """
        try:
            await self.mem0_service.revert_to_turn(session_id, message_id)
            return {
                "status": "success", 
                "message": f"Reverted to turn {message_id}",
                "session_id": session_id,
                "message_id": message_id
            }
        except Exception as e:
            logger.error(f"Error reverting to turn {message_id} for session {session_id}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}