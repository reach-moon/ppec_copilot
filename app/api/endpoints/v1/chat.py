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
from app.schemas.tool_calling import ToolCallingRequest
from config.settings import settings

logger = logging.getLogger(__name__)

# 创建 API 路由器实例
router = APIRouter()


# @router.post("/chat")
# async def stream_chat(request: ChatRequest):
#     """
#     流式处理聊天请求的主要端点。
#     
#     该函数通过session_id找到对应的Agent，并由该Agent处理请求。
#     每个session_id对应一个独立的Agent实例，用于维护会话状态。
#
#     Args:
#         request (ChatRequest): 包含用户消息和会话ID的请求对象
#             - session_id (str): 唯一的会话标识符，用于检索和存储对话历史
#             - message_id (Optional[str]): 交互ID，用于标识单次用户请求
#             - message (str): 用户的输入消息
#
#     Returns:
#         StreamingResponse: 一个SSE流响应，由对应的Agent生成
#     """
#     # 获取对应session_id的Agent实例
#     agent = agent_manager.get_agent(request.session_id)
#
#     # 由Agent处理请求并返回流式响应
#     return await agent.process_request(request.message, request.message_id)


@router.post("/ragflow-stream")
async def ragflow_stream(request: ChatCompletionRequest):
    """
    Direct proxy endpoint for RAGFlow API with full OpenAI compatibility
    
    Args:
        request (ChatCompletionRequest): The request object following OpenAI format
            - model (str): Model name to use for completion
            - messages (List[ChatCompletionMessageParam]): List of messages in the conversation
            - stream (bool): Whether to stream the response
            - extra_body (Optional[Dict[str, Any]]): Additional parameters
            
    Returns:
        StreamingResponse or JSONResponse: SSE stream response or JSON response in OpenAI format
    """
    # Extract user message from messages
    user_message = ""
    for msg in request.messages:
        if msg["role"] == "user":
            user_message = msg["content"]
            break
    
    # If no user message found, use the last message
    if not user_message and request.messages:
        user_message = request.messages[-1]["content"]
    
    logger.info(f"Starting RAGFlow processing for message: {user_message[:50]}...")
    
    # 1. Construct the complete RAGFlow API URL
    url = settings.RAGFLOW_API_URL + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.RAGFLOW_API_KEY}"
    }
    
    # 2. Construct RAGFlow/OpenAI compatible request payload
    payload = {
        "model": request.model if request.model != "model" else "default-model",
        "messages": [
            {   
                "role": "system",
                "content": (
                    "你是一个智能助手，请总结知识库的内容来回答问题，请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括'知识库中未找到您要的答案！'这句话。回答需要考虑聊天历史，同时一定要注意优化返回的内容样式排版，要求美观大方，易于人类阅读。"
                )
            },
            {"role": "user", "content": user_message}
        ],
        "stream": request.stream,  # Use the stream parameter from the request
        "extra_body": request.extra_body or {"reference": True}
    }
    
    logger.info(f"Sending request to RAGFlow API: {url}")
    logger.debug(f"Request payload: {payload}")
    
    if request.stream:
        # 3. Create custom async generator for streaming proxy
        async def stream_content():
            done_sent = False
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream('POST', url, json=payload, headers=headers) as ragflow_response:
                        logger.info(f"RAGFlow API response status: {ragflow_response.status_code}")
                        
                        # Log response headers
                        logger.debug(f"RAGFlow API response headers: {dict(ragflow_response.headers)}")
                        
                        # Check response status code
                        if ragflow_response.status_code != 200:
                            # Try to read error content
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
    else:
        # Non-streaming response
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                ragflow_response = await client.post(url, json=payload, headers=headers)
                
                if ragflow_response.status_code != 200:
                    # Handle error response
                    error_msg = ragflow_response.text
                    logger.error(f"RAGFlow API error: {error_msg}")
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=ragflow_response.status_code,
                        detail={
                            "code": ragflow_response.status_code,
                            "message": f"RAGFlow API Error: {error_msg}"
                        }
                    )
                
                # Return the response directly as JSON
                response_data = ragflow_response.json()
                return response_data
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP Error during RAGFlow API call: {e}")
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail={
                    "code": 500,
                    "message": f"HTTP Error during RAGFlow API call: {str(e)}"
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error in non-streaming response: {e}", exc_info=True)
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail={
                    "code": 500,
                    "message": f"Unexpected error: {str(e)}"
                }
            )


@router.post("/llm-stream")
async def llm_stream(request: ChatCompletionRequest):
    """
    Direct streaming endpoint for LLM model responses with full OpenAI compatibility.
    Can be configured to work with different models via the model parameter.
    
    Args:
        request (ChatCompletionRequest): The request object following OpenAI format
            - model (str): Model name to use for completion (e.g., "qwen", "gpt-3.5-turbo")
            - messages (List[ChatCompletionMessageParam]): List of messages in the conversation
            - stream (bool): Whether to stream the response
            - extra_body (Optional[Dict[str, Any]]): Additional parameters for model configuration
            
    Returns:
        StreamingResponse or JSONResponse: SSE stream response or JSON response in OpenAI format
    """
    logger.info(f"Starting LLM processing for model: {request.model}, message: {request.messages[-1]['content'][:50]}...")
    
    # Extract the user message (for backward compatibility with simple message handling)
    user_message = ""
    messages_for_llm = []
    
    for msg in request.messages:
        messages_for_llm.append(msg)
        if msg["role"] == "user":
            user_message = msg["content"]
    
    # If no user message found, use the last message
    if not user_message and request.messages:
        user_message = request.messages[-1]["content"]
        messages_for_llm = [{"role": "user", "content": user_message}]
    
    # Get the appropriate LLM based on the model parameter
    llm = get_llm(model_name=request.model if request.model != "model" else "qwen")

    # Generate a unique ID for the response
    response_id = f"chatcmpl-{uuid.uuid4().hex}"
    created_time = int(datetime.now().timestamp())
    
    # Convert messages to LangChain format
    langchain_messages = []
    for msg in messages_for_llm:
        if msg["role"] == "user":
            langchain_messages.append(HumanMessage(content=msg["content"]))
        # Add other roles as needed

    if request.stream:
        # Streaming response
        async def event_stream():
            response_id = f"chatcmpl-{uuid.uuid4().hex}"
            created_time = int(datetime.now().timestamp())
            try:
                # Stream the response
                async for chunk in llm.astream(langchain_messages):
                    if chunk.content:
                        # Format response to match OpenAI streaming format
                        delta_dict = {
                            "content": chunk.content,
                            "role": "assistant",
                            "function_call": None,
                            "tool_calls": None,
                            "reasoning_content": None  # Standard LLMs don't provide reasoning content
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
                            model=request.model or "qwen",
                            object="chat.completion.chunk",
                            system_fingerprint="fp_0f2a7a3e",
                            usage=None
                        )
                        yield f"data: {response_data.model_dump_json()}\n\n"

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
                    model=request.model or "qwen",
                    object="chat.completion.chunk",
                    system_fingerprint="fp_0f2a7a3e",
                    usage=None
                )
                yield f"data: {finish_response.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Error in LLM streaming: {e}", exc_info=True)
                # Generate unique ID if not exists
                response_id = f"chatcmpl-{uuid.uuid4().hex}"
                created_time = int(datetime.now().timestamp())
                
                error_response = ChatCompletionChunk(
                    id=response_id,
                    choices=[
                        Choice(
                            delta=ChoiceDelta(
                                content=f"Error in LLM streaming: {str(e)}",
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
                    model=request.model or "qwen",
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
    else:
        # Non-streaming response
        try:
            # Get the full response
            response = await llm.ainvoke(langchain_messages)
            
            # Count tokens (simplified)
            prompt_tokens = sum(len(msg.content) for msg in langchain_messages if hasattr(msg, 'content'))
            completion_tokens = len(response.content) if hasattr(response, 'content') else 0
            
            # Format response to match OpenAI non-streaming format
            from openai.types.chat.chat_completion import ChatCompletion, Choice as ChatCompletionChoice
            from openai.types.chat.chat_completion_message import ChatCompletionMessage
            
            chat_completion = ChatCompletion(
                id=response_id,
                choices=[
                    ChatCompletionChoice(
                        finish_reason="stop",
                        index=0,
                        logprobs=None,
                        message=ChatCompletionMessage(
                            content=response.content if hasattr(response, 'content') else str(response),
                            role="assistant",
                            function_call=None,
                            tool_calls=None
                        )
                    )
                ],
                created=created_time,
                model=request.model or "qwen",
                object="chat.completion",
                system_fingerprint="fp_0f2a7a3e",
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            )
            
            return chat_completion
            
        except Exception as e:
            logger.error(f"Error in LLM non-streaming response: {e}", exc_info=True)
            # Return error in proper format
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail={
                    "code": 500,
                    "message": f"Error in LLM processing: {str(e)}"
                }
            )


@router.post("/tool-calling")
async def tool_calling_endpoint(request: ToolCallingRequest):
    """
    Unified endpoint for tool calling with full OpenAI compatibility.
    
    This endpoint provides a standardized interface that follows the OpenAI API specification
    for chat completions with tool calling capabilities. It can route requests to different 
    models based on the model parameter in the request.
    
    Args:
        request (ToolCallingRequest): The request object following OpenAI format with tool calling support
            - model (str): Model name to use for completion
            - messages (List[ChatCompletionMessageParam]): List of messages in the conversation
            - tools (Optional[List[Dict[str, Any]]]): List of tools available to the model
            - tool_choice (Optional[Union[str, Dict[str, Any]]]): How to select tools
            - stream (bool): Whether to stream the response
            - extra_body (Optional[Dict[str, Any]]): Additional parameters
            
    Returns:
        StreamingResponse or JSONResponse: SSE stream response or JSON response in OpenAI format
    """
    logger.info(f"Starting tool calling for model: {request.model}")
    
    # Convert ToolCallingRequest to ChatCompletionRequest for compatibility with existing llm_stream
    chat_request = ChatCompletionRequest(
        model=request.model,
        messages=request.messages,
        stream=request.stream,
        extra_body=request.extra_body
    )
    
    # Use the existing llm_stream function for now
    # In the future, this could be enhanced to specifically handle tool calling
    return await llm_stream(chat_request)


@router.post("/chat/completions")
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
        StreamingResponse or JSONResponse: SSE stream response or JSON response in OpenAI format
    """
    # Route to appropriate backend based on model
    return await ragflow_stream(request)
    
    # if "ragflow" in request.model.lower():
    #     # For ragflow, directly call the ragflow_stream function
    #     return await ragflow_stream(request)
    # else:
    #     # For other models, use the llm_stream endpoint
    #     return await llm_stream(request)


# @router.post("/qwen-stream")
# async def qwen_stream(request: ChatRequest):
#     """
#     Backward compatibility endpoint for Qwen streaming.
#     Direct streaming endpoint for Qwen model responses with full OpenAI compatibility.
#
#     Args:
#         request (ChatRequest): 包含用户消息和会话ID的请求对象
#             - session_id (str): 唯一的会话标识符
#             - turn_id (Optional[str]): 交互ID
#             - message (str): 用户的输入消息
#
#     Returns:
#         StreamingResponse: SSE流响应，遵循OpenAI格式
#     """
#     logger.info(f"Starting Qwen stream for message: {request.message[:50]}...")
#
#     # Create a ChatCompletionRequest for compatibility with llm_stream
#     chat_completion_request = ChatCompletionRequest(
#         model="qwen",
#         messages=[{"role": "user", "content": request.message}],
#         stream=True  # Always stream for backward compatibility
#     )
#
#     # Use the llm_stream function for processing
#     return await llm_stream(chat_completion_request)


# @router.post("/ragflow-stream-old")
# async def ragflow_stream_old(request: ChatRequest):
#     """
#     Backward compatibility endpoint for RAGFlow streaming.
#     Direct proxy endpoint for RAGFlow API with full OpenAI compatibility.
#
#     Args:
#         request (ChatRequest): 包含用户消息和会话ID的请求对象
#             - session_id (str): 唯一的会话标识符
#             - turn_id (Optional[str]): 交互ID
#             - message (str): 用户的输入消息
#
#     Returns:
#         StreamingResponse: SSE流响应，遵循OpenAI格式
#     """
#     logger.info(f"Starting RAGFlow stream for message: {request.message[:50]}...")
#
#     # Create a ChatCompletionRequest for compatibility with ragflow_stream
#     chat_completion_request = ChatCompletionRequest(
#         model="ragflow",
#         messages=[{"role": "user", "content": request.message}],
#         stream=True,  # Always stream for backward compatibility
#         extra_body={"reference": True}
#     )
#
#     # Use the ragflow_stream function for processing
#     return await ragflow_stream(chat_completion_request)
