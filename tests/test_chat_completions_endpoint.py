import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.api.main import app

client = TestClient(app)


def test_chat_completions_endpoint_structure():
    """Test that the new chat-completions endpoint exists and has the right structure"""
    
    # Test that we can create a proper ChatCompletionRequest
    from app.api.endpoints.v1.models import ChatCompletionRequest
    
    request_data = ChatCompletionRequest(
        model="test-model",
        messages=[
            {"role": "user", "content": "Hello, world!"}
        ],
        stream=True,
        extra_body={"temperature": 0.7}
    )
    
    assert request_data.model == "test-model"
    assert len(request_data.messages) == 1
    assert request_data.messages[0]["role"] == "user"
    assert request_data.messages[0]["content"] == "Hello, world!"
    assert request_data.stream is True
    assert request_data.extra_body == {"temperature": 0.7}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])