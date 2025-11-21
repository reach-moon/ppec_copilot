import pytest
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_tool_calling_endpoint():
    """Test the new tool-calling endpoint"""
    
    # Test data
    test_request = {
        "model": "qwen",
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "stream": True
    }
    
    # Make request to the tool-calling endpoint
    response = client.post(
        "/api/v1/tool-calling",
        json=test_request
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    

def async_generator(items):
    """Helper function to create an async generator from a list"""
    async def gen():
        for item in items:
            yield item
    return gen()


@pytest.mark.asyncio
async def test_qwen_stream_endpoint():
    """Test the qwen-stream endpoint for backward compatibility"""
    
    # Mock the LLM response
    mock_llm = MagicMock()
    mock_chunk1 = MagicMock()
    mock_chunk1.content = "Hello! I'm doing well, thank you for asking."
    
    # Make the astream method return our mock chunks
    mock_llm.astream = MagicMock(return_value=async_generator([mock_chunk1]))
    
    with patch('app.api.endpoints.v1.chat.get_llm', return_value=mock_llm):
        response = client.post(
            "/api/v1/qwen-stream",
            json={
                "session_id": "test-session",
                "turn_id": "test-turn",
                "message": "Hello"
            }
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")
        
        # Check that the response is successful
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_llm_stream_with_model_parameter():
    """Test the llm-stream endpoint with model parameter"""
    
    # Mock the LLM response
    mock_llm = MagicMock()
    mock_chunk1 = MagicMock()
    mock_chunk1.content = "This is a test response from the LLM."
    
    # Make the astream method return our mock chunks
    mock_llm.astream = MagicMock(return_value=async_generator([mock_chunk1]))
    
    with patch('app.api.endpoints.v1.chat.get_llm', return_value=mock_llm):
        response = client.post(
            "/api/v1/llm-stream",
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