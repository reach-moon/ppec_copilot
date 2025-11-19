# tests/component/test_hierarchical_planner.py
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import AIMessage


class TestPlannerModule:
    """Test cases for Planner module components"""

    def test_planner_runnable_exists(self):
        """Test that planner_runnable is properly defined"""
        # Import the actual components
        from app.core.agents.hierarchical_planner import planner_runnable
        
        # Verify that the planner runnable exists and has the expected structure
        assert planner_runnable is not None
        # Should be a chain (combination of prompt and LLM)
        assert hasattr(planner_runnable, 'first')  # Prompt part
        assert hasattr(planner_runnable, 'last')   # LLM part

    def test_planner_has_tools_info(self):
        """Test that planner has information about available tools"""
        from app.core.agents.hierarchical_planner import planner_prompt
        
        # Check that the prompt contains information about tools
        messages = planner_prompt.messages
        system_message = messages[0]  # Should be the system message
        
        # Verify that the system message mentions the tools
        assert "ragflow_knowledge_search" in system_message.prompt.template
        # In future, should also mention code tools when implemented


class TestExecutorModule:
    """Test cases for Executor module components"""

    def test_executor_llm_exists(self):
        """Test that executor_llm is properly defined"""
        from app.core.agents.hierarchical_planner import executor_llm, tools
        
        # Verify that the executor LLM exists
        assert executor_llm is not None
        # Should be an LLM that can bind tools
        assert hasattr(executor_llm, 'bind_tools')
        
        # Verify that tools are defined
        assert isinstance(tools, list)
        assert len(tools) >= 1  # Should have at least ragflow_knowledge_search

    def test_executor_has_ragflow_tool(self):
        """Test that executor has access to ragflow knowledge search tool"""
        from app.core.agents.hierarchical_planner import tools
        from app.services.tools.ragflow_tools import ragflow_knowledge_search
        
        # Verify that ragflow_knowledge_search is in the tools list
        assert ragflow_knowledge_search in tools
        assert ragflow_knowledge_search.name == "ragflow_knowledge_search"


class TestSummarizerModule:
    """Test cases for Summarizer module components"""

    def test_summarizer_chain_exists(self):
        """Test that summarizer_chain is properly defined"""
        from app.core.agents.hierarchical_planner import summarizer_chain
        
        # Verify that the summarizer chain exists
        assert summarizer_chain is not None
        # Should be a chain (combination of prompt and LLM)
        assert hasattr(summarizer_chain, 'first')  # Prompt part
        assert hasattr(summarizer_chain, 'last')   # LLM part

    def test_summarizer_prompt_structure(self):
        """Test that summarizer prompt has the expected structure"""
        from app.core.agents.hierarchical_planner import summarizer_prompt
        
        # Check that the prompt has the expected messages
        messages = summarizer_prompt.messages
        assert len(messages) >= 2  # Should have system and user messages
        
        system_message = messages[0]
        user_message = messages[-1]  # Last message should be user message
        
        # Verify content of system message
        assert "总结" in system_message.prompt.template or "summary" in system_message.prompt.template.lower()
        
        # Verify user message has placeholders
        assert "{goal}" in user_message.prompt.template
        assert "{plan_steps_summary}" in user_message.prompt.template