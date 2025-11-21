import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.api.main import app
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

client = TestClient(app)


def test_ragflow_stream_proper_sse_formatting():
    """Test that ragflow-stream properly formats SSE data with space after 'data:'"""
    
    # Mock the httpx response to simulate RAGFlow API with improperly formatted data
    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {"content-type": "text/event-stream"}
        
        async def aiter_bytes(self):
            # Simulate RAGFlow response chunks with missing space after 'data:'
            chunks = [
                b'data:{"id": "chatcmpl-test123", "choices": [{"delta": {"content": null, "role": "assistant", "function_call": null, "tool_calls": null, "reasoning_content": ","}, "finish_reason": null, "index": 0, "logprobs": null}], "created": 1763648516, "model": "model", "object": "chat.completion.chunk", "system_fingerprint": "", "usage": null}\n\n',
                b'data:{"id": "chatcmpl-test123", "choices": [{"delta": {"content": "Hello", "role": "assistant", "function_call": null, "tool_calls": null, "reasoning_content": null}, "finish_reason": null, "index": 0, "logprobs": null}], "created": 1763648517, "model": "model", "object": "chat.completion.chunk", "system_fingerprint": "", "usage": null}\n\n'
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
        
        # Check that each line starts with 'data: ' (with space)
        for i in range(len(lines) - 1):  # All except the last [DONE] line
            assert lines[i].startswith('data: '), f"Line {i} doesn't start with 'data: '"
            # Check that there's a space after 'data:'
            assert lines[i][5] == ' ', f"Line {i} missing space after 'data:'"
        
        # Check first chunk (reasoning)
        first_data_str = lines[0][6:]  # Remove 'data: ' prefix
        first_data = json.loads(first_data_str)
        
        # Validate against OpenAI ChatCompletionChunk model
        chunk = ChatCompletionChunk(**first_data)
        assert chunk.choices[0].delta.reasoning_content == ","
        assert chunk.choices[0].delta.content is None
        
        # Check second chunk (content)
        second_data_str = lines[1][6:]  # Remove 'data: ' prefix
        second_data = json.loads(second_data_str)
        
        # Validate against OpenAI ChatCompletionChunk model
        chunk = ChatCompletionChunk(**second_data)
        assert chunk.choices[0].delta.content == "Hello"
        assert chunk.choices[0].delta.reasoning_content is None
        
        # Check DONE message
        assert lines[2] == "data: [DONE]"


def test_ragflow_stream_already_properly_formatted():
    """Test that ragflow-stream handles already properly formatted data correctly"""
    
    # Mock the httpx response to simulate RAGFlow API with properly formatted data
    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {"content-type": "text/event-stream"}
        
        async def aiter_bytes(self):
            # Simulate RAGFlow response chunks with proper spacing
            chunks = [
                b'data: {"id": "chatcmpl-test123", "choices": [{"delta": {"content": null, "role": "assistant", "function_call": null, "tool_calls": null, "reasoning_content": "Thinking"}, "finish_reason": null, "index": 0, "logprobs": null}], "created": 1763648516, "model": "model", "object": "chat.completion.chunk", "system_fingerprint": "", "usage": null}\n\n',
                b'data: {"id": "chatcmpl-test123", "choices": [{"delta": {"content": "Hello World", "role": "assistant", "function_call": null, "tool_calls": null, "reasoning_content": null}, "finish_reason": null, "index": 0, "logprobs": null}], "created": 1763648517, "model": "model", "object": "chat.completion.chunk", "system_fingerprint": "", "usage": null}\n\n'
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
        
        # Check that each line starts with 'data: ' (with space)
        for i in range(len(lines) - 1):  # All except the last [DONE] line
            assert lines[i].startswith('data: '), f"Line {i} doesn't start with 'data: '"
            # Check that there's a space after 'data:'
            assert lines[i][5] == ' ', f"Line {i} missing space after 'data:'"
        
        # Check first chunk (reasoning)
        first_data_str = lines[0][6:]  # Remove 'data: ' prefix
        first_data = json.loads(first_data_str)
        
        # Validate against OpenAI ChatCompletionChunk model
        chunk = ChatCompletionChunk(**first_data)
        assert chunk.choices[0].delta.reasoning_content == "Thinking"
        assert chunk.choices[0].delta.content is None
        
        # Check second chunk (content)
        second_data_str = lines[1][6:]  # Remove 'data: ' prefix
        second_data = json.loads(second_data_str)
        
        # Validate against OpenAI ChatCompletionChunk model
        chunk = ChatCompletionChunk(**second_data)
        assert chunk.choices[0].delta.content == "Hello World"
        assert chunk.choices[0].delta.reasoning_content is None
        
        # Check DONE message
        assert lines[2] == "data: [DONE]"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])