import pytest
import os
from app.agents.requirement_agent import RequirementAgent
from app.agents.price_specs_agent import PriceSpecsAgent, ComparisonResult
from app.agents.review_agent import ReviewAnalysisAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.database.database import load_products, get_product_by_id

def should_skip():
    mock_mode = os.getenv("RECOMMENDATION_AGENT_MOCK_MODE", "false").lower() == "true"
    api_key = os.getenv("GEMINI_API_KEY")
    return not mock_mode and not api_key

@pytest.fixture
def agent():
    return RecommendationAgent()

@pytest.fixture
def full_setup(monkeypatch):
    monkeypatch.setenv("RECOMMENDATION_AGENT_MOCK_MODE", "true")
    monkeypatch.setenv("PRICE_SPECS_AGENT_MOCK_MODE", "true")
    monkeypatch.setenv("REVIEW_AGENT_MOCK_MODE", "true")
    monkeypatch.setenv("REQUIREMENT_AGENT_MOCK_MODE", "true")

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_best_overall(agent, full_setup):
    reqs = RequirementAgent().extract_requirements("I want a smartphone under ₹100,000")
    products = [p for p in load_products() if p.product_id in ["P1009", "P1010"]]
    price_res = PriceSpecsAgent().compare(reqs, products)
    reviews = {p.product_id: ReviewAnalysisAgent().analyze(p.product_id) for p in products}
    
    rec_res = agent.recommend(reqs, price_res, reviews)
    assert rec_res.has_valid_matches == True
    assert rec_res.best_overall is not None
    assert rec_res.best_overall.overall_score > 0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_best_value(agent, full_setup):
    reqs = RequirementAgent().extract_requirements("I want a smartphone under ₹100,000")
    products = [p for p in load_products() if p.product_id in ["P1009", "P1010", "P1011"]]
    price_res = PriceSpecsAgent().compare(reqs, products)
    reviews = {p.product_id: ReviewAnalysisAgent().analyze(p.product_id) for p in products}
    
    rec_res = agent.recommend(reqs, price_res, reviews)
    assert rec_res.best_value is not None
    assert rec_res.best_value.recommendation_type == "Best Value"

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_alternative_generation(agent, full_setup):
    reqs = RequirementAgent().extract_requirements("I want a smartphone under ₹100,000")
    products = [p for p in load_products() if p.category == "Smartphones"][:4]
    price_res = PriceSpecsAgent().compare(reqs, products)
    reviews = {p.product_id: ReviewAnalysisAgent().analyze(p.product_id) for p in products}
    
    rec_res = agent.recommend(reqs, price_res, reviews)
    # 4 products -> 1 overall, 1 value, up to 2 alternatives
    assert len(rec_res.alternatives) > 0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_hard_requirement_priority(agent, full_setup):
    reqs = RequirementAgent().extract_requirements("I want a smartphone under ₹40,000")
    products = [p for p in load_products() if p.product_id in ["P1009", "P1010"]]
    price_res = PriceSpecsAgent().compare(reqs, products)
    reviews = {p.product_id: ReviewAnalysisAgent().analyze(p.product_id) for p in products}
    
    rec_res = agent.recommend(reqs, price_res, reviews)
    # Both are ~44k, so they fail hard requirements.
    assert rec_res.has_valid_matches == False
    assert rec_res.best_overall is None
    # They should show up as alternatives with the correct warning type
    assert len(rec_res.alternatives) > 0
    assert "Over Budget" in rec_res.alternatives[0].recommendation_type

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_review_impact(agent, full_setup):
    reqs = RequirementAgent().extract_requirements("I want a smartphone")
    products = [get_product_by_id("P1009")]
    price_res = PriceSpecsAgent().compare(reqs, products)
    
    # Analyze with real reviews
    reviews_real = {"P1009": ReviewAnalysisAgent().analyze("P1009")}
    rec_res_real = agent.recommend(reqs, price_res, reviews_real)
    score_with_reviews = rec_res_real.best_overall.overall_score
    
    # Analyze without reviews (empty dict)
    rec_res_none = agent.recommend(reqs, price_res, {})
    score_without_reviews = rec_res_none.best_overall.overall_score
    
    # Verify review logic impacts the final score
    assert score_with_reviews != score_without_reviews

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_price_impact(agent, full_setup):
    # Already implicitly tested by price specs agent, but verify recommendation pulls the price summary correctly
    reqs = RequirementAgent().extract_requirements("I want a smartphone under ₹100,000")
    products = [get_product_by_id("P1009")]
    price_res = PriceSpecsAgent().compare(reqs, products)
    rec_res = agent.recommend(reqs, price_res, {})
    
    assert "\u20b9" in rec_res.best_overall.price_summary

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_over_budget_handling(agent, full_setup):
    reqs = RequirementAgent().extract_requirements("I want a smartphone under ₹40,000")
    products = [get_product_by_id("P1009")]
    price_res = PriceSpecsAgent().compare(reqs, products)
    rec_res = agent.recommend(reqs, price_res, {})
    
    assert rec_res.has_valid_matches == False
    assert "No products satisfy your" in rec_res.decision_summary

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_no_matching_products(agent, full_setup):
    reqs = RequirementAgent().extract_requirements("I want a smartphone")
    price_res = ComparisonResult(products=[], best_value_product="None", best_overall_product="None", summary="")
    rec_res = agent.recommend(reqs, price_res, {})
    
    assert rec_res.has_valid_matches == False
    assert rec_res.best_overall is None
    assert "No products" in rec_res.decision_summary

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_missing_review_data(agent, full_setup):
    reqs = RequirementAgent().extract_requirements("I want a smartphone")
    products = [get_product_by_id("P1009")]
    price_res = PriceSpecsAgent().compare(reqs, products)
    
    rec_res = agent.recommend(reqs, price_res, {})
    assert "Limited review data available" in rec_res.best_overall.review_summary

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_recommendation_explanation(agent, full_setup):
    reqs = RequirementAgent().extract_requirements("I want a smartphone")
    products = [get_product_by_id("P1009")]
    price_res = PriceSpecsAgent().compare(reqs, products)
    rec_res = agent.recommend(reqs, price_res, {})
    
    assert len(rec_res.best_overall.why_recommended) > 0
    assert isinstance(rec_res.best_overall.why_recommended[0], str)

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_deterministic_ranking(agent, full_setup):
    reqs = RequirementAgent().extract_requirements("I want a smartphone")
    products = [get_product_by_id("P1009"), get_product_by_id("P1010")]
    price_res = PriceSpecsAgent().compare(reqs, products)
    reviews = {p.product_id: ReviewAnalysisAgent().analyze(p.product_id) for p in products}
    
    res1 = agent.recommend(reqs, price_res, reviews)
    res2 = agent.recommend(reqs, price_res, reviews)
    
    assert res1.best_overall.product_id == res2.best_overall.product_id

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_strict_in_budget_recommendations(agent, full_setup):
    from app.agents.product_search_agent import ProductSearchAgent
    reqs = RequirementAgent().extract_requirements("I want a smartphone under ₹100,000")
    # Using relaxed_budget=False to ensure search only gives strictly in-budget
    search_res = ProductSearchAgent().search(reqs, relaxed_budget=False)
    products = [p for p in load_products() if p.product_id in {r.product_id for r in search_res}]
    price_res = PriceSpecsAgent().compare(reqs, products)
    rec_res = agent.recommend(reqs, price_res, {})
    
    assert rec_res.has_valid_matches == True
    assert rec_res.best_overall is not None
    assert all(c.within_budget for c in price_res.products)

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_over_budget_candidate_retrieval(full_setup):
    from app.agents.product_search_agent import ProductSearchAgent
    reqs = RequirementAgent().extract_requirements("I want a smartphone under ₹40,000")
    
    # Strict mode should return empty
    strict_res = ProductSearchAgent().search(reqs, relaxed_budget=False)
    assert len(strict_res) == 0
    
    # Relaxed mode should retrieve the over-budget candidates
    relaxed_res = ProductSearchAgent().search(reqs, relaxed_budget=True)
    assert len(relaxed_res) > 0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_over_budget_alternatives(agent, full_setup):
    from app.agents.product_search_agent import ProductSearchAgent
    reqs = RequirementAgent().extract_requirements("I want a smartphone under ₹40,000")
    search_res = ProductSearchAgent().search(reqs, relaxed_budget=True)
    products = [p for p in load_products() if p.product_id in {r.product_id for r in search_res}]
    price_res = PriceSpecsAgent().compare(reqs, products)
    rec_res = agent.recommend(reqs, price_res, {})
    
    assert rec_res.has_valid_matches == False
    assert len(rec_res.alternatives) > 0
    assert "Over Budget" in rec_res.alternatives[0].recommendation_type

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_strict_recommendations_never_containing_over_budget(agent, full_setup):
    from app.agents.product_search_agent import ProductSearchAgent
    reqs = RequirementAgent().extract_requirements("I want a smartphone under ₹50,000")
    search_res = ProductSearchAgent().search(reqs, relaxed_budget=True)
    products = [p for p in load_products() if p.product_id in {r.product_id for r in search_res}]
    price_res = PriceSpecsAgent().compare(reqs, products)
    rec_res = agent.recommend(reqs, price_res, {})
    
    # Check that best overall is valid
    assert rec_res.has_valid_matches == True
    assert "Over Budget" not in rec_res.best_overall.recommendation_type
    if rec_res.best_value:
        assert "Over Budget" not in rec_res.best_value.recommendation_type
    
    for alt in rec_res.alternatives:
        assert "Over Budget" not in alt.recommendation_type

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_no_products_satisfying_budget_message(agent, full_setup):
    from app.agents.product_search_agent import ProductSearchAgent
    reqs = RequirementAgent().extract_requirements("I want a smartphone under ₹10,000")
    search_res = ProductSearchAgent().search(reqs, relaxed_budget=True)
    products = [p for p in load_products() if p.product_id in {r.product_id for r in search_res}]
    price_res = PriceSpecsAgent().compare(reqs, products)
    rec_res = agent.recommend(reqs, price_res, {})
    
    assert rec_res.has_valid_matches == False
    assert "No products satisfy your" in rec_res.decision_summary

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_no_stale_recommendation_state(agent, full_setup):
    reqs1 = RequirementAgent().extract_requirements("I want a smartphone under ₹100,000")
    price_res1 = PriceSpecsAgent().compare(reqs1, [get_product_by_id("P1009")])
    rec_res1 = agent.recommend(reqs1, price_res1, {})
    
    reqs2 = RequirementAgent().extract_requirements("I want a smartwatch")
    price_res2 = PriceSpecsAgent().compare(reqs2, [get_product_by_id("P1026")])
    rec_res2 = agent.recommend(reqs2, price_res2, {})
    
    assert rec_res1.best_overall.product_id != rec_res2.best_overall.product_id

