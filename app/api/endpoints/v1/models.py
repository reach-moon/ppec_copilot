from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from openai.types.chat import ChatCompletionMessageParam


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="唯一的会话ID，用于维持对话记忆。")
    turn_id: str | None = Field(None, description="本次交互ID，用于回滚或关联。")
    message: str = Field(..., description="用户的提问。")


class ChatCompletionRequest(BaseModel):
    model: str = Field("model", description="模型名称")
    channel_id: Optional[int] = Field(8, description="OneAPI频道ID")

    messages: List[ChatCompletionMessageParam] = Field(..., description="消息历史")
    stream: bool = Field(True, description="是否流式响应")
    extra_body: Optional[Dict[str, Any]] = Field(None, description="额外参数")
    
    
class ToolCallingRequest(BaseModel):
    model: str = Field("model", description="模型名称")
    messages: List[ChatCompletionMessageParam] = Field(..., description="消息历史")
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="可用工具列表")
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(None, description="工具选择策略")
    stream: bool = Field(True, description="是否流式响应")
    extra_body: Optional[Dict[str, Any]] = Field(None, description="额外参数")