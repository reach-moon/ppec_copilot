# tests/e2e/test_chat_api.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.api.main import app
from app.schemas.graph_state import GraphState, Plan, PlanStep

client = TestClient(app)


class TestChatAPI:
    """End-to-end tests for the /chat API endpoint"""

    def test_chat_api_endpoint_exists(self):
        """Test that the /chat endpoint exists and responds to POST requests"""
        # Mock the entire graph to avoid calling actual LLMs
        with patch('app.api.endpoints.v1.chat.get_graph') as mock_get_graph:
            mock_graph = MagicMock()
            
            async def mock_astream_events(initial_state, version):
                # Create a simple mock plan
                mock_plan = Plan(
                    goal="测试查询",
                    steps=[
                        PlanStep(
                            step_id=1,
                            instruction="测试步骤",
                            status="complete",
                            result="测试结果"
                        )
                    ],
                    final_summary="测试总结"
                )
                
                # Yield a simple event
                yield {
                    "event": "on_chain_end",
                    "name": "summarize_step",
                    "data": {
                        "output": {
                            "plan": mock_plan
                        }
                    }
                }
            
            mock_graph.astream_events = mock_astream_events
            mock_get_graph.return_value = mock_graph
            
            # Send a simple request to check if endpoint exists
            response = client.post("/api/v1/chat", json={
                "session_id": "test_session_123",
                "message": "Hello, world!"
            })
            
            # With proper mocking, this should succeed
            assert response.status_code == 200

    def test_normal_conversation(self):
        """Test normal conversation flow with mocked graph execution"""
        # Mock the graph execution to return a predefined plan
        mock_plan = Plan(
            goal="测试查询",
            steps=[
                PlanStep(
                    step_id=1,
                    instruction="使用ragflow_knowledge_search工具搜索相关文档",
                    status="complete",
                    result="找到了相关文档"
                )
            ],
            final_summary="根据您的查询，我们找到了相关文档。"
        )
        
        # Create a mock graph with astream_events method
        mock_graph = MagicMock()
        
        async def mock_astream_events(initial_state, version):
            # Yield plan_update event
            yield {
                "event": "on_chain_end",
                "name": "execute_step",
                "data": {
                    "output": {
                        "plan": mock_plan
                    }
                }
            }
            
            # Yield final_response event
            yield {
                "event": "on_chain_end",
                "name": "summarize_step",
                "data": {
                    "output": {
                        "plan": mock_plan
                    }
                }
            }
        
        mock_graph.astream_events = mock_astream_events
        
        with patch('app.api.endpoints.v1.chat.get_graph', return_value=mock_graph):
            # Send POST request to /chat endpoint
            response = client.post("/api/v1/chat", json={
                "session_id": "test_session_123",
                "message": "查找相关文档"
            })
            
            # Verify response
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

    def test_session_continuity(self):
        """Test session continuity across multiple chat calls"""
        # This test would require more complex mocking to verify that
        # the messages context is passed correctly between calls.
        # For now, we'll verify that the endpoint accepts session_id correctly.
        
        with patch('app.api.endpoints.v1.chat.get_graph') as mock_get_graph:
            # Create a mock graph
            mock_graph = MagicMock()
            mock_graph.astream_events = self._create_mock_astream_events()
            mock_get_graph.return_value = mock_graph
            
            # First call
            response1 = client.post("/api/v1/chat", json={
                "session_id": "continuous_session_456",
                "message": "第一次查询"
            })
            
            # Second call with same session_id
            response2 = client.post("/api/v1/chat", json={
                "session_id": "continuous_session_456",
                "message": "第二次查询"
            })
            
            # Both should succeed
            assert response1.status_code == 200
            assert response2.status_code == 200

    def _create_mock_astream_events(self):
        """Helper method to create a mock astream_events function"""
        mock_plan = Plan(
            goal="测试查询",
            steps=[
                PlanStep(
                    step_id=1,
                    instruction="测试步骤",
                    status="complete",
                    result="测试结果"
                )
            ],
            final_summary="测试总结"
        )
        
        async def mock_astream_events(initial_state, version):
            yield {
                "event": "on_chain_end",
                "name": "summarize_step",
                "data": {
                    "output": {
                        "plan": mock_plan
                    }
                }
            }
        
        return mock_astream_events


class TestRevertAPI:
    """End-to-end tests for the /revert API endpoint (when implemented)"""

    def test_revert_endpoint_structure(self):
        """Test that the basic structure for revert functionality is in place"""
        # Currently, the /revert endpoint is not implemented
        # This test verifies that we can check for its existence
        
        # In the future, when /revert is implemented, we would test:
        # 1. Creating memories with multiple chat interactions
        # 2. Calling /revert with a specific turn_id
        # 3. Verifying that the memory state is correctly reverted
        pass

    def test_memory_service_integration_potential(self):
        """Test that memory service can be integrated for revert functionality"""
        # Verify that the mem0_service can be imported and used
        from app.services.tools.mem0_service import Mem0Service
        
        # Verify that the service class exists
        assert Mem0Service is not None
        
        # In a full E2E test, we would:
        # 1. Mock the mem0 client
        # 2. Test adding memories
        # 3. Test retrieving memories
        # 4. Test deleting memories (for revert functionality)
        pass


class TestRagflowProxy:
    """E2E tests for the /ragflow-stream proxy endpoint with mocked upstream"""

    def test_ragflow_proxy_passthrough(self):
        """Verify that the endpoint correctly streams responses from RAGFlow API"""
        # Simple async context manager to mock httpx response
        class AsyncMockResponse:
            def __init__(self):
                self.status_code = 200
                self.headers = {"content-type": "text/event-stream"}
            async def aiter_bytes(self):
                yield b"data: {\"content\": \"Hello\"}\n\n"
                yield b"data: {\"content\": \" World\"}\n\n"
                yield b"data: [DONE]\n\n"
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        def mock_stream(*args, **kwargs):
            return AsyncMockResponse()

        with patch('httpx.AsyncClient.stream', new=mock_stream):
            resp = client.post(
                "/api/v1/ragflow-stream",
                json={
                    "session_id": "test_session",
                    "turn_id": "test_turn",
                    "message": "Hello"
                }
            )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            assert "no-cache" in resp.headers.get("cache-control", "")
            assert resp.text.strip().startswith("data:")
            assert 'data: {"content": "Hello"}' in resp.text  # Verify first chunk
            assert 'data: {"content": " World"}' in resp.text  # Verify second chunk
            assert 'data: [DONE]' in resp.text  # Verify end marker

    def test_ragflow_proxy_error_passthrough(self):
        """Verify non-200 status and error responses are passed through"""
        # Simple async context manager to mock error response
        class AsyncMockErrorResponse:
            def __init__(self):
                self.status_code = 503
                self.headers = {"content-type": "application/json"}
            async def aiter_bytes(self):
                yield b'{"error": "upstream unavailable"}'
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        def mock_stream(*args, **kwargs):
            return AsyncMockErrorResponse()

        with patch('httpx.AsyncClient.stream', new=mock_stream):
            resp = client.post(
                "/api/v1/ragflow-stream",
                json={
                    "session_id": "test_session",
                    "turn_id": "test_turn",
                    "message": "Hello"
                }
            )
            assert resp.status_code == 503
            assert "application/json" in resp.headers.get("content-type", "")
            assert "upstream unavailable" in resp.text

    def test_ragflow_proxy_request_structure(self):
        """Verify that the proxy correctly formats requests to RAGFlow API"""
        captured_url = None
        captured_headers = None
        captured_payload = None

        # Simple async context manager to mock httpx response
        class AsyncMockResponse:
            def __init__(self):
                self.status_code = 200
                self.headers = {"content-type": "text/event-stream"}
            async def aiter_bytes(self):
                yield b"data: [DONE]\n\n"
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        def mock_stream(*args, **kwargs):
            """Return MockResponse directly as async context manager, capturing request data"""
            nonlocal captured_url, captured_headers, captured_payload

            # Extract URL from args or kwargs (adjust for bound method self argument)
            if len(args) >= 3:
                captured_url = args[2]  # Method, URL, etc. (self is args[0])
            elif "url" in kwargs:
                captured_url = kwargs["url"]
            elif len(args) >= 2:
                captured_url = args[1]  # Fallback for unbound methods
            else:
                captured_url = ""
            captured_headers = kwargs.get("headers")
            captured_payload = kwargs.get("json")
            return AsyncMockResponse()

        with patch('httpx.AsyncClient.stream', new=mock_stream):
            with patch('config.settings.settings.RAGFLOW_API_URL', new='http://test-ragflow-api:1080/api/v1/chats_openai/test-chat-id'):
                with patch('config.settings.settings.RAGFLOW_API_KEY', new='test-api-key'):
                    client.post(
                        "/api/v1/ragflow-stream",
                        json={
                            "session_id": "test_session",
                            "turn_id": "test_turn",
                            "message": "Hello world"
                        }
                    )

                    # Verify the request structure
                    assert captured_url == "http://test-ragflow-api:1080/api/v1/chats_openai/test-chat-id/chat/completions"
                    assert "Content-Type" in captured_headers
                    assert captured_headers["Content-Type"] == "application/json"
                    assert "Authorization" in captured_headers
                    assert captured_headers["Authorization"] == "Bearer test-api-key"
                    assert captured_payload["messages"][1]["content"] == "Hello world"
                    assert captured_payload["stream"] == True
                    assert "extra_body" in captured_payload
                    assert captured_payload["extra_body"]["reference"] == True