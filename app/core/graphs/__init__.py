from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# 配置参数
model = "model"
api_key = "ragflow-jubLI6vjMitU2tzMx4K0c2_jB4zTsBMLaDnHT8NWD38"
base_url = f"http://212.64.10.189:1080/api/v1/chats_openai/86936f54c47f11f097350242ac150006"
stream = True
reference = True

# 初始化 ChatOpenAI 实例
chat = ChatOpenAI(
    model_name=model,  # 对应原model参数
    openai_api_key=api_key,  # 对应原api_key
    openai_api_base=base_url,  # 对应原base_url
    streaming=stream,  # 启用流式响应
    temperature=0  # 可根据需求调整
)

# 构造消息列表（使用langchain的消息类型）
messages = [
    SystemMessage(content="You are a professional technical assistant. Please provide concise and clear answers. When searching for information, do not display your search process or intermediate thoughts. Provide only the final polished answer. If you need to reference sources, include them at the end of your response in a separate section called 'References'."),
    HumanMessage(content="什么是数字电源?"),
]

def safe_get_raw_response(obj):
    """安全地获取原始响应数据"""
    try:
        if hasattr(obj, 'response_metadata'):
            return obj.response_metadata.get("raw")
    except (AttributeError, KeyError, TypeError):
        pass
    return None

def safe_get_attribute(obj, attr_path):
    """安全地获取嵌套属性"""
    try:
        attrs = attr_path.split('.')
        result = obj
        for attr in attrs:
            result = getattr(result, attr)
        return result
    except (AttributeError, TypeError):
        return None

def extract_content_from_chunk(chunk):
    """从chunk中提取内容，支持content和reasoning_content字段"""
    content = ""
    
    # 尝试获取常规内容
    if hasattr(chunk, 'content'):
        content = chunk.content
    
    # 如果常规内容为空，尝试获取reasoning_content
    if not content and hasattr(chunk, 'delta'):
        delta = chunk.delta
        if hasattr(delta, 'content') and delta.content:
            content = delta.content
        elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
            content = delta.reasoning_content
    
    return content

if stream:
    # 流式响应处理
    for chunk in chat.stream(messages, extra_body={"reference": reference}):
        # 从chunk中提取内容
        content = extract_content_from_chunk(chunk)
        if content:
            print(f"Content: {content}")  # 输出内容
        else:
            print(chunk)  # 如果没有内容，则打印整个chunk对象

        # 安全地获取原始响应数据
        raw_chunk = safe_get_raw_response(chunk)
        if raw_chunk:
            # 处理结束标识和引用信息
            finish_reason = safe_get_attribute(raw_chunk, "choices.0.finish_reason")
            if reference and finish_reason == "stop":
                reference_data = safe_get_attribute(raw_chunk, "choices.0.delta.reference")
                if reference_data:
                    print(f"Reference:\n{reference_data}")
                
                final_content = safe_get_attribute(raw_chunk, "choices.0.delta.final_content")
                if final_content:
                    print(f"Final content:\n{final_content}")
        else:
            # 如果没有原始响应数据，直接使用chunk的属性
            chunk_content = getattr(chunk, 'content', 'No content available')
            if chunk_content:
                print(f"Chunk content: {chunk_content}")
else:
    # 非流式响应处理
    response = chat.invoke(messages, extra_body={"reference": reference})
    content = extract_content_from_chunk(response)
    if content:
        print(content)
    else:
        print(getattr(response, 'content', 'No content available'))  # 回答内容

    # 安全地获取原始响应中的引用信息
    if reference:
        raw_response = safe_get_raw_response(response)
        if raw_response:
            reference_data = safe_get_attribute(raw_response, "choices.0.message.reference")
            if reference_data:
                print(reference_data)