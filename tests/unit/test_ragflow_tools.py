# tests/unit/test_ragflow_tools.py
import pytest
from unittest.mock import patch, MagicMock
from openai import APIError
from requests import Timeout
from config.settings import settings
from app.services.tools.ragflow_tools import ragflow_knowledge_search
from app.core.exceptions import PpecCopilotException, ServiceUnavailableException


class TestRagflowTools:
    """Test cases for RAGFlow tools"""

    @pytest.mark.asyncio
    async def test_ragflow_knowledge_search_success(self):
        """Test successful RAGFlow knowledge search"""
        with patch('app.services.tools.ragflow_tools.OpenAI') as mock_openai:
            # Mock the OpenAI client and response
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "This is a test answer from RAGFlow"
            mock_client.chat.completions.create.return_value = mock_completion
            
            # Execute the tool
            result = await ragflow_knowledge_search.ainvoke({"query": "test query"})
            
            # Verify the result
            assert result == "This is a test answer from RAGFlow"
            
            # Verify OpenAI client was called with correct parameters
            mock_openai.assert_called_once_with(
                api_key=settings.RAGFLOW_API_KEY,
                base_url=settings.RAGFLOW_API_URL
            )
            
            mock_client.chat.completions.create.assert_called_once_with(
                model="model",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "test query"}
                ],
                stream=False,
                extra_body={"reference": True},
                timeout=60.0
            )

    @pytest.mark.asyncio
    async def test_ragflow_knowledge_search_empty_answer(self):
        """Test RAGFlow knowledge search with empty answer"""
        with patch('app.services.tools.ragflow_tools.OpenAI') as mock_openai:
            # Mock the OpenAI client and response with empty content
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = None
            mock_client.chat.completions.create.return_value = mock_completion
            
            # Execute the tool
            result = await ragflow_knowledge_search.ainvoke({"query": "test query"})
            
            # Verify the result
            assert result == "知识库中没有找到相关答案。"

    @pytest.mark.asyncio
    async def test_ragflow_knowledge_search_api_error(self):
        """Test RAGFlow knowledge search with API error"""
        with patch('app.services.tools.ragflow_tools.OpenAI') as mock_openai:
            # Mock the OpenAI client to raise APIError
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            
            # Execute the tool and expect ServiceUnavailableException
            with pytest.raises(PpecCopilotException) as exc_info:
                await ragflow_knowledge_search.ainvoke({"query": "test query"})
            
            # Verify the exception message
            assert "调用知识问答服务时发生未知错误。" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ragflow_knowledge_search_timeout(self):
        """Test RAGFlow knowledge search with timeout"""
        with patch('app.services.tools.ragflow_tools.OpenAI') as mock_openai:
            # Mock the OpenAI client to raise a timeout error
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Timeout("Request timed out")
            
            # Execute the tool and expect ServiceUnavailableException
            with pytest.raises(ServiceUnavailableException) as exc_info:
                await ragflow_knowledge_search.ainvoke({"query": "test query"})
            
            # Verify the exception message
            assert "知识问答服务响应超时，请稍后再试。" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ragflow_knowledge_search_unexpected_error(self):
        """Test RAGFlow knowledge search with unexpected error"""
        with patch('app.services.tools.ragflow_tools.OpenAI') as mock_openai:
            # Mock the OpenAI client to raise a generic exception
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("Unexpected Error")
            
            # Execute the tool and expect PpecCopilotException
            with pytest.raises(PpecCopilotException) as exc_info:
                await ragflow_knowledge_search.ainvoke({"query": "test query"})
            
            # Verify the exception message
            assert "调用知识问答服务时发生未知错误。" in str(exc_info.value)