import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import asyncio

from app.api.main import app

client = TestClient(app)


# Async iterator helper
async def async_generator(items):
    for item in items:
        yield item


# Async mock response
async def async_mock_response():
    mock_response = MagicMock()
    mock_response.content = "Hello, this is a non-streaming response."
    return mock_response


def test_llm_non_streaming_response():
    """Test the llm-stream endpoint with stream=False"""
    
    # Mock the LLM response
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Hello, this is a non-streaming response."
    
    # Make the ainvoke method return our mock response
    async def mock_ainvoke(*args, **kwargs):
        return mock_response
    
    mock_llm.ainvoke = mock_ainvoke
    
    with patch('app.api.endpoints.v1.chat.get_llm', return_value=mock_llm):
        response = client.post(
            "/api/v1/llm-stream",
            json={
                "model": "qwen",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "stream": False
            }
        )
        
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response content: {response.text}")
        
        # Check that the response is successful
        assert response.status_code == 200
        
        # Check that the response is JSON (not streaming)
        assert "application/json" in response.headers["content-type"]
        
        # Parse the JSON response
        response_data = response.json()
        
        # Check the structure of the response
        assert "id" in response_data
        assert "choices" in response_data
        assert "created" in response_data
        assert "model" in response_data
        assert "object" in response_data
        assert response_data["object"] == "chat.completion"
        
        # Check the choices structure
        assert len(response_data["choices"]) == 1
        choice = response_data["choices"][0]
        assert "finish_reason" in choice
        assert "index" in choice
        assert "message" in choice
        assert choice["finish_reason"] == "stop"
        
        # Check the message structure
        message = choice["message"]
        assert "content" in message
        assert "role" in message
        assert message["role"] == "assistant"
        assert message["content"] == "Hello, this is a non-streaming response."


def test_chat_completions_non_streaming():
    """Test the chat/completions endpoint with stream=False"""
    
    # Mock the LLM response
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "This is a response from chat completions endpoint."
    
    # Make the ainvoke method return our mock response
    async def mock_ainvoke(*args, **kwargs):
        return mock_response
    
    mock_llm.ainvoke = mock_ainvoke
    
    with patch('app.api.endpoints.v1.chat.get_llm', return_value=mock_llm):
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "model": "qwen-test",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "stream": False
            }
        )
        
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response content: {response.text}")
        
        # Check that the response is successful
        assert response.status_code == 200
        
        # Check that the response is JSON (not streaming)
        assert "application/json" in response.headers["content-type"]
        
        # Parse the JSON response
        response_data = response.json()
        
        # Check the structure of the response
        assert "id" in response_data
        assert "choices" in response_data
        assert "created" in response_data
        assert "model" in response_data
        assert "object" in response_data
        assert response_data["object"] == "chat.completion"
        
        # Check that the model name is correct
        assert response_data["model"] == "qwen-test"
        
        # Check the message content
        message = response_data["choices"][0]["message"]
        assert message["content"] == "This is a response from chat completions endpoint."


def test_qwen_stream_non_streaming():
    """Test the qwen-stream endpoint with stream=False (backward compatibility)"""
    
    # Mock the LLM response
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "This is a response from the Qwen stream endpoint."
    
    # Make the ainvoke method return our mock response
    async def mock_ainvoke(*args, **kwargs):
        return mock_response
    
    mock_llm.ainvoke = mock_ainvoke
    
    with patch('app.api.endpoints.v1.chat.get_llm', return_value=mock_llm):
        response = client.post(
            "/api/v1/qwen-stream",
            json={
                "session_id": "test-session",
                "turn_id": "test-turn",
                "message": "Hello"
            }
        )
        
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response content: {response.text}")
        
        # Check that the response is successful
        assert response.status_code == 200
        
        # Check that the response is JSON (not streaming)
        assert "application/json" in response.headers["content-type"]
        
        # Parse the JSON response
        response_data = response.json()
        
        # Check the structure of the response
        assert "id" in response_data
        assert "choices" in response_data
        assert "created" in response_data
        assert "model" in response_data
        assert "object" in response_data
        assert response_data["object"] == "chat.completion"
        
        # Check that the model name is correct
        assert response_data["model"] == "qwen"
        
        # Check the message content
        message = response_data["choices"][0]["message"]
        assert message["content"] == "This is a response from the Qwen stream endpoint."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])