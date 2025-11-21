import json, logging
import httpx
from datetime import datetime
import uuid

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, Choice, ChoiceDelta

from app.api.endpoints.v1.models import ChatRequest, ChatCompletionRequest
from app.core.agents import agent_manager
from app.services.llm_service import get_llm
from config.settings import settings

logger = logging.getLogger(__name__)

# 创建 API 路由器实例
router = APIRouter()


@router.post("/chat")
async def stream_chat(request: ChatRequest):
    """
    流式处理聊天请求的主要端点。
    
    该函数通过session_id找到对应的Agent，并由该Agent处理请求。
    每个session_id对应一个独立的Agent实例，用于维护会话状态。
    
    Args:
        request (ChatRequest): 包含用户消息和会话ID的请求对象
            - session_id (str): 唯一的会话标识符，用于检索和存储对话历史
            - turn_id (Optional[str]): 交互ID，用于标识单次用户请求
            - message (str): 用户的输入消息
            
    Returns:
        StreamingResponse: 一个SSE流响应，由对应的Agent生成
    """
    # 获取对应session_id的Agent实例
    agent = agent_manager.get_agent(request.session_id)

    # 由Agent处理请求并返回流式响应
    return await agent.process_request(request.message, request.turn_id)


@router.post("/ragflow-stream")
async def ragflow_stream(request: ChatRequest):
    """
    Direct proxy endpoint for RAGFlow API with full OpenAI compatibility
    """
    logger.info(f"Starting RAGFlow proxy stream for message: {request.message[:50]}...")
    
    # 1. Construct the complete RAGFlow API URL
    url = settings.RAGFLOW_API_URL + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.RAGFLOW_API_KEY}"
    }
    
    # 2. Construct RAGFlow/OpenAI compatible request payload
    payload = {
        "model": "model",
        "messages": [
            {   
                "role": "system",
                "content": (
                    "First output your step-by-step reasoning, then mark final answer with '---FINAL ANSWER---'. "
                    "Keep the reasoning concise and relevant."
                )
            },
            {"role": "user", "content": request.message}
        ],
        "stream": True,
        "extra_body": {"reference": True}
    }
    
    logger.info(f"Sending request to RAGFlow API: {url}")
    logger.debug(f"Request payload: {payload}")
    
    # 3. 创建自定义异步生成器进行流式代理
    async def stream_content():
        done_sent = False
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream('POST', url, json=payload, headers=headers) as ragflow_response:
                    logger.info(f"RAGFlow API response status: {ragflow_response.status_code}")
                    
                    # 记录响应头信息
                    logger.debug(f"RAGFlow API response headers: {dict(ragflow_response.headers)}")
                    
                    # 检查响应状态码
                    if ragflow_response.status_code != 200:
                        # 尝试读取错误内容
                        try:
                            error_content = await ragflow_response.aread()
                            error_msg = error_content.decode()
                            logger.error(f"RAGFlow API error content: {error_msg}")
                        except Exception as read_error:
                            logger.error(f"Failed to read RAGFlow API error content: {read_error}")
                            error_msg = "Unknown error from RAGFlow API"
                        
                        logger.error(f"RAGFlow API returned error status: {ragflow_response.status_code}")
                        # Format error in OpenAI standard format
                        error_response = ChatCompletionChunk(
                            id=f"chatcmpl-{uuid.uuid4().hex}",
                            choices=[
                                Choice(
                                    delta=ChoiceDelta(
                                        content=f"RAGFlow API Error: {ragflow_response.status_code} - {error_msg}",
                                        role="assistant",
                                        function_call=None,
                                        tool_calls=None,
                                        reasoning_content=None
                                    ),
                                    finish_reason="stop",
                                    index=0,
                                    logprobs=None
                                )
                            ],
                            created=int(datetime.now().timestamp()),
                            model="ragflow",
                            object="chat.completion.chunk",
                            system_fingerprint="",
                            usage=None
                        )
                        yield f"data: {error_response.model_dump_json()}\n\n"
                        yield "data: [DONE]\n\n"
                        done_sent = True
                        return
                    
                    # Process and forward response content in proper OpenAI format
                    async for chunk in ragflow_response.aiter_bytes():
                        # Handle empty chunks
                        if not chunk:
                            continue
                            
                        # Decode the chunk
                        try:
                            decoded_chunk = chunk.decode('utf-8')
                            # Handle empty or whitespace-only chunks
                            if not decoded_chunk.strip():
                                continue
                                
                            if decoded_chunk.startswith('data:'):
                                # Ensure proper spacing after 'data:'
                                if decoded_chunk.startswith('data: '):
                                    # Already properly formatted
                                    data_part = decoded_chunk
                                else:
                                    # Fix formatting by adding space after 'data:'
                                    data_part = 'data: ' + decoded_chunk[5:]  # Skip 'data:' part
                                    
                                # Extract the JSON part
                                json_str = data_part[6:]  # Remove 'data: ' prefix
                                if json_str.strip() == '[DONE]':
                                    yield "data: [DONE]\n\n"
                                    done_sent = True
                                else:
                                    # Try to parse and validate as ChatCompletionChunk
                                    try:
                                        json_data = json.loads(json_str)
                                        logger.info(f"Parsed RAGFlow chunk: {json_data}")
                                        # Validate by creating a ChatCompletionChunk object
                                        ChatCompletionChunk(**json_data)
                                        # If valid, re-serialize to ensure proper format
                                        yield f"data: {json.dumps(json_data)}\n\n"
                                    except (json.JSONDecodeError, Exception) as e:
                                        logger.warning(f"Failed to parse RAGFlow chunk: {e}")
                                        # If we can't parse or validate, forward with proper formatting
                                        yield data_part + "\n\n"
                            elif decoded_chunk.strip() == 'data: [DONE]':
                                # Handle DONE message that might not have proper spacing
                                yield "data: [DONE]\n\n"
                                done_sent = True
                            else:
                                # Forward non-data lines as is
                                yield decoded_chunk
                        except UnicodeDecodeError:
                            # If we can't decode, forward as binary
                            yield chunk
                    
                    # Ensure we always send DONE at the end if not already sent
                    if not done_sent:
                        yield "data: [DONE]\n\n"
                        
        except httpx.HTTPError as e:
            logger.error(f"HTTP Error during RAGFlow API call: {e}")
            # Format HTTP error in OpenAI standard format
            error_response = ChatCompletionChunk(
                id=f"chatcmpl-{uuid.uuid4().hex}",
                choices=[
                    Choice(
                        delta=ChoiceDelta(
                            content=f"HTTP Error during RAGFlow API call: {str(e)}",
                            role="assistant",
                            function_call=None,
                            tool_calls=None,
                            reasoning_content=None
                        ),
                        finish_reason="stop",
                        index=0,
                        logprobs=None
                    )
                ],
                created=int(datetime.now().timestamp()),
                model="ragflow",
                object="chat.completion.chunk",
                system_fingerprint="",
                usage=None
            )
            yield f"data: {error_response.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Unexpected error in streaming: {e}", exc_info=True)
            # Format unexpected error in OpenAI standard format
            error_response = ChatCompletionChunk(
                id=f"chatcmpl-{uuid.uuid4().hex}",
                choices=[
                    Choice(
                        delta=ChoiceDelta(
                            content=f"Unexpected error: {str(e)}",
                            role="assistant",
                            function_call=None,
                            tool_calls=None,
                            reasoning_content=None
                        ),
                        finish_reason="stop",
                        index=0,
                        logprobs=None
                    )
                ],
                created=int(datetime.now().timestamp()),
                model="ragflow",
                object="chat.completion.chunk",
                system_fingerprint="",
                usage=None
            )
            yield f"data: {error_response.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
    
    # 4. Prepare response headers
    response_headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Disable buffering for nginx
        "Content-Type": "text/event-stream"
    }
    
    # 5. Return streaming response
    return StreamingResponse(
        stream_content(),
        status_code=200,
        headers=response_headers,
        media_type="text/event-stream"
    )


@router.post("/qwen-stream")
async def qwen_stream(request: ChatRequest):
    """
    Direct streaming endpoint for Qwen model responses with full OpenAI compatibility
    """
    llm = get_llm()

    async def event_stream():
        try:
            # Create the message
            messages = [HumanMessage(content=request.message)]
            
            # Generate a unique ID for the response
            response_id = f"chatcmpl-{uuid.uuid4().hex}"
            created_time = int(datetime.now().timestamp())
            
            # Stream the response
            async for chunk in llm.astream(messages):
                if chunk.content:
                    # Format response to match OpenAI streaming format
                    # Note: For Qwen, we don't have reasoning_content, so we set it to None
                    delta_dict = {
                        "content": chunk.content,
                        "role": "assistant",
                        "function_call": None,
                        "tool_calls": None,
                        "reasoning_content": None  # Qwen doesn't provide reasoning content
                    }
                    
                    response_data = ChatCompletionChunk(
                        id=response_id,
                        choices=[
                            Choice(
                                delta=ChoiceDelta(**delta_dict),
                                finish_reason=None,
                                index=0,
                                logprobs=None
                            )
                        ],
                        created=created_time,
                        model="qwen",
                        object="chat.completion.chunk",
                        system_fingerprint="fp_0f2a7a3e",
                        usage=None
                    )
                    data_json = response_data.model_dump_json()
                    logger.info(f"qwen-stream Streaming response: {data_json}")
                    yield f"data: {data_json}\n\n"

            # Send end marker with finish_reason
            finish_response = ChatCompletionChunk(
                id=response_id,
                choices=[
                    Choice(
                        delta=ChoiceDelta(
                            content=None,
                            role="assistant",
                            function_call=None,
                            tool_calls=None,
                            reasoning_content=None
                        ),
                        finish_reason="stop",
                        index=0,
                        logprobs=None
                    )
                ],
                created=created_time,
                model="qwen",
                object="chat.completion.chunk",
                system_fingerprint="fp_0f2a7a3e",
                usage=None
            )
            yield f"data: {finish_response.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Error in Qwen streaming: {e}", exc_info=True)
            # Generate unique ID if not exists
            response_id = f"chatcmpl-{uuid.uuid4().hex}"
            created_time = int(datetime.now().timestamp())
            
            error_response = ChatCompletionChunk(
                id=response_id,
                choices=[
                    Choice(
                        delta=ChoiceDelta(
                            content=f"Error in Qwen streaming: {str(e)}",
                            role="assistant",
                            function_call=None,
                            tool_calls=None,
                            reasoning_content=None
                        ),
                        finish_reason="stop",
                        index=0,
                        logprobs=None
                    )
                ],
                created=created_time,
                model="qwen",
                object="chat.completion.chunk",
                system_fingerprint="fp_0f2a7a3e",
                usage=None
            )
            yield f"data: {error_response.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

    # Create response with headers to disable buffering
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
    )


@router.post("/chat-completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    Unified endpoint for chat completions following OpenAI API format
    
    This endpoint provides a unified interface that follows the OpenAI API specification
    for chat completions. It can route requests to different models based on the 
    model parameter in the request.
    
    Args:
        request (ChatCompletionRequest): The request object following OpenAI format
            - model (str): Model name to use for completion
            - messages (List[ChatCompletionMessageParam]): List of messages in the conversation
            - stream (bool): Whether to stream the response
            - extra_body (Optional[Dict[str, Any]]): Additional parameters
            
    Returns:
        StreamingResponse: SSE stream response in OpenAI format
    """
    # For now, we'll implement a simple routing mechanism
    # In a real implementation, this would route to different models based on the model parameter
    
    # Extract the user message from the messages array
    user_message = ""
    for msg in request.messages:
        if msg["role"] == "user":
            user_message = msg["content"]
            break
    
    # If no user message found, use the last message
    if not user_message and request.messages:
        user_message = request.messages[-1]["content"]
    
    # Create a ChatRequest for internal processing
    chat_request = ChatRequest(
        session_id=f"session_{uuid.uuid4().hex[:8]}",
        message=user_message
    )
    
    # For demonstration, we'll route to qwen-stream
    # In a real implementation, this would be based on the model parameter
    llm = get_llm()

    async def event_stream():
        try:
            # Create the message
            messages = [HumanMessage(content=chat_request.message)]
            
            # Generate a unique ID for the response
            response_id = f"chatcmpl-{uuid.uuid4().hex}"
            
            # Stream the response
            async for chunk in llm.astream(messages):
                if chunk.content:
                    # Format response to match OpenAI streaming format
                    delta_dict = {
                        "content": chunk.content,
                        "role": "assistant",
                        "function_call": None,
                        "tool_calls": None,
                        "reasoning_content": None  # Qwen doesn't provide reasoning content
                    }
                    
                    response_data = ChatCompletionChunk(
                        id=response_id,
                        choices=[
                            Choice(
                                delta=ChoiceDelta(**delta_dict),
                                finish_reason=None,
                                index=0,
                                logprobs=None
                            )
                        ],
                        created=int(datetime.now().timestamp()),
                        model=request.model or "qwen",
                        object="chat.completion.chunk",
                        system_fingerprint="",
                        usage=None
                    )
                    yield f"data: {response_data.model_dump_json()}\n\n"

            # Send end marker
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Error in chat completions: {e}", exc_info=True)
            delta_dict = {
                "content": None,
                "role": "assistant",
                "function_call": None,
                "tool_calls": None,
                "reasoning_content": None
            }
            
            error_response = ChatCompletionChunk(
                id=response_id if 'response_id' in locals() else f"chatcmpl-{uuid.uuid4().hex}",
                choices=[
                    Choice(
                        delta=ChoiceDelta(**delta_dict),
                        finish_reason=None,
                        index=0,
                        logprobs=None
                    )
                ],
                created=int(datetime.now().timestamp()),
                model=request.model or "qwen",
                object="chat.completion.chunk",
                system_fingerprint="",
                usage=None
            )
            yield f"data: {error_response.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

    # Create response with headers to disable buffering
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
    )
