import pytest
import json
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, Choice, ChoiceDelta


def test_chat_completion_chunk_model():
    """Test that we can create a ChatCompletionChunk model with our expected structure"""
    
    # Test data matching the example
    test_data = {
        "id": "chatcmpl-86936f54c47f11f097350242ac150006",
        "choices": [
            {
                "delta": {
                    "content": None,
                    "role": "assistant",
                    "function_call": None,
                    "tool_calls": None,
                    "reasoning_content": "我"
                },
                "finish_reason": None,
                "index": 0,
                "logprobs": None
            }
        ],
        "created": 1763635033,
        "model": "model",
        "object": "chat.completion.chunk",
        "system_fingerprint": "",
        "usage": None
    }
    
    # Create the model instance
    chunk = ChatCompletionChunk(
        id=test_data["id"],
        choices=[
            Choice(
                delta=ChoiceDelta(
                    content=test_data["choices"][0]["delta"]["content"],
                    role=test_data["choices"][0]["delta"]["role"],
                    function_call=test_data["choices"][0]["delta"]["function_call"],
                    tool_calls=test_data["choices"][0]["delta"]["tool_calls"],
                    reasoning_content=test_data["choices"][0]["delta"]["reasoning_content"]
                ),
                finish_reason=test_data["choices"][0]["finish_reason"],
                index=test_data["choices"][0]["index"],
                logprobs=test_data["choices"][0]["logprobs"]
            )
        ],
        created=test_data["created"],
        model=test_data["model"],
        object=test_data["object"],
        system_fingerprint=test_data["system_fingerprint"],
        usage=test_data["usage"]
    )
    
    # Verify the model
    assert chunk.id == test_data["id"]
    assert chunk.created == test_data["created"]
    assert chunk.model == test_data["model"]
    assert chunk.object == test_data["object"]
    assert chunk.system_fingerprint == test_data["system_fingerprint"]
    assert chunk.usage == test_data["usage"]
    
    # Verify choices
    assert len(chunk.choices) == 1
    choice = chunk.choices[0]
    assert choice.index == 0
    assert choice.finish_reason is None
    assert choice.logprobs is None
    
    # Verify delta
    delta = choice.delta
    assert delta.content is None
    assert delta.role == "assistant"
    assert delta.function_call is None
    assert delta.tool_calls is None
    assert delta.reasoning_content == "我"


def test_serialization():
    """Test that the model serializes correctly to JSON"""
    
    # Test data matching the example
    test_data = {
        "id": "chatcmpl-86936f54c47f11f097350242ac150006",
        "choices": [
            {
                "delta": {
                    "content": None,
                    "role": "assistant",
                    "function_call": None,
                    "tool_calls": None,
                    "reasoning_content": "我"
                },
                "finish_reason": None,
                "index": 0,
                "logprobs": None
            }
        ],
        "created": 1763635033,
        "model": "model",
        "object": "chat.completion.chunk",
        "system_fingerprint": "",
        "usage": None
    }
    
    # Create the model instance
    chunk = ChatCompletionChunk(
        id=test_data["id"],
        choices=[
            Choice(
                delta=ChoiceDelta(
                    content=test_data["choices"][0]["delta"]["content"],
                    role=test_data["choices"][0]["delta"]["role"],
                    function_call=test_data["choices"][0]["delta"]["function_call"],
                    tool_calls=test_data["choices"][0]["delta"]["tool_calls"],
                    reasoning_content=test_data["choices"][0]["delta"]["reasoning_content"]
                ),
                finish_reason=test_data["choices"][0]["finish_reason"],
                index=test_data["choices"][0]["index"],
                logprobs=test_data["choices"][0]["logprobs"]
            )
        ],
        created=test_data["created"],
        model=test_data["model"],
        object=test_data["object"],
        system_fingerprint=test_data["system_fingerprint"],
        usage=test_data["usage"]
    )
    
    # Serialize to JSON
    json_str = chunk.model_dump_json()
    parsed_json = json.loads(json_str)
    
    # Verify serialization
    assert parsed_json["id"] == test_data["id"]
    assert parsed_json["created"] == test_data["created"]
    assert parsed_json["model"] == test_data["model"]
    assert parsed_json["object"] == test_data["object"]
    assert parsed_json["system_fingerprint"] == test_data["system_fingerprint"]
    assert parsed_json["usage"] == test_data["usage"]
    
    # Verify choices serialization
    assert len(parsed_json["choices"]) == 1
    choice = parsed_json["choices"][0]
    assert choice["index"] == 0
    assert choice["finish_reason"] is None
    assert choice["logprobs"] is None
    
    # Verify delta serialization
    delta = choice["delta"]
    assert delta["content"] is None
    assert delta["role"] == "assistant"
    assert delta["function_call"] is None
    assert delta["tool_calls"] is None
    assert delta["reasoning_content"] == "我"


def test_streaming_format_compatibility():
    """Test that our format matches the expected streaming format"""
    
    # Test the standard streaming format with content
    content_chunk = ChatCompletionChunk(
        id="chatcmpl-test123",
        choices=[
            Choice(
                delta=ChoiceDelta(
                    content="Hello",
                    role="assistant",
                    function_call=None,
                    tool_calls=None,
                    reasoning_content=None
                ),
                finish_reason=None,
                index=0,
                logprobs=None
            )
        ],
        created=1763635033,
        model="test-model",
        object="chat.completion.chunk",
        system_fingerprint="",
        usage=None
    )
    
    content_json = json.loads(content_chunk.model_dump_json())
    assert content_json["choices"][0]["delta"]["content"] == "Hello"
    assert content_json["choices"][0]["delta"]["reasoning_content"] is None
    
    # Test the reasoning format
    reasoning_chunk = ChatCompletionChunk(
        id="chatcmpl-test123",
        choices=[
            Choice(
                delta=ChoiceDelta(
                    content=None,
                    role="assistant",
                    function_call=None,
                    tool_calls=None,
                    reasoning_content="Thinking..."
                ),
                finish_reason=None,
                index=0,
                logprobs=None
            )
        ],
        created=1763635033,
        model="test-model",
        object="chat.completion.chunk",
        system_fingerprint="",
        usage=None
    )
    
    reasoning_json = json.loads(reasoning_chunk.model_dump_json())
    assert reasoning_json["choices"][0]["delta"]["content"] is None
    assert reasoning_json["choices"][0]["delta"]["reasoning_content"] == "Thinking..."


if __name__ == "__main__":
    pytest.main([__file__])