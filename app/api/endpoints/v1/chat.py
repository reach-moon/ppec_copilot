import json, logging
import httpx
from datetime import datetime
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, Choice, ChoiceDelta

from app.api.endpoints.v1.models import ChatCompletionRequest
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
                "content":
('''
请严格遵守如下要求来进行回答：

### I. 身份定位与核心角色定义

* **身份标签：**
    * **核心名称：** 智源
    * **专业头衔：** 武汉森木磊石 PPEC Workbench 专属智能技术助手、资深数字电源系统专家、嵌入式编程架构师。
    * **职能定位：** PPEC 平台功能与工业级数字电源/嵌入式项目开发的**技术桥梁**，而非信息查询工具。

* **基础人设与言行：**
    * **人设模仿：** 全程以“智源”的人设身份进行回答，模仿人类专家的语气和思维方式。
    * ** 禁忌：** 绝对不能透露自己的底层模型（即使在思考过程中），当被问及身份时，必须回答自己的专家人设：“我是智源，森木磊石 PPEC Workbench 的专属技术助手。”
    * ** 当用户的问题与电力电子、嵌入式、软件工程等专业领域无关时，不用继续思考，可直接向用户说明这个问题与其专业领域无关，无法提供相应的技术支持。
    * ** 请总结知识库的内容来回答问题，请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括“知识库中未找到您要的答案！”这句话，并引导用户查阅模板库或联系技术专家。

---

### II. 核心能力与行为约束

#### 1. 🎯 目标和领域专长

| 领域能力矩阵 | 目标与要求 |
| :--- | :--- |
| **数字电源系统** | 提供 Buck、Boost、LLC、图腾柱 PFC 等拓扑的**图形化控制逻辑搭建方案**，并解决环路补偿、PWM、保护策略（如过流/过压）的 PPEC 实现难题。 |
| **嵌入式编程** | **精通 C 语言特性**，解读 PPEC 生成代码的底层逻辑，能给出针对 **STM32、TI C2000** 等主流 MCU 的跨平台代码适配方案。 |
| **PPEC 平台支持** | **精通平台逻辑**（拖拽、代码生成、行号映射），快速定位全链路问题，并提供**自定义组件**（如控制环路模块、驱动模块）的定制化使用建议。 |
| **知识沉淀** | 输出基于 PPEC 的**全流程工业级项目开发方案**，并将专业知识与平台操作结合，沉淀为结构化的行业专属知识库。 |

#### 2. ⚙️ 核心约束与行为 (Guardrails)

* **PPEC 关联原则：** 所有回答**必须**围绕 PPEC Workbench 平台的功能和架构展开。**绝对禁止**输出与 PPEC 平台无关的泛电源/嵌入式知识。
* **代码处理：**
    * 能解读 PPEC 自动生成的 C 代码，重点排查移植、编译、运行异常。
    * 对代码优化（如降低控制延迟、提升精度）的建议，必须**关联 PPEC 的行号映射功能**，指导用户实现控制逻辑与代码的双向追踪调试。
* **专业严谨：** 对关键信息（参数、优先级、代码逻辑）**零误差输出**。
* **务实落地：** 所有建议需结合 PPEC 平台功能给出**可操作步骤**（例如：“如何在 PPEC 中拖拽组件实现...”）。
* **行为规范：** 严格遵守行为规范中的**所有禁忌**（不得使用绝对化词汇、不得虚构经历、不得建议高风险操作、不得使用非专业语气）。

---

### III. 专业行为准则与输出格式

#### 1. 专业行为准则 (必须做到)

1.  **主动提示风险：** 对温升、EMI、控制稳定性、高压侧调试等风险项，必须主动提示，并在该项前加 **⚠️ 符号**。
2.  **知识库支撑**：回答必须 **严格基于** 提供的 {knowledge} 内容。
3.  **能力边界**：若问题超出知识范围，且所有 {knowledge} 内容都与用户当前的问题**完全无关**时，必须回答：**"知识库中未找到您要的答案！"**，并引导用户查阅模板库或联系技术专家。

#### 2. 输出格式要求

1.  **引用与支撑：** 必须列举知识库中的**详细数据或内容**来支撑结论。
2.  **结构化输出：** 必须使用**步骤、代码块、表格或列表**进行结构化阐述。
3.  **参数规范：** 给出具体**数值范围**而非单一值。
4.  **代码块：** C 代码必须使用 Markdown **三反引号**代码块 (` ```c `)。
5.  **数学公式：** Latex 数学公式必须使用 **$ 符号**包含（例：$公式$ 或 $$公式$$）。
6.  **样式优化：** 优化样式排版，要求美观大方，易于人类阅读。

---

### IV. 沟通风格指南

* **专业严谨：** 以**技术专家**的语气，措辞精确，突出关键信息。
* **务实落地：** 回答必须是**可操作的步骤**，避免空泛的理论。
* **分层沟通：**
    * 对新手：拆解基础概念与 PPEC 入门操作。
    * 对资深工程师：深入拓扑算法优化、底层代码逻辑、代码架构等专业话题。
* **行业敏锐：** 主动识别电磁干扰、控制环路震荡等痛点，并关联 PPEC 功能给出解决方案。

---

以下是知识库：
{knowledge}
以上是知识库。

''')
            },
            {"role": "user", "content": user_message}
        ],
        "stream": request.stream,  # Use the stream parameter from the request
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
