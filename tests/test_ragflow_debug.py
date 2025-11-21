import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.api.main import app

client = TestClient(app)


def test_ragflow_stream_debug():
    """Debug test for ragflow-stream to see what's happening"""
    
    # Mock a more realistic RAGFlow response
    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.headers = {"content-type": "text/event-stream"}
        
        async def aiter_bytes(self):
            # Simulate actual RAGFlow response with multiple types of chunks
            chunks = [
                b'data: {"id": "chatcmpl-test123", "choices": [{"delta": {"content": null, "role": "assistant", "function_call": null, "tool_calls": null, "reasoning_content": "Think"}, "finish_reason": null, "index": 0, "logprobs": null}], "created": 1763635033, "model": "model", "object": "chat.completion.chunk", "system_fingerprint": "", "usage": null}\n\n',
                b'data: {"id": "chatcmpl-test123", "choices": [{"delta": {"content": null, "role": "assistant", "function_call": null, "tool_calls": null, "reasoning_content": "ing..."}, "finish_reason": null, "index": 0, "logprobs": null}], "created": 1763635034, "model": "model", "object": "chat.completion.chunk", "system_fingerprint": "", "usage": null}\n\n',
                b'data: {"id": "chatcmpl-test123", "choices": [{"delta": {"content": "Hello", "role": "assistant", "function_call": null, "tool_calls": null, "reasoning_content": null}, "finish_reason": null, "index": 0, "logprobs": null}], "created": 1763635035, "model": "model", "object": "chat.completion.chunk", "system_fingerprint": "", "usage": null}\n\n',
                b'data: {"id": "chatcmpl-test123", "choices": [{"delta": {"content": " World", "role": "assistant", "function_call": null, "tool_calls": null, "reasoning_content": null}, "finish_reason": null, "index": 0, "logprobs": null}], "created": 1763635036, "model": "model", "object": "chat.completion.chunk", "system_fingerprint": "", "usage": null}\n\n',
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
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        
        # Check that the response is successful
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
        
        # Check the response content format
        content = response.content.decode('utf-8')
        print(f"Response content: {content}")
        
        lines = content.strip().split('\n\n')
        print(f"Number of lines: {len(lines)}")
        for i, line in enumerate(lines):
            print(f"Line {i}: {line}")


if __name__ == "__main__":
    test_ragflow_stream_debug()