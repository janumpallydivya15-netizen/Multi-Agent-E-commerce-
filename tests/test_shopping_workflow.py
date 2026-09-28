import pytest
import os
from unittest.mock import patch

from app.workflows.shopping_workflow import (
    ShoppingState,
    requirement_node,
    product_search_node,
    review_analysis_node,
    price_specs_node,
    recommendation_node,
    build_workflow,
    run_shopping_workflow
)

from app.agents.requirement_agent import ShoppingRequirements

def should_skip():
    mock_mode_req = os.getenv("REQUIREMENT_AGENT_MOCK_MODE", "false").lower() == "true"
    api_key = os.getenv("GEMINI_API_KEY")
    return not mock_mode_req and not api_key

@pytest.fixture
def full_setup(monkeypatch):
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    monkeypatch.setenv("PRODUCT_SEARCH_AGENT_MOCK_MODE", "true")
    monkeypatch.setenv("REVIEW_AGENT_MOCK_MODE", "true")
    monkeypatch.setenv("PRICE_SPECS_AGENT_MOCK_MODE", "true")
    monkeypatch.setenv("RECOMMENDATION_AGENT_MOCK_MODE", "true")

def test_workflow_initialization(full_setup):
    workflow = build_workflow()
    assert workflow is not None

def test_requirement_node(full_setup):
    state = ShoppingState(user_request="I want a smartphone", current_step="start")
    new_state = requirement_node(state)
    assert new_state["requirements"] is not None
    assert new_state["requirements"].category == "Smartphones"
    assert new_state["current_step"] == "requirements"

def test_product_search_node(full_setup):
    reqs = ShoppingRequirements(category="Smartphones", budget=100000)
    state = ShoppingState(user_request="", requirements=reqs, current_step="requirements")
    new_state = product_search_node(state)
    assert "search_results" in new_state
    assert len(new_state["search_results"]) > 0
    assert new_state["current_step"] == "product_search"

def test_review_node(full_setup):
    reqs = ShoppingRequirements(category="Smartphones")
    state = ShoppingState(user_request="", requirements=reqs, current_step="requirements")
    state.update(product_search_node(state))
    new_state = review_analysis_node(state)
    assert "review_results" in new_state
    assert isinstance(new_state["review_results"], dict)
    assert new_state["current_step"] == "review_analysis"

def test_price_specs_node(full_setup):
    reqs = ShoppingRequirements(category="Smartphones")
    state = ShoppingState(user_request="", requirements=reqs, current_step="requirements")
    state.update(product_search_node(state))
    new_state = price_specs_node(state)
    assert "comparison_results" in new_state
    assert new_state["comparison_results"] is not None
    assert new_state["current_step"] == "price_specs"

def test_recommendation_node(full_setup):
    reqs = ShoppingRequirements(category="Smartphones")
    state = ShoppingState(user_request="", requirements=reqs, current_step="requirements")
    state.update(product_search_node(state))
    state.update(review_analysis_node(state))
    state.update(price_specs_node(state))
    new_state = recommendation_node(state)
    assert "recommendation_result" in new_state
    assert new_state["recommendation_result"] is not None
    assert new_state["current_step"] == "recommendation"

@pytest.mark.skipif(should_skip(), reason="Missing mock configuration")
def test_complete_workflow(full_setup):
    result = run_shopping_workflow("I want a smartphone under ₹100000")
    assert result["requirements"] is not None
    assert len(result["search_results"]) > 0
    assert result["comparison_results"] is not None
    assert result["recommendation_result"] is not None
    assert result["error"] is None
    assert result["current_step"] == "recommendation"

@pytest.mark.skipif(should_skip(), reason="Missing mock configuration")
def test_empty_search_results(full_setup):
    with patch('app.agents.product_search_agent.ProductSearchAgent.search', return_value=[]):
        result = run_shopping_workflow("I want an impossible item")
        assert result["requirements"] is not None
        assert result["error"] is None
        assert len(result["search_results"]) == 0
        assert result["recommendation_result"] is not None
        assert result["recommendation_result"].has_valid_matches == False

@pytest.mark.skipif(should_skip(), reason="Missing mock configuration")
def test_workflow_error_handling(full_setup):
    # Force an error in one of the nodes by mocking requirement_agent to raise exception
    with patch('app.agents.requirement_agent.RequirementAgent.extract_requirements', side_effect=Exception("Mocked Error")):
        result = run_shopping_workflow("I want a smartphone")
        assert result["error"] == "Requirement extraction failed: Mocked Error"
        assert result["current_step"] == "requirements"
        assert result.get("search_results") == []

def test_current_step_tracking(full_setup):
    state = ShoppingState(user_request="smartphone", current_step="start")
    state.update(requirement_node(state))
    assert state["current_step"] == "requirements"

@pytest.mark.skipif(should_skip(), reason="Missing mock configuration")
def test_smartphone_workflow(full_setup):
    result = run_shopping_workflow("I want a smartphone under ₹100,000 with good battery life")
    assert result["error"] is None
    assert result["requirements"].category == "Smartphones"
    assert result["recommendation_result"].has_valid_matches == True
    assert result["recommendation_result"].best_overall is not None

@pytest.mark.skipif(should_skip(), reason="Missing mock configuration")
def test_laptop_workflow(full_setup):
    result = run_shopping_workflow("I want a laptop under ₹70,000 for programming with 16GB RAM and good battery life")
    assert result["error"] is None
    assert result["requirements"].category == "Laptops"
    assert result["recommendation_result"] is not None

@pytest.mark.skipif(should_skip(), reason="Missing mock configuration")
def test_over_budget_workflow(full_setup):
    result = run_shopping_workflow("I want a smartphone under ₹40,000")
    assert result["error"] is None
    # With relaxed_budget=True in the product_search_node, the search results will contain the 44k phones
    assert len(result["search_results"]) > 0
    assert result["comparison_results"] is not None
    # However, recommendation node handles budget appropriately
    assert result["recommendation_result"].has_valid_matches == False
    assert len(result["recommendation_result"].alternatives) > 0
    assert "Over Budget" in result["recommendation_result"].alternatives[0].recommendation_type
