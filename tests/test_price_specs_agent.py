import pytest
import os
from app.agents.price_specs_agent import PriceSpecsAgent
from app.agents.requirement_agent import ShoppingRequirements
from app.database.database import get_product_by_id

def should_skip():
    mock_mode = os.getenv("PRICE_SPECS_AGENT_MOCK_MODE", "false").lower() == "true"
    api_key = os.getenv("GEMINI_API_KEY")
    return not mock_mode and not api_key

@pytest.fixture
def agent():
    return PriceSpecsAgent()

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_single_product_comparison(agent, monkeypatch):
    monkeypatch.setenv("PRICE_SPECS_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(category="Smartphones", budget=100000.0)
    p = get_product_by_id("P1009") # PhoneMax Air 7
    res = agent.compare(reqs, [p])
    assert len(res.products) == 1
    assert res.products[0].within_budget == True

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_multiple_product_comparison(agent, monkeypatch):
    monkeypatch.setenv("PRICE_SPECS_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(category="Smartphones", budget=100000.0)
    p1 = get_product_by_id("P1009")
    p2 = get_product_by_id("P1010")
    res = agent.compare(reqs, [p1, p2])
    assert len(res.products) == 2

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_budget_status(agent, monkeypatch):
    monkeypatch.setenv("PRICE_SPECS_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(budget=100000.0)
    p = get_product_by_id("P1009")
    res = agent.compare(reqs, [p])
    assert res.products[0].within_budget == True

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_over_budget_product(agent, monkeypatch):
    monkeypatch.setenv("PRICE_SPECS_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(budget=40000.0)
    p = get_product_by_id("P1009") # ~44,000 INR
    res = agent.compare(reqs, [p])
    assert res.products[0].within_budget == False
    assert res.products[0].score <= 69.0 # Should be penalized

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_required_requirement_matching(agent, monkeypatch):
    monkeypatch.setenv("PRICE_SPECS_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(category="Smartphones", important_specifications=["12GB RAM"])
    p = get_product_by_id("P1009") # Has 12GB RAM
    res = agent.compare(reqs, [p])
    assert res.products[0].required_matches == res.products[0].required_total

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_preferred_requirement_matching(agent, monkeypatch):
    monkeypatch.setenv("PRICE_SPECS_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(preferred_brands=["PhoneMax"])
    p = get_product_by_id("P1009")
    res = agent.compare(reqs, [p])
    assert res.products[0].preferred_matches == 1

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_specification_comparison(agent, monkeypatch):
    monkeypatch.setenv("PRICE_SPECS_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(category="Smartphones")
    p = get_product_by_id("P1009")
    res = agent.compare(reqs, [p])
    specs = res.products[0].specification_comparison
    assert "battery" in specs
    assert "processor" in specs

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_missing_specification(agent, monkeypatch):
    monkeypatch.setenv("PRICE_SPECS_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(category="Smartwatches")
    p = get_product_by_id("P1026") # A smartwatch, should miss non-existent specs gracefully
    res = agent.compare(reqs, [p])
    specs = res.products[0].specification_comparison
    assert isinstance(specs, dict)

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_product_ranking(agent, monkeypatch):
    monkeypatch.setenv("PRICE_SPECS_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(category="Smartphones", budget=50000.0)
    p1 = get_product_by_id("P1009") # in budget ~44k
    p2 = get_product_by_id("P1016") # PhoneMax Z 2 ~98k -> over budget
    res = agent.compare(reqs, [p1, p2])
    # p1 should rank higher than p2
    assert res.products[0].product_id == p1.product_id

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_empty_product_list(agent, monkeypatch):
    monkeypatch.setenv("PRICE_SPECS_AGENT_MOCK_MODE", "true")
    reqs = ShoppingRequirements(category="Smartphones")
    res = agent.compare(reqs, [])
    assert len(res.products) == 0
    assert "No products" in res.summary
