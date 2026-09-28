import pytest
import os
from app.agents.requirement_agent import RequirementAgent, ShoppingRequirements
from app.agents.product_search_agent import ProductSearchAgent
from app.agents.price_specs_agent import PriceSpecsAgent
from app.agents.review_agent import ReviewAnalysisAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.database.database import load_products, get_product_by_id

@pytest.fixture(autouse=True)
def setup_mock_mode(monkeypatch):
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")
    monkeypatch.setenv("PRICE_SPECS_AGENT_MOCK_MODE", "true")
    monkeypatch.setenv("REVIEW_AGENT_MOCK_MODE", "true")
    monkeypatch.setenv("RECOMMENDATION_AGENT_MOCK_MODE", "true")

# ==========================================
# ISSUE 1: REQUIREMENT EXTRACTION - PREFERRED BRANDS
# ==========================================

def test_preferred_brands_extraction_from_or_list():
    agent = RequirementAgent()
    reqs = agent.extract_requirements("I need a laptop under ₹100,000 with 16GB RAM from HP, Dell, or Lenovo.")
    assert reqs.category == "Laptops"
    assert reqs.budget == 100000.0
    assert "16GB RAM" in reqs.important_specifications
    assert "HP" in reqs.preferred_brands
    assert "Dell" in reqs.preferred_brands
    assert "Lenovo" in reqs.preferred_brands

def test_preferred_brands_variations():
    agent = RequirementAgent()
    req1 = agent.extract_requirements("I prefer HP, Dell, Lenovo laptops")
    assert set(["HP", "Dell", "Lenovo"]).issubset(set(req1.preferred_brands))

    req2 = agent.extract_requirements("brands like HP, Dell, Lenovo")
    assert set(["HP", "Dell", "Lenovo"]).issubset(set(req2.preferred_brands))

# ==========================================
# ISSUE 2: STRICT PRODUCT SEARCH RESULTS
# ==========================================

def test_strict_vs_relaxed_search_count():
    search_agent = ProductSearchAgent()
    reqs = ShoppingRequirements(category="Smartphones", budget=40000)
    
    # Strict search yields 0 because cheapest smartphone is ~₹44,654
    strict_res = search_agent.search(reqs, relaxed_budget=False)
    assert len(strict_res) == 0

    # Relaxed search yields over budget candidates
    relaxed_res = search_agent.search(reqs, relaxed_budget=True)
    assert len(relaxed_res) > 0

# ==========================================
# ISSUE 3 & 4: RECOMMENDATION MATCH CASES
# ==========================================

def test_case_a_no_products_within_budget():
    req_agent = RequirementAgent()
    rec_agent = RecommendationAgent()
    price_agent = PriceSpecsAgent()
    
    reqs = req_agent.extract_requirements("I want a smartphone under ₹40,000.")
    # Search with relaxed budget to get candidates
    search_agent = ProductSearchAgent()
    search_res = search_agent.search(reqs, relaxed_budget=True)
    products = [p for p in load_products() if p.product_id in {r.product_id for r in search_res}]
    
    comp_res = price_agent.compare(reqs, products)
    rec_res = rec_agent.recommend(reqs, comp_res, {})
    
    assert rec_res.match_case == "no_budget_match"
    assert rec_res.has_valid_matches == False
    assert rec_res.best_overall is None
    assert rec_res.best_value is None
    assert len(rec_res.alternatives) > 0
    assert "Over Budget" in rec_res.alternatives[0].recommendation_type
    assert "No products satisfy your" in rec_res.decision_summary or "No products meet your" in rec_res.decision_summary

def test_case_b_in_budget_partial_match():
    # Laptop under ₹100,000 where products exist in budget
    req_agent = RequirementAgent()
    rec_agent = RecommendationAgent()
    price_agent = PriceSpecsAgent()
    
    reqs = req_agent.extract_requirements("I need a laptop under ₹100,000 with 16GB RAM.")
    search_agent = ProductSearchAgent()
    search_res = search_agent.search(reqs, relaxed_budget=False)
    products = [p for p in load_products() if p.product_id in {r.product_id for r in search_res}]
    
    comp_res = price_agent.compare(reqs, products)
    rec_res = rec_agent.recommend(reqs, comp_res, {})
    
    # Should NOT be no_budget_match!
    assert rec_res.match_case in ("full_match", "partial_match")
    assert rec_res.best_overall is not None
    assert "No products meet your budget" not in rec_res.decision_summary

def test_case_c_full_requirement_match():
    reqs = ShoppingRequirements(category="Smartphones", budget=100000)
    products = [get_product_by_id("P1009"), get_product_by_id("P1010")]
    price_res = PriceSpecsAgent().compare(reqs, products)
    rec_res = RecommendationAgent().recommend(reqs, price_res, {})
    
    assert rec_res.match_case == "full_match"
    assert rec_res.has_valid_matches == True
    assert rec_res.best_overall is not None

def test_case_d_no_products():
    reqs = ShoppingRequirements(category="Smartwatches", budget=10)
    price_res = PriceSpecsAgent().compare(reqs, [])
    rec_res = RecommendationAgent().recommend(reqs, price_res, {})
    
    assert rec_res.match_case == "no_products"
    assert rec_res.has_valid_matches == False
    assert rec_res.best_overall is None

# ==========================================
# ISSUE 5: OVER BUDGET ALTERNATIVES NEVER LABELED BEST OVERALL
# ==========================================

def test_over_budget_alternatives_badges():
    reqs = ShoppingRequirements(category="Smartphones", budget=40000)
    search_res = ProductSearchAgent().search(reqs, relaxed_budget=True)
    products = [p for p in load_products() if p.product_id in {r.product_id for r in search_res}]
    price_res = PriceSpecsAgent().compare(reqs, products)
    rec_res = RecommendationAgent().recommend(reqs, price_res, {})
    
    assert rec_res.best_overall is None
    assert rec_res.best_value is None
    for alt in rec_res.alternatives:
        assert alt.recommendation_type == "Over Budget"
        assert "Best Overall" not in alt.recommendation_type
        assert "Best Value" not in alt.recommendation_type

# ==========================================
# ISSUE 9: GEMINI FALLBACK / NO RAW TRACEBACK
# ==========================================

def test_gemini_fallback_friendly_message(monkeypatch):
    monkeypatch.setenv("RECOMMENDATION_AGENT_MOCK_MODE", "false")
    # Simulate LLM throwing 429 quota exception
    def mock_raise_quota(*args, **kwargs):
        raise Exception("429 RESOURCE_EXHAUSTED: Quota exceeded")
    
    from app.core.llm import llm_service
    monkeypatch.setattr(llm_service, "generate_json", mock_raise_quota)
    monkeypatch.setattr(llm_service, "is_configured", lambda: True)

    reqs = ShoppingRequirements(category="Smartphones", budget=100000)
    products = [get_product_by_id("P1009")]
    price_res = PriceSpecsAgent().compare(reqs, products)
    rec_res = RecommendationAgent().recommend(reqs, price_res, {})

    assert rec_res.best_overall is not None
    assert "AI explanation is temporarily unavailable" in rec_res.decision_summary
    assert "RESOURCE_EXHAUSTED" not in rec_res.decision_summary
