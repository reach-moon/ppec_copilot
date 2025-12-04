import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.api.main import app
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

client = TestClient(app)


def test_ragflow_stream_proper_format():
    """Test that ragflow-stream properly formats the response"""
    
    # Mock the httpx response to simulate RAGFlow API with actual format
    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {"content-type": "text/event-stream"}
        
        async def aiter_bytes(self):
            # Simulate actual RAGFlow response chunks with the exact format you mentioned
            chunks = [
                b'data: {"id": "chatcmpl-86936f54c47f11f097350242ac150006", "choices": [{"delta": {"content": null, "role": "assistant", "function_call": null, "tool_calls": null, "reasoning_content": "\\u6211"}, "finish_reason": null, "index": 0, "logprobs": null}], "created": 1763635033, "model": "model", "object": "chat.completion.chunk", "system_fingerprint": "", "usage": null}\n\n',
                b'data: {"id": "chatcmpl-86936f54c47f11f097350242ac150006", "choices": [{"delta": {"content": "\\u4f60\\u597d", "role": "assistant", "function_call": null, "tool_calls": null, "reasoning_content": null}, "finish_reason": null, "index": 0, "logprobs": null}], "created": 1763635034, "model": "model", "object": "chat.completion.chunk", "system_fingerprint": "", "usage": null}\n\n'
            ]
            
            for chunk in chunks:
                yield chunk
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
        assert len(lines) == 3
        
        # Check first chunk (reasoning)
        assert lines[0].startswith('data: ')
        first_data_str = lines[0][6:]  # Remove 'data: ' prefix
        first_data = json.loads(first_data_str)
        
        # Validate against OpenAI ChatCompletionChunk model
        chunk = ChatCompletionChunk(**first_data)
        assert chunk.id == "chatcmpl-86936f54c47f11f097350242ac150006"
        assert chunk.object == "chat.completion.chunk"
        assert chunk.choices[0].delta.reasoning_content == "我"
        assert chunk.choices[0].delta.content is None
        
        # Check second chunk (content)
        assert lines[1].startswith('data: ')
        second_data_str = lines[1][6:]  # Remove 'data: ' prefix
        second_data = json.loads(second_data_str)
        
        # Validate against OpenAI ChatCompletionChunk model
        chunk = ChatCompletionChunk(**second_data)
        assert chunk.id == "chatcmpl-86936f54c47f11f097350242ac150006"
        assert chunk.object == "chat.completion.chunk"
        assert chunk.choices[0].delta.content == "你好"
        assert chunk.choices[0].delta.reasoning_content is None
        
        # Check DONE message
        assert lines[2] == "data: [DONE]"


def test_ragflow_stream_error_handling():
    """Test that ragflow-stream properly handles errors"""
    
    # Mock an error response from RAGFlow
    class MockErrorResponse:
        def __init__(self):
            self.status_code = 500
            self.headers = {"content-type": "application/json"}
        
        async def aread(self):
            return b'{"error": {"message": "Internal server error"}}'
        
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Patch the httpx.AsyncClient.stream method
    with patch('httpx.AsyncClient.stream', return_value=MockErrorResponse()):
        response = client.post(
            "/api/v1/ragflow-stream",
            json={
                "session_id": "test_session",
                "message": "Hello"
            }
        )
        
        # Check that the response is successful (the endpoint handles the error)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
        
        # Check that error is properly formatted
        content = response.content.decode('utf-8')
        assert 'data: {"error":' in content
        assert 'data: [DONE]' in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])