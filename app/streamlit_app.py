import streamlit as st
import requests
import json
from typing import Generator

# Streamlit app configuration
st.set_page_config(page_title="PPEC Copilot", page_icon="🤖", layout="wide")

# App title
st.title("🤖 PPEC Copilot")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "您好！我是 PPEC Copilot，您的智能助手。请问有什么我可以帮您的吗？"}]

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Sidebar for settings
st.sidebar.header("设置")
api_url = st.sidebar.text_input("API Base URL", "http://localhost:8000")
stream_enabled = st.sidebar.checkbox("启用流式传输", value=True)

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
        
        if stream_enabled:
            # Streaming response
            try:
                response = requests.post(
                    f"{api_url}/api/v1/ragflow-stream",
                    json={
                        "session_id": "streamlit_session",
                        "message": prompt
                    },
                    stream=True,
                    timeout=60
                )
                response.raise_for_status()
                
                # Create placeholders for different content types
                reasoning_placeholder = st.empty()
                content_placeholder = st.empty()
                
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith('data: '):
                            data_str = decoded_line[6:]  # Remove 'data: ' prefix
                            if data_str == '[DONE]':
                                break
                                
                            try:
                                data = json.loads(data_str)
                                
                                # Handle RAGFlow format
                                if 'choices' in data and len(data['choices']) > 0:
                                    delta = data['choices'][0].get('delta', {})
                                    if 'reasoning_content' in delta and delta['reasoning_content']:
                                        reasoning_content += delta['reasoning_content']
                                        with reasoning_placeholder.container():
                                            st.info(f"**🧠 深度思考:**\n\n{reasoning_content}")
                                    if 'content' in delta and delta['content']:
                                        full_response += delta['content']
                                        content_placeholder.markdown(full_response + "▌")
                                # Handle simplified format
                                elif 'reasoning_content' in data and data['reasoning_content']:
                                    reasoning_content += data['reasoning_content']
                                    with reasoning_placeholder.container():
                                        st.info(f"**🧠 深度思考:**\n\n{reasoning_content}")
                                elif 'content' in data and data['content']:
                                    full_response += data['content']
                                    content_placeholder.markdown(full_response + "▌")
                                    
                            except json.JSONDecodeError:
                                # Handle non-JSON lines
                                continue
                
                # Display final response without cursor
                if reasoning_content:
                    st.info(f"**🧠 深度思考:**\n\n{reasoning_content}")
                content_placeholder.markdown(full_response)
                
            except requests.exceptions.RequestException as e:
                st.error(f"请求出错: {e}")
                full_response = "抱歉，请求出错，请稍后再试。"
                message_placeholder.markdown(full_response)
        else:
            # Non-streaming response (for testing)
            try:
                response = requests.post(
                    f"{api_url}/api/v1/ragflow-stream",
                    json={
                        "session_id": "streamlit_session",
                        "message": prompt
                    },
                    timeout=60
                )
                response.raise_for_status()
                full_response = response.text
                message_placeholder.markdown(full_response)
            except requests.exceptions.RequestException as e:
                st.error(f"请求出错: {e}")
                full_response = "抱歉，请求出错，请稍后再试。"
                message_placeholder.markdown(full_response)
        
        # Add assistant response to session state
        # Combine reasoning and content for session state
        combined_response = ""
        if reasoning_content:
            combined_response += f"**🧠 深度思考:**\n\n{reasoning_content}\n\n"
        if full_response:
            combined_response += f"**回答:**\n\n{full_response}"
            
        st.session_state.messages.append({"role": "assistant", "content": combined_response})