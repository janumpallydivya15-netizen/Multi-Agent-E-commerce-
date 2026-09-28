import pytest
from app.agents.requirement_agent import RequirementAgent
from app.core.llm import llm_service

@pytest.fixture
def agent():
    return RequirementAgent()

def test_empty_input(agent):
    # Empty input should be handled gracefully without calling LLM
    reqs = agent.extract_requirements("")
    assert reqs.category is None
    assert reqs.budget is None

import os

def should_skip():
    mock_mode = os.getenv("REQUIREMENT_AGENT_MOCK_MODE", "false").lower() == "true"
    return not (llm_service.is_configured() or mock_mode)

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_laptop_programming(agent):
    request = "I need a laptop under ₹70,000 for programming with 16GB RAM."
    reqs = agent.extract_requirements(request)
    
    assert reqs.category == "Laptops"
    assert reqs.budget == 70000
    assert any("program" in p.lower() or "cod" in p.lower() for p in reqs.purpose)
    assert any("16" in s.lower() and "ram" in s.lower() for s in reqs.important_specifications)

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_wireless_headphones(agent):
    request = "Show me wireless headphones below 5k with noise cancellation."
    reqs = agent.extract_requirements(request)
    
    assert reqs.category == "Headphones"
    assert reqs.budget == 5000
    assert any("noise" in f.lower() for f in reqs.required_features)

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_samsung_smartphone(agent):
    request = "I want a Samsung smartphone with a good camera."
    reqs = agent.extract_requirements(request)
    
    assert reqs.category == "Smartphones"
    assert any("samsung" in b.lower() for b in reqs.preferred_brands)
    assert any("camera" in f.lower() for f in reqs.required_features)

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_smartwatch_fitness(agent):
    request = "Need a smartwatch for fitness with GPS."
    reqs = agent.extract_requirements(request)
    
    assert reqs.category == "Smartwatches"
    assert any("fitness" in p.lower() for p in reqs.purpose)
    assert any("gps" in f.lower() for f in reqs.required_features)

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_ambiguous_good(agent):
    request = "I want something good."
    reqs = agent.extract_requirements(request)
    
    # Should not invent category or budget
    assert reqs.category is None
    assert reqs.budget is None


def test_llm_not_configured_graceful_failure(monkeypatch):
    # Disable mock mode
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "false")
    
    # If the LLM is forcibly unconfigured, it should raise RuntimeError
    agent = RequirementAgent()
    original_client = llm_service.client
    llm_service.client = None
    
    with pytest.raises(RuntimeError, match="LLM is not configured"):
        agent.extract_requirements("I need a laptop")
        
    # Restore for other tests
    llm_service.client = original_client
