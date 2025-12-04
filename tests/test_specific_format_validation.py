import pytest
import json
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, Choice, ChoiceDelta


def test_specific_ragflow_format_validation():
    """Test that validates the exact format provided in the requirements"""
    
    # Exact data from the requirement
    test_data = {
        "id": "chatcmpl-86936f54c47f11f097350242ac150006",
        "choices": [
            {
                "delta": {
                    "content": None,
                    "role": "assistant",
                    "function_call": None,
                    "tool_calls": None,
                    "reasoning_content": "\u6211"  # "我" in unicode
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
    
    # Create the model instance from the exact data
    chunk = ChatCompletionChunk(**test_data)
    
    # Verify the model matches exactly
    assert chunk.id == "chatcmpl-86936f54c47f11f097350242ac150006"
    assert chunk.created == 1763635033
    assert chunk.model == "model"
    assert chunk.object == "chat.completion.chunk"
    assert chunk.system_fingerprint == ""
    assert chunk.usage is None
    
    # Verify choices structure
    assert len(chunk.choices) == 1
    choice = chunk.choices[0]
    assert choice.index == 0
    assert choice.finish_reason is None
    assert choice.logprobs is None
    
    # Verify delta structure, particularly the reasoning_content
    delta = choice.delta
    assert delta.content is None
    assert delta.role == "assistant"
    assert delta.function_call is None
    assert delta.tool_calls is None
    assert delta.reasoning_content == "\u6211"  # "我"
    
    # Verify JSON serialization contains all required fields
    serialized = json.loads(chunk.model_dump_json())
    assert serialized["id"] == test_data["id"]
    assert serialized["created"] == test_data["created"]
    assert serialized["model"] == test_data["model"]
    assert serialized["object"] == test_data["object"]
    assert serialized["system_fingerprint"] == test_data["system_fingerprint"]
    assert serialized["usage"] == test_data["usage"]
    
    # Verify choices
    assert len(serialized["choices"]) == 1
    ser_choice = serialized["choices"][0]
    assert ser_choice["index"] == 0
    assert ser_choice["finish_reason"] is None
    assert ser_choice["logprobs"] is None
    
    # Verify delta
    ser_delta = ser_choice["delta"]
    assert ser_delta["content"] is None
    assert ser_delta["role"] == "assistant"
    assert ser_delta["function_call"] is None
    assert ser_delta["tool_calls"] is None
    assert ser_delta["reasoning_content"] == "\u6211"  # "我"


def test_parsing_from_json_string():
    """Test parsing the exact JSON string format"""
    
    # Exact JSON string from the requirement
    json_string = '''{
    "id": "chatcmpl-86936f54c47f11f097350242ac150006",
    "choices": [
        {
            "delta": {
                "content": null,
                "role": "assistant",
                "function_call": null,
                "tool_calls": null,
                "reasoning_content": "\u6211"
            },
            "finish_reason": null,
            "index": 0,
            "logprobs": null
        }
    ],
    "created": 1763635033,
    "model": "model",
    "object": "chat.completion.chunk",
    "system_fingerprint": "",
    "usage": null
}'''
    
    # Parse the JSON
    parsed_data = json.loads(json_string)
    
    # Create model from parsed data
    chunk = ChatCompletionChunk(**parsed_data)
    
    # Validate all fields
    assert chunk.id == "chatcmpl-86936f54c47f11f097350242ac150006"
    assert chunk.choices[0].delta.reasoning_content == "\u6211"
    assert chunk.choices[0].delta.content is None
    assert chunk.model == "model"
    assert chunk.object == "chat.completion.chunk"


def test_streaming_data_prefix_format():
    """Test the SSE format with data: prefix"""
    
    # Exact data from the requirement
    test_data = {
        "id": "chatcmpl-86936f54c47f11f097350242ac150006",
        "choices": [
            {
                "delta": {
                    "content": None,
                    "role": "assistant",
                    "function_call": None,
                    "tool_calls": None,
                    "reasoning_content": "\u6211"  # "我" in unicode
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
    
    # Create the model
    chunk = ChatCompletionChunk(**test_data)
    
    # Generate SSE format (data: prefix)
    sse_formatted = f"data: {chunk.model_dump_json()}\n\n"
    
    # Verify it starts with data: prefix
    assert sse_formatted.startswith("data: ")
    
    # Extract JSON from SSE format
    json_part = sse_formatted[6:-2]  # Remove 'data: ' prefix and '\n\n' suffix
    parsed_back = json.loads(json_part)
    
    # Should contain all the key fields
    assert parsed_back["id"] == test_data["id"]
    assert parsed_back["model"] == test_data["model"]
    assert parsed_back["object"] == test_data["object"]
    
    # Check choices
    assert len(parsed_back["choices"]) == 1
    assert parsed_back["choices"][0]["delta"]["reasoning_content"] == "\u6211"  # "我"
    assert parsed_back["choices"][0]["delta"]["content"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])