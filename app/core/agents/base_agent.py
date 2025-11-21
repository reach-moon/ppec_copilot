from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

class AgentState(Enum):
    """Agent 状态枚举"""
    CREATED = "created"           # 已创建
    INITIALIZING = "initializing" # 初始化中
    READY = "ready"              # 就绪
    RUNNING = "running"          # 运行中
    STOPPING = "stopping"        # 停止中
    STOPPED = "stopped"          # 已停止
    ERROR = "error"              # 错误

class BaseAgent(ABC):
    """
    所有Agent的基类，定义了Agent的通用接口和生命周期管理。
    类似于Java中的Bean，具有完整的生命周期管理。
    """
    
    def __init__(self, session_id: str, agent_id: Optional[str] = None):
        """
        初始化BaseAgent。
        
        Args:
            session_id (str): 会话ID
            agent_id (Optional[str]): Agent的唯一标识符，如果未提供则使用类名
        """
        self.session_id = session_id
        self.agent_id = agent_id or self.__class__.__name__
        self.state = AgentState.CREATED
        self._lock = asyncio.Lock()
        logger.info(f"Agent {self.agent_id} created for session {self.session_id}")
    
    @property
    def current_state(self) -> AgentState:
        """获取当前Agent状态"""
        return self.state
    
    async def initialize(self) -> None:
        """
        初始化Agent的异步方法，在Agent创建后调用。
        子类可以重写此方法来执行初始化逻辑。
        """
        async with self._lock:
            if self.state != AgentState.CREATED:
                raise RuntimeError(f"Agent {self.agent_id} is not in CREATED state")
            
            self.state = AgentState.INITIALIZING
            try:
                await self._do_initialize()
                self.state = AgentState.READY
                logger.info(f"Agent {self.agent_id} initialized successfully")
            except Exception as e:
                self.state = AgentState.ERROR
                logger.error(f"Error initializing agent {self.agent_id}: {e}", exc_info=True)
                raise
    
    async def _do_initialize(self) -> None:
        """
        实际的初始化逻辑，子类可以重写此方法。
        """
        pass
    
    async def start(self) -> None:
        """
        启动Agent，使其进入运行状态。
        """
        async with self._lock:
            if self.state != AgentState.READY:
                raise RuntimeError(f"Agent {self.agent_id} is not in READY state")
            
            self.state = AgentState.RUNNING
            try:
                await self._do_start()
                logger.info(f"Agent {self.agent_id} started successfully")
            except Exception as e:
                self.state = AgentState.ERROR
                logger.error(f"Error starting agent {self.agent_id}: {e}", exc_info=True)
                raise
    
    async def _do_start(self) -> None:
        """
        实际的启动逻辑，子类可以重写此方法。
        """
        pass
    
    @abstractmethod
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理任务的抽象方法，所有子类必须实现。
        
        Args:
            task (Dict[str, Any]): 任务信息
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        pass
    
    async def stop(self) -> None:
        """
        停止Agent，释放资源。
        """
        async with self._lock:
            if self.state in [AgentState.STOPPED, AgentState.CREATED]:
                return
            
            if self.state == AgentState.ERROR:
                # 即使在错误状态，也尝试清理
                pass
            
            self.state = AgentState.STOPPING
            try:
                await self._do_stop()
                self.state = AgentState.STOPPED
                logger.info(f"Agent {self.agent_id} stopped successfully")
            except Exception as e:
                self.state = AgentState.ERROR
                logger.error(f"Error stopping agent {self.agent_id}: {e}", exc_info=True)
                raise
    
    async def _do_stop(self) -> None:
        """
        实际的停止逻辑，子类可以重写此方法来执行清理逻辑。
        """
        pass
    
    async def restart(self) -> None:
        """
        重启Agent。
        """
        await self.stop()
        await self.initialize()
        await self.start()
    
    def is_ready(self) -> bool:
        """
        检查Agent是否就绪。
        
        Returns:
            bool: 如果Agent就绪则返回True
        """
        return self.state == AgentState.READY
    
    def is_running(self) -> bool:
        """
        检查Agent是否正在运行。
        
        Returns:
            bool: 如果Agent正在运行则返回True
        """
        return self.state == AgentState.RUNNING
    
    def is_stopped(self) -> bool:
        """
        检查Agent是否已停止。
        
        Returns:
            bool: 如果Agent已停止则返回True
        """
        return self.state == AgentState.STOPPED
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(session_id={self.session_id}, agent_id={self.agent_id}, state={self.state})"
    
    def __repr__(self) -> str:
        return self.__str__()