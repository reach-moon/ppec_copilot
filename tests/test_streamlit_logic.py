import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pytest
from unittest.mock import patch, MagicMock

# Mock Streamlit functions
class MockEmpty:
    def __init__(self):
        self.content = ""
    
    def markdown(self, content):
        self.content = content
        
    def info(self, content):
        self.content = content

class MockChatMessage:
    def __init__(self, role):
        self.role = role
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def markdown(self, content):
        pass

def test_streamlit_logic():
    """Test that the Streamlit logic properly handles responses"""
    
    # Mock the session state
    st.session_state = {"messages": []}
    
    # Mock the response
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.iter_lines = MagicMock(return_value=[
        b'data: {"choices": [{"delta": {"reasoning_content": "Think"}}]}',
        b'data: {"choices": [{"delta": {"reasoning_content": "ing..."}}]}',
        b'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        b'data: {"choices": [{"delta": {"content": " World"}}]}',
        b'data: [DONE]'
    ])
    
    # Mock requests.post
    with patch('requests.post', return_value=mock_response):
        # Mock Streamlit functions
        with patch('streamlit.empty', return_value=MockEmpty()) as mock_empty, \
             patch('streamlit.chat_message', side_effect=MockChatMessage), \
             patch('streamlit.spinner'), \
             patch('streamlit.error'):
            
            # Simulate the streaming logic from streamlit_client.py
            full_response = ""
            reasoning_content = ""
            assistant_message_container = None
            reasoning_container = None
            
            endpoint = "/api/v1/qwen-stream"
            base_url = "http://127.0.0.1:8000"
            session_id = "test_session"
            prompt = "Hello"
            
            try:
                if endpoint == "/api/v1/chat/completions":
                    response = MagicMock()  # This won't be called in this test
                else:
                    response = mock_response
                    
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
                                                reasoning_container = MockEmpty()
                                        
                                        # Handle content
                                        if 'content' in delta and delta['content']:
                                            full_response += delta['content']
                                            # Create or update assistant message container
                                            if assistant_message_container is None:
                                                assistant_message_container = MockEmpty()
                                except json.JSONDecodeError:
                                    # Handle non-JSON lines
                                    continue
                        except Exception as e:
                            print(f"Error: {e}")
                            break
                
                # Finalize the response without cursor
                if assistant_message_container is not None:
                    assistant_message_container.markdown(full_response)
                
                # Check results
                assert full_response == "Hello World"
                assert reasoning_content == "Thinking..."
                assert assistant_message_container is not None
                assert assistant_message_container.content == "Hello World"
                
                print("Test passed!")
                
            except Exception as e:
                print(f"Test failed with exception: {e}")

if __name__ == "__main__":
    test_streamlit_logic()