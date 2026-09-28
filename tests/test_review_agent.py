import pytest
import os
from app.agents.review_agent import ReviewAnalysisAgent
from app.database.models import Review

def should_skip():
    mock_mode = os.getenv("REVIEW_AGENT_MOCK_MODE", "false").lower() == "true"
    api_key = os.getenv("GEMINI_API_KEY")
    return not mock_mode and not api_key

@pytest.fixture
def agent():
    return ReviewAnalysisAgent()

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_review_loading_and_positive_sentiment(agent, monkeypatch):
    monkeypatch.setenv("REVIEW_AGENT_MOCK_MODE", "true")
    # P1001 exists and has reviews
    analysis = agent.analyze("P1001")
    assert analysis is not None
    assert analysis.product_id == "P1001"
    assert analysis.review_count > 0
    assert analysis.average_rating >= 1.0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_empty_reviews(agent, monkeypatch):
    monkeypatch.setenv("REVIEW_AGENT_MOCK_MODE", "true")
    analysis = agent._mock_analyze("P_FAKE", "Fake Product", [])
    assert analysis.review_count == 0
    assert analysis.overall_sentiment == "Neutral"
    assert analysis.average_rating == 0.0

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_nonexistent_product(agent, monkeypatch):
    monkeypatch.setenv("REVIEW_AGENT_MOCK_MODE", "true")
    analysis = agent.analyze("NONEXISTENT_PRODUCT_999")
    assert analysis is None

@pytest.mark.skipif(should_skip(), reason="Neither LLM nor MOCK mode configured")
def test_sentiment_and_themes(agent, monkeypatch):
    monkeypatch.setenv("REVIEW_AGENT_MOCK_MODE", "true")
    # Provide synthetic reviews to test deterministic logic
    reviews = [
        Review(review_id="1", product_id="P1", rating=5, review_text="Amazing battery and great performance.", sentiment_hint=""),
        Review(review_id="2", product_id="P1", rating=1, review_text="Terrible heating issues and awful camera.", sentiment_hint="")
    ]
    analysis = agent._mock_analyze("P1", "Test Product", reviews)
    assert analysis.average_rating == 3.0
    assert analysis.overall_sentiment == "Mixed"
    assert analysis.positive_count == 1
    assert analysis.negative_count == 1
    
    # Check themes extraction
    assert "Battery" in analysis.positive_themes
    assert "Performance" in analysis.positive_themes
    assert "Heating" in analysis.negative_themes
    assert "Camera" in analysis.negative_themes
