from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="唯一的会话ID，用于维持对话记忆。")
    message: str = Field(..., description="用户的提问。")