import logging
from typing import Dict
from app.core.agents.planner_agent import PlannerAgent
from app.core.agents.memory_agent import MemoryAgent

logger = logging.getLogger(__name__)

class AgentManager:
    """
    Agent管理器，负责创建、存储和检索基于session_id的Agent实例。
    """
    
    def __init__(self):
        # 存储session_id到Agent实例的映射
        self._agents: Dict[str, PlannerAgent] = {}
        self._memory_agents: Dict[str, MemoryAgent] = {}
    
    def get_agent(self, session_id: str) -> PlannerAgent:
        """
        根据session_id获取PlannerAgent实例，如果不存在则创建新的实例。
        
        Args:
            session_id (str): 会话ID
            
        Returns:
            PlannerAgent: 对应的PlannerAgent实例
        """
        if session_id not in self._agents:
            logger.info(f"Creating new planner agent for session: {session_id}")
            self._agents[session_id] = PlannerAgent(session_id, self)
        
        return self._agents[session_id]
    
    def get_memory_agent(self, agent_id: str = "default") -> MemoryAgent:
        """
        根据agent_id获取MemoryAgent实例，如果不存在则创建新的实例。
        
        Args:
            agent_id (str): MemoryAgent的唯一标识符，默认为"default"
            
        Returns:
            MemoryAgent: 对应的MemoryAgent实例
        """
        if agent_id not in self._memory_agents:
            logger.info(f"Creating new memory agent with id: {agent_id}")
            self._memory_agents[agent_id] = MemoryAgent(agent_id)
        
        return self._memory_agents[agent_id]
    
    def remove_agent(self, session_id: str) -> bool:
        """
        移除指定session_id的Agent实例。
        
        Args:
            session_id (str): 会话ID
            
        Returns:
            bool: 是否成功移除
        """
        removed = False
        if session_id in self._agents:
            logger.info(f"Removing planner agent for session: {session_id}")
            del self._agents[session_id]
            removed = True
            
        return removed
    
    def remove_memory_agent(self, agent_id: str) -> bool:
        """
        移除指定agent_id的MemoryAgent实例。
        
        Args:
            agent_id (str): MemoryAgent的唯一标识符
            
        Returns:
            bool: 是否成功移除
        """
        if agent_id in self._memory_agents:
            logger.info(f"Removing memory agent with id: {agent_id}")
            del self._memory_agents[agent_id]
            return True
        return False
    
    def get_agent_count(self) -> int:
        """
        获取当前管理的Agent数量。
        
        Returns:
            int: Agent数量
        """
        return len(self._agents) + len(self._memory_agents)

# 全局单例实例
agent_manager = AgentManager()