# tests/unit/test_schemas.py
import pytest
from pydantic import ValidationError
from app.schemas.graph_state import PlanStep, Plan, GraphState
from typing import List
import uuid


class TestPlanStep:
    """Test cases for PlanStep schema"""

    def test_plan_step_creation_success(self):
        """Test successful creation of PlanStep with valid data"""
        step = PlanStep(
            step_id=1,
            instruction="Test instruction"
        )
        
        assert step.step_id == 1
        assert step.instruction == "Test instruction"
        assert step.status == "pending"
        assert step.result is None

    def test_plan_step_with_all_fields(self):
        """Test creation of PlanStep with all fields provided"""
        step = PlanStep(
            step_id=1,
            instruction="Test instruction",
            status="complete",
            result="Test result"
        )
        
        assert step.step_id == 1
        assert step.instruction == "Test instruction"
        assert step.status == "complete"
        assert step.result == "Test result"

    def test_plan_step_missing_required_fields(self):
        """Test that PlanStep raises ValidationError when required fields are missing"""
        with pytest.raises(ValidationError):
            PlanStep(step_id=1)  # Missing instruction
            
        with pytest.raises(ValidationError):
            PlanStep(instruction="Test instruction")  # Missing step_id

    def test_plan_step_invalid_status(self):
        """Test that PlanStep accepts any status value (no strict validation)"""
        step = PlanStep(
            step_id=1,
            instruction="Test instruction",
            status="invalid_status"
        )
        
        assert step.status == "invalid_status"

    def test_plan_step_serialization(self):
        """Test PlanStep serialization to and from dict"""
        step = PlanStep(
            step_id=1,
            instruction="Test instruction",
            status="complete",
            result="Test result"
        )
        
        # Serialize to dict
        step_dict = step.model_dump()
        expected_dict = {
            "step_id": 1,
            "instruction": "Test instruction",
            "status": "complete",
            "result": "Test result"
        }
        assert step_dict == expected_dict
        
        # Deserialize from dict
        step_from_dict = PlanStep(**step_dict)
        assert step_from_dict.step_id == step.step_id
        assert step_from_dict.instruction == step.instruction
        assert step_from_dict.status == step.status
        assert step_from_dict.result == step.result


class TestPlan:
    """Test cases for Plan schema"""

    def test_plan_creation_success(self):
        """Test successful creation of Plan with minimal data"""
        plan = Plan(
            goal="Test goal",
            steps=[]
        )
        
        # Verify turn_id is auto-generated
        assert isinstance(plan.turn_id, str)
        assert uuid.UUID(plan.turn_id)  # Should be a valid UUID
        
        assert plan.goal == "Test goal"
        assert plan.steps == []
        assert plan.final_summary is None

    def test_plan_creation_with_all_fields(self):
        """Test creation of Plan with all fields provided"""
        steps = [
            PlanStep(step_id=1, instruction="Step 1"),
            PlanStep(step_id=2, instruction="Step 2", status="complete")
        ]
        
        plan = Plan(
            turn_id="test-turn-id",
            goal="Test goal",
            steps=steps,
            final_summary="Test summary"
        )
        
        assert plan.turn_id == "test-turn-id"
        assert plan.goal == "Test goal"
        assert len(plan.steps) == 2
        assert plan.final_summary == "Test summary"

    def test_plan_auto_turn_id(self):
        """Test that Plan auto-generates unique turn_id"""
        plan1 = Plan(goal="Test goal 1", steps=[])
        plan2 = Plan(goal="Test goal 2", steps=[])
        
        assert plan1.turn_id != plan2.turn_id
        assert uuid.UUID(plan1.turn_id)
        assert uuid.UUID(plan2.turn_id)

    def test_plan_missing_required_fields(self):
        """Test that Plan raises ValidationError when required fields are missing"""
        with pytest.raises(ValidationError):
            Plan(steps=[])  # Missing goal
            
        with pytest.raises(ValidationError):
            Plan(goal="Test goal")  # Missing steps

    def test_plan_serialization(self):
        """Test Plan serialization to and from dict"""
        steps = [
            PlanStep(step_id=1, instruction="Step 1"),
            PlanStep(step_id=2, instruction="Step 2", status="complete", result="Done")
        ]
        
        plan = Plan(
            turn_id="test-turn-id",
            goal="Test goal",
            steps=steps,
            final_summary="Test summary"
        )
        
        # Serialize to dict
        plan_dict = plan.model_dump()
        expected_dict = {
            "turn_id": "test-turn-id",
            "goal": "Test goal",
            "steps": [
                {
                    "step_id": 1,
                    "instruction": "Step 1",
                    "status": "pending",
                    "result": None
                },
                {
                    "step_id": 2,
                    "instruction": "Step 2",
                    "status": "complete",
                    "result": "Done"
                }
            ],
            "final_summary": "Test summary"
        }
        assert plan_dict == expected_dict
        
        # Deserialize from dict
        plan_from_dict = Plan(**plan_dict)
        assert plan_from_dict.turn_id == plan.turn_id
        assert plan_from_dict.goal == plan.goal
        assert plan_from_dict.final_summary == plan.final_summary
        assert len(plan_from_dict.steps) == len(plan.steps)
        
        # Verify steps
        for i, step in enumerate(plan_from_dict.steps):
            assert step.step_id == plan.steps[i].step_id
            assert step.instruction == plan.steps[i].instruction
            assert step.status == plan.steps[i].status
            assert step.result == plan.steps[i].result


class TestGraphState:
    """Test cases for GraphState schema"""

    def test_graph_state_creation(self):
        """Test creation of GraphState"""
        state: GraphState = {
            "session_id": "test-session",
            "messages": []
        }
        
        assert state["session_id"] == "test-session"
        assert state["messages"] == []

    def test_graph_state_with_plan(self):
        """Test GraphState with plan"""
        plan = Plan(goal="Test goal", steps=[])
        
        state: GraphState = {
            "session_id": "test-session",
            "plan": plan,
            "messages": [{"role": "user", "content": "Test message"}]
        }
        
        assert state["session_id"] == "test-session"
        assert state["plan"] == plan
        assert state["messages"] == [{"role": "user", "content": "Test message"}]

    def test_graph_state_optional_fields(self):
        """Test GraphState with optional fields"""
        state: GraphState = {
            "session_id": "test-session",
            "plan": None,
            "messages": []
        }
        
        assert state["session_id"] == "test-session"
        assert state["plan"] is None
        assert state["messages"] == []