import streamlit as st
import requests
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any

# Streamlit app configuration
st.set_page_config(page_title="PPEC Copilot - Streamlit Client", page_icon="🤖", layout="wide")

# App title
st.title("🤖 PPEC Copilot - Streamlit Client")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "您好！我是 PPEC Copilot，您的智能助手。请问有什么我可以帮您的吗？"}]

# Sidebar for settings
st.sidebar.header("⚙️ 设置")
base_url = st.sidebar.text_input("Backend API URL", "http://127.0.0.1:8000")
endpoint = st.sidebar.selectbox("选择接口", [
    "/api/v1/ragflow-stream", 
    "/api/v1/chat/completions"
])
stream_enabled = st.sidebar.checkbox("启用流式传输", value=True)
session_id = st.sidebar.text_input("会话 ID", "streamlit_session")
model_name = st.sidebar.text_input("模型名称", "qwen")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("请输入您的问题..."):
    # Add user message to session state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Add assistant response to session state
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        reasoning_content = ""
        assistant_message_container = None
        reasoning_container = None
        
        if stream_enabled:
            # Streaming response
            try:
                with st.spinner("正在获取回答..."):
                    if endpoint == "/api/v1/chat/completions" or endpoint == "/api/v1/ragflow-stream":
                        # 使用新的统一接口格式
                        response = requests.post(
                            f"{base_url}{endpoint}",
                            json={
                                "model": model_name,
                                "messages": [
                                    {"role": "user", "content": prompt}
                                ],
                                "stream": True
                            },
                            stream=True,
                            timeout=60
                        )
                    else:
                        # 使用原有的接口格式
                        response = requests.post(
                            f"{base_url}{endpoint}",
                            json={
                                "session_id": session_id,
                                "message": prompt
                            },
                            stream=True,
                            timeout=60
                        )
                    response.raise_for_status()
                    
                    for line in response.iter_lines():
                        if line:
                            try:
                                decoded_line = line.decode('utf-8')
                                if decoded_line.startswith('data: '):
                                    data_str = decoded_line[6:]  # Remove 'data: ' prefix
                                    if data_str == '[DONE]':
                                        continue
                                        
                                    try:
                                        data = json.loads(data_str)
                                        
                                        # Handle OpenAI format (with choices and delta)
                                        if 'choices' in data and len(data['choices']) > 0:
                                            delta = data['choices'][0].get('delta', {})
                                            
                                            # Handle reasoning_content
                                            if 'reasoning_content' in delta and delta['reasoning_content']:
                                                reasoning_content += delta['reasoning_content']
                                                # Create or update reasoning container
                                                if reasoning_container is None:
                                                    reasoning_container = st.empty()
                                                reasoning_container.info(f"**🧠 深度思考:**\n\n{reasoning_content}")
                                            
                                            # Handle content
                                            if 'content' in delta and delta['content']:
                                                full_response += delta['content']
                                                # Create or update assistant message container
                                                if assistant_message_container is None:
                                                    assistant_message_container = st.empty()
                                                assistant_message_container.markdown(full_response + "▌")
                                        # Handle simple format for backward compatibility
                                        elif 'content' in data and data['content']:
                                            full_response += data['content']
                                            # Create or update assistant message container
                                            if assistant_message_container is None:
                                                assistant_message_container = st.empty()
                                            assistant_message_container.markdown(full_response + "▌")
                                            
                                    except json.JSONDecodeError:
                                        # Handle non-JSON lines
                                        continue
                            except Exception as e:
                                st.error(f"处理流数据时出错: {e}")
                                break
                
                # Finalize the response without cursor
                if assistant_message_container is not None:
                    assistant_message_container.markdown(full_response)
                
            except requests.exceptions.RequestException as e:
                st.error(f"请求出错: {e}")
                full_response = "抱歉，请求出错，请稍后再试。"
                if assistant_message_container is None:
                    assistant_message_container = st.empty()
                assistant_message_container.markdown(full_response)
        else:
            # Non-streaming response
            try:
                if endpoint == "/api/v1/chat/completions" or endpoint == "/api/v1/ragflow-stream":
                    # 使用新的统一接口格式
                    response = requests.post(
                        f"{base_url}{endpoint}",
                        json={
                            "model": model_name,
                            "messages": [
                                {"role": "user", "content": prompt}
                            ],
                            "stream": False
                        },
                        timeout=60
                    )
                else:
                    # 使用原有的接口格式
                    response = requests.post(
                        f"{base_url}{endpoint}",
                        json={
                            "session_id": session_id,
                            "message": prompt
                        },
                        timeout=60
                    )
                response.raise_for_status()
                # For non-streaming, we just display the full response
                full_response = response.text
                if assistant_message_container is None:
                    assistant_message_container = st.empty()
                assistant_message_container.markdown(full_response)
            except requests.exceptions.RequestException as e:
                st.error(f"请求出错: {e}")
                full_response = "抱歉，请求出错，请稍后再试。"
                if assistant_message_container is None:
                    assistant_message_container = st.empty()
                assistant_message_container.markdown(full_response)
        
        # Add assistant response to session state
        # Combine reasoning and content for session state
        combined_response = ""
        if reasoning_content:
            combined_response += f"**🧠 深度思考:**\n\n{reasoning_content}\n\n"
        if full_response:
            combined_response += f"**回答:**\n\n{full_response}"
            
        st.session_state.messages.append({"role": "assistant", "content": combined_response})

# Add a button to clear chat history
if st.sidebar.button("清空聊天记录"):
    st.session_state.messages = [{"role": "assistant", "content": "您好！我是 PPEC Copilot，您的智能助手。请问有什么我可以帮您的吗？"}]
    st.rerun()