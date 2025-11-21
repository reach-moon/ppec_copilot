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


def test_ragflow_stream_format():
    """Test that ragflow-stream returns the correct OpenAI format"""
    
    # Mock the httpx response to simulate RAGFlow API
    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {"content-type": "text/event-stream"}
        
        async def aiter_bytes(self):
            # Simulate RAGFlow response chunks
            chunks = [
                {
                    "id": "chatcmpl-test123",
                    "choices": [{
                        "delta": {
                            "content": None,
                            "role": "assistant",
                            "function_call": None,
                            "tool_calls": None,
                            "reasoning_content": "思考"
                        },
                        "finish_reason": None,
                        "index": 0,
                        "logprobs": None
                    }],
                    "created": 1763635033,
                    "model": "model",
                    "object": "chat.completion.chunk",
                    "system_fingerprint": "",
                    "usage": None
                },
                {
                    "id": "chatcmpl-test123",
                    "choices": [{
                        "delta": {
                            "content": "你好",
                            "role": "assistant",
                            "function_call": None,
                            "tool_calls": None,
                            "reasoning_content": None
                        },
                        "finish_reason": None,
                        "index": 0,
                        "logprobs": None
                    }],
                    "created": 1763635034,
                    "model": "model",
                    "object": "chat.completion.chunk",
                    "system_fingerprint": "",
                    "usage": None
                }
            ]
            
            for chunk in chunks:
                yield f"data: {json.dumps(chunk)}\n\n".encode('utf-8')
            yield b"data: [DONE]\n\n"
        
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Patch the httpx.AsyncClient.stream method
    with patch('httpx.AsyncClient.stream', return_value=MockResponse()):
        response = client.post(
            "/api/v1/ragflow-stream",
            json={
                "session_id": "test_session",
                "message": "Hello"
            }
        )
        
        # Check that the response is successful
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
        
        # Check the response content format
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n\n')
        
        # Should have 3 lines: 2 data chunks + DONE
        assert len(lines) >= 2
        
        # Check first chunk (reasoning)
        assert lines[0].startswith('data: ')
        first_data = json.loads(lines[0][6:])  # Remove 'data: ' prefix
        
        # Validate against OpenAI ChatCompletionChunk model
        chunk = ChatCompletionChunk(**first_data)
        assert chunk.id == "chatcmpl-test123"
        assert chunk.object == "chat.completion.chunk"
        assert chunk.choices[0].delta.reasoning_content == "思考"
        assert chunk.choices[0].delta.content is None
        
        # Check second chunk (content)
        assert lines[1].startswith('data: ')
        second_data = json.loads(lines[1][6:])  # Remove 'data: ' prefix
        
        # Validate against OpenAI ChatCompletionChunk model
        chunk = ChatCompletionChunk(**second_data)
        assert chunk.id == "chatcmpl-test123"
        assert chunk.object == "chat.completion.chunk"
        assert chunk.choices[0].delta.content == "你好"
        assert chunk.choices[0].delta.reasoning_content is None


def test_qwen_stream_format():
    """Test that qwen-stream returns the correct OpenAI format"""
    
    # Mock the LLM response
    mock_llm = MagicMock()
    mock_chunk1 = MagicMock()
    mock_chunk1.content = "你好"
    
    # Make the astream method return our mock chunks
    mock_llm.astream = MagicMock(return_value=async_generator([mock_chunk1]))
    
    with patch('app.api.endpoints.v1.chat.get_llm', return_value=mock_llm):
        response = client.post(
            "/api/v1/qwen-stream",
            json={
                "session_id": "test_session",
                "message": "Hello"
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
        # Qwen doesn't provide reasoning content
        assert chunk.choices[0].delta.reasoning_content is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])