import pytest
import os
from app.agents.requirement_agent import ShoppingRequirements
from app.agents.product_search_agent import ProductSearchAgent, SearchResult
from app.core.llm import llm_service
from app.database.models import Product

def is_mock_enabled():
    return os.getenv("REQUIREMENT_AGENT_MOCK_MODE", "false").lower() == "true"

def should_skip():
    return not (llm_service.is_configured() or is_mock_enabled())

@pytest.fixture
def agent():
    return ProductSearchAgent()

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_search_laptop_under_budget(agent):
    reqs = ShoppingRequirements(
        category="Laptops",
        budget=70000,
        important_specifications=["16GB RAM"]
    )
    results = agent.search(reqs)
    
    assert len(results) > 0
    assert isinstance(results[0], SearchResult)
    # The first result should have a high score
    assert results[0].match_score > 0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_search_no_candidates(agent):
    reqs = ShoppingRequirements(
        category="Smartwatches",
        budget=10 # Impossibly low budget to ensure 0 candidates
    )
    results = agent.search(reqs)
    
    assert len(results) == 0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_search_mock_mode_specific(agent, monkeypatch):
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(
        category="Smartphones",
        budget=50000,
        preferred_brands=["Samsung"]
    )
    results = agent.search(reqs)
    
    assert len(results) > 0
    # In mock mode, we expect top 3 at most
    assert len(results) <= 3

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_smartphone_category_search(agent, monkeypatch):
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(category="Smartphones")
    results = agent.search(reqs)
    assert len(results) > 0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_budget_filter(agent, monkeypatch):
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(budget=100000)
    results = agent.search(reqs)
    assert len(results) > 0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_smartphone_under_40000(agent, monkeypatch):
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(category="Smartphones", budget=40000)
    results = agent.search(reqs)
    # 0 because cheapest smartphone is ~$538 * 83 = ~44654 INR
    assert len(results) == 0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_laptop_under_70000(agent, monkeypatch):
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(category="Laptops", budget=70000)
    results = agent.search(reqs)
    assert len(results) > 0
    
@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_no_stale_search_criteria(monkeypatch):
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    from app.agents.requirement_agent import RequirementAgent
    req_agent = RequirementAgent()
    
    req1 = req_agent.extract_requirements("I want smartphones under ₹40,000")
    assert req1.category == "Smartphones"
    assert req1.budget == 40000.0
    
    req2 = req_agent.extract_requirements("I want laptops under ₹70,000")
    assert req2.category == "Laptops"
    assert req2.budget == 70000.0
    
    req3 = req_agent.extract_requirements("I want headphones under ₹5,000")
    assert req3.category == "Headphones"
    assert req3.budget == 5000.0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_category_normalization(monkeypatch):
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    from app.agents.requirement_agent import RequirementAgent
    req_agent = RequirementAgent()
    
    assert req_agent.extract_requirements("mobile").category == "Smartphones"
    assert req_agent.extract_requirements("notebook").category == "Laptops"
    assert req_agent.extract_requirements("earphones").category == "Headphones"
    assert req_agent.extract_requirements("smart watch").category == "Smartwatches"
    
@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_budget_normalization(monkeypatch):
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    from app.agents.requirement_agent import RequirementAgent
    req_agent = RequirementAgent()
    
    assert req_agent.extract_requirements("under ₹40,000").budget == 40000.0
    assert req_agent.extract_requirements("40000").budget == 40000.0
    assert req_agent.extract_requirements("40k").budget == 40000.0
    assert req_agent.extract_requirements("40 K").budget == 40000.0
    assert req_agent.extract_requirements("below 40k").budget == 40000.0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_empty_search(agent, monkeypatch):
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements()
    results = agent.search(reqs)
    # Should search all and return top 3
    assert len(results) > 0
    assert len(results) <= 3

# ==========================================
# PHASE 9 INTEGRATION FIX TESTS
# ==========================================

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_search_accepts_relaxed_budget(agent, monkeypatch):
    """Verify that ProductSearchAgent.search() accepts relaxed_budget."""
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(category="Smartphones", budget=40000)
    
    # This should not raise an unexpected keyword argument error
    results = agent.search(reqs, relaxed_budget=False)
    assert len(results) == 0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_search_relaxed_budget_preserves_strict_behavior(agent, monkeypatch):
    """Verify that relaxed_budget=False strictly enforces the budget limit."""
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(category="Smartphones", budget=40000)
    
    # Strict behavior should yield 0 since cheapest smartphone is ~₹44,654
    results = agent.search(reqs, relaxed_budget=False)
    assert len(results) == 0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_search_relaxed_budget_returns_candidates(agent, monkeypatch):
    """Verify that relaxed_budget=True returns candidates exceeding the budget limit."""
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(category="Smartphones", budget=40000)
    
    # Relaxed behavior should return smartphones regardless of price
    results = agent.search(reqs, relaxed_budget=True)
    assert len(results) > 0
