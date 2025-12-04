# tests/unit/test_mem0_service.py
import pytest
from unittest.mock import patch, MagicMock
from app.services.tools.mem0_service import Mem0Service
from app.schemas.graph_state import Plan, PlanStep


class TestMem0Service:
    """Test cases for Mem0Service"""

    @pytest.fixture
    def mem0_service(self):
        """Fixture to create a Mem0Service instance with mocked client"""
        with patch('app.services.tools.mem0_service.get_mem0_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            service = Mem0Service()
            return service, mock_client

    def test_init(self):
        """Test Mem0Service initialization"""
        with patch('app.services.tools.mem0_service.get_mem0_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            service = Mem0Service()
            
            assert service._client == mock_client
            mock_get_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_completed_plan_success(self, mem0_service):
        """Test successful addition of completed plan to memory"""
        service, mock_client = mem0_service
        
        # Create a test plan with final summary
        plan = Plan(
            message_id="test_turn_1",
            goal="Test user goal",
            steps=[],
            final_summary="Test AI response"
        )
        
        # Execute the method
        await service.add_completed_plan("test_session_id", plan)
        
        # Verify the client's add method was called with correct parameters
        mock_client.add.assert_called_once_with(
            "User Goal: Test user goal\nAI Response: Test AI response",
            user_id="test_session_id",
            metadata={
                "plan": plan.model_dump_json(),
                "message_id": "test_turn_1"
            }
        )

    @pytest.mark.asyncio
    async def test_add_completed_plan_no_summary(self, mem0_service):
        """Test adding completed plan with no final summary"""
        service, mock_client = mem0_service
        
        # Create a test plan without final summary
        plan = Plan(
            message_id="test_turn_1",
            goal="Test user goal",
            steps=[]
            # No final_summary field
        )
        
        # Execute the method
        await service.add_completed_plan("test_session_id", plan)
        
        # Verify the client's add method was NOT called
        mock_client.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_completed_plan_exception_handling(self, mem0_service):
        """Test exception handling when adding completed plan"""
        service, mock_client = mem0_service
        
        # Make the client's add method raise an exception
        mock_client.add.side_effect = Exception("Test error")
        
        # Create a test plan
        plan = Plan(
            message_id="test_turn_1",
            goal="Test user goal",
            steps=[],
            final_summary="Test AI response"
        )
        
        # Execute the method (should not raise exception)
        await service.add_completed_plan("test_session_id", plan)
        
        # Verify the client's add method was called
        mock_client.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_memory_history_success(self, mem0_service):
        """Test successful retrieval of memory history"""
        service, mock_client = mem0_service
        
        # Mock the client's get_all response
        mock_client.get_all.return_value = [
            {
                "metadata": {
                    "plan": Plan(
                        message_id="test_turn_1",
                        goal="Test user goal 1",
                        steps=[],
                        final_summary="Test AI response 1"
                    ).model_dump_json()
                }
            },
            {
                "metadata": {
                    "plan": Plan(
                        message_id="test_turn_2",
                        goal="Test user goal 2",
                        steps=[],
                        final_summary="Test AI response 2"
                    ).model_dump_json()
                }
            }
        ]
        
        # Execute the method
        result = await service.get_memory_history("test_session_id")
        
        # Verify the result
        assert len(result) == 4  # 2 pairs of user/assistant messages
        assert result[0] == {"role": "user", "content": "Test user goal 1"}
        assert result[1] == {"role": "assistant", "content": "Test AI response 1"}
        assert result[2] == {"role": "user", "content": "Test user goal 2"}
        assert result[3] == {"role": "assistant", "content": "Test AI response 2"}
        
        # Verify the client's get_all method was called with correct parameters
        mock_client.get_all.assert_called_once_with(user_id="test_session_id", include_metadata=True)

    @pytest.mark.asyncio
    async def test_get_memory_history_parsing_error(self, mem0_service):
        """Test handling of invalid plan metadata"""
        service, mock_client = mem0_service
        
        # Mock the client's get_all response with invalid plan metadata
        mock_client.get_all.return_value = [
            {
                "metadata": {
                    "plan": "invalid json"  # This will cause a parsing error
                }
            }
        ]
        
        # Execute the method
        result = await service.get_memory_history("test_session_id")
        
        # Verify empty result due to parsing error
        assert result == []
        
        # Verify the client's get_all method was called
        mock_client.get_all.assert_called_once_with(user_id="test_session_id", include_metadata=True)

    @pytest.mark.asyncio
    async def test_get_memory_history_exception_handling(self, mem0_service):
        """Test exception handling when retrieving memory history"""
        service, mock_client = mem0_service
        
        # Make the client's get_all method raise an exception
        mock_client.get_all.side_effect = Exception("Test error")
        
        # Execute the method
        result = await service.get_memory_history("test_session_id")
        
        # Verify empty result due to exception
        assert result == []
        
        # Verify the client's get_all method was called
        mock_client.get_all.assert_called_once_with(user_id="test_session_id", include_metadata=True)

    @pytest.mark.asyncio
    async def test_revert_to_turn_success(self, mem0_service):
        """Test successful revert to specific turn"""
        service, mock_client = mem0_service
        
        # Mock the client's get_all response
        mock_client.get_all.return_value = [
            {"id": "mem_1", "metadata": {"message_id": "turn_1"}},
            {"id": "mem_2", "metadata": {"message_id": "turn_2"}},
            {"id": "mem_3", "metadata": {"message_id": "turn_3"}},
        ]
        
        # Execute the method
        await service.revert_to_turn("test_session_id", "turn_2")
        
        # Verify the client's get_all method was called
        mock_client.get_all.assert_called_once_with(user_id="test_session_id", include_metadata=True)
        
        # Verify the client's delete method was called for the correct memory
        mock_client.delete.assert_called_once_with(id="mem_3")

    @pytest.mark.asyncio
    async def test_revert_to_turn_not_found(self, mem0_service):
        """Test revert to turn that doesn't exist"""
        service, mock_client = mem0_service
        
        # Mock the client's get_all response
        mock_client.get_all.return_value = [
            {"id": "mem_1", "metadata": {"message_id": "turn_1"}},
            {"id": "mem_2", "metadata": {"message_id": "turn_2"}},
        ]
        
        # Execute the method and expect ValueError
        with pytest.raises(ValueError) as exc_info:
            await service.revert_to_turn("test_session_id", "turn_3")
        
        # Verify the exception message
        assert "Target turn ID not found in memory." in str(exc_info.value)
        
        # Verify no delete operations were performed
        mock_client.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_revert_to_turn_no_memories_to_delete(self, mem0_service):
        """Test revert to last turn (no memories to delete)"""
        service, mock_client = mem0_service
        
        # Mock the client's get_all response
        mock_client.get_all.return_value = [
            {"id": "mem_1", "metadata": {"message_id": "turn_1"}},
            {"id": "mem_2", "metadata": {"message_id": "turn_2"}},
        ]
        
        # Execute the method
        await service.revert_to_turn("test_session_id", "turn_2")
        
        # Verify no delete operations were performed
        mock_client.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_revert_to_turn_exception_handling(self, mem0_service):
        """Test exception handling when reverting to turn"""
        service, mock_client = mem0_service
        
        # Make the client's get_all method raise an exception
        mock_client.get_all.side_effect = Exception("Test error")
        
        # Execute the method and expect the exception to be raised
        with pytest.raises(Exception) as exc_info:
            await service.revert_to_turn("test_session_id", "turn_1")
        
        # Verify the exception message
        assert "Test error" in str(exc_info.value)