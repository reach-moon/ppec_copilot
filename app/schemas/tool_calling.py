from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from openai.types.chat import ChatCompletionMessageParam


class ToolCall(BaseModel):
    """Represents a tool call that can be made by the LLM."""
    name: str = Field(..., description="The name of the tool to call")
    arguments: Dict[str, Any] = Field(..., description="Arguments for the tool call")


class ToolCallingRequest(BaseModel):
    """Request model for tool calling interface."""
    model: str = Field("model", description="Model name to use for completion")
    messages: List[ChatCompletionMessageParam] = Field(..., description="Messages in the conversation")
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="List of tools available for the model")
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(None, description="How to select tools")
    stream: bool = Field(True, description="Whether to stream the response")
    extra_body: Optional[Dict[str, Any]] = Field(None, description="Additional parameters for model configuration")


class ToolCallingResponse(BaseModel):
    """Response model for tool calling interface."""
    id: str = Field(..., description="Unique identifier for the response")
    choices: List[Dict[str, Any]] = Field(..., description="List of response choices")
    created: int = Field(..., description="Unix timestamp of when the response was created")
    model: str = Field(..., description="The model used for generation")
    object: str = Field("chat.completion", description="Object type")
    system_fingerprint: Optional[str] = Field(None, description="System fingerprint")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage statistics")