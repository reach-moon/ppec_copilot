import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.api.main import app
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

client = TestClient(app)


# Async iterator helper
async def async_generator(items):
    for item in items:
        yield item


def test_chat_completions_endpoint():
    """Test the new unified chat-completions endpoint"""
    
    # Mock the LLM response
    mock_llm = MagicMock()
    mock_chunk1 = MagicMock()
    mock_chunk1.content = "你好"
    
    # Make the astream method return our mock chunks
    mock_llm.astream = MagicMock(return_value=async_generator([mock_chunk1]))
    
    with patch('app.api.endpoints.v1.chat.get_llm', return_value=mock_llm):
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "model": "qwen",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "stream": True
            }
        )
        
        # Check that the response is successful
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        # Check the response content
        content = response.content.decode('utf-8')
        assert 'data: ' in content
        assert 'data: [DONE]' in content
        
        # Extract and validate JSON data
        lines = content.strip().split('\n\n')
        json_lines = [line for line in lines if line.startswith('data: ') and not line == 'data: [DONE]']
        assert len(json_lines) >= 1
        
        # Validate the format of the first data line
        first_data = json.loads(json_lines[0][6:])  # Remove 'data: ' prefix
        chunk = ChatCompletionChunk(**first_data)
        
        assert chunk.object == "chat.completion.chunk"
        assert chunk.choices[0].delta.content == "你好"
        assert chunk.choices[0].delta.role == "assistant"
        assert chunk.model == "qwen"


def test_chat_completions_endpoint_with_no_user_message():
    """Test the chat-completions endpoint when no user message is provided"""
    
    # Mock the LLM response
    mock_llm = MagicMock()
    mock_chunk1 = MagicMock()
    mock_chunk1.content = "你好"
    
    # Make the astream method return our mock chunks
    mock_llm.astream = MagicMock(return_value=async_generator([mock_chunk1]))
    
    with patch('app.api.endpoints.v1.chat.get_llm', return_value=mock_llm):
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "model": "qwen",
                "messages": [
                    {"role": "assistant", "content": "Previous assistant message"}
                ],
                "stream": True
            }
        )
        
        # Check that the response is successful
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])