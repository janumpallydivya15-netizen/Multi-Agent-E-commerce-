import json
import os
import re
from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.llm import llm_service
from app.database.database import get_reviews_for_product, get_product_by_id
from app.database.models import Review, Product

class ReviewAnalysis(BaseModel):
    product_id: str
    product_name: str
    review_count: int
    average_rating: float
    positive_count: int
    neutral_count: int
    negative_count: int
    overall_sentiment: str
    positive_themes: List[str]
    negative_themes: List[str]
    common_complaints: List[str]
    common_strengths: List[str]
    summary: str

class ReviewAnalysisAgent:
    def __init__(self):
        self.system_prompt = """You are a Review Analysis Agent.
Your job is to analyze a list of customer reviews for a specific product and provide a structured summary.

PRODUCT: {product_name} (ID: {product_id})

REVIEWS:
{reviews_json}

CRITICAL RULES:
1. Base your analysis ONLY on the provided reviews. Do not invent information.
2. Determine the overall sentiment (Positive, Neutral, Mixed, Negative).
3. Identify positive and negative themes (e.g., Battery, Performance, Build Quality).
4. Identify common complaints and strengths.
5. Provide a concise 1-2 sentence summary.
6. Return EXACTLY a JSON object matching this schema:
{schema}
"""

    def analyze(self, product_id: str) -> Optional[ReviewAnalysis]:
        product = get_product_by_id(product_id)
        if not product:
            return None
            
        reviews = get_reviews_for_product(product_id)
        
        mock_mode = os.getenv("REVIEW_AGENT_MOCK_MODE", "false").lower() == "true"
        if mock_mode:
            return self._mock_analyze(product_id, product.name, reviews)
            
        return self._gemini_analyze(product_id, product.name, reviews)
        
    def _gemini_analyze(self, product_id: str, product_name: str, reviews: List[Review]) -> ReviewAnalysis:
        if not llm_service.is_configured():
            return self._mock_analyze(product_id, product_name, reviews)
            
        if not reviews:
            return self._empty_analysis(product_id, product_name)
            
        reviews_data = [
            {"rating": r.rating, "text": r.review_text} for r in reviews
        ]
        
        schema_json = json.dumps(ReviewAnalysis.model_json_schema(), indent=2)
        prompt = self.system_prompt.format(
            product_name=product_name,
            product_id=product_id,
            reviews_json=json.dumps(reviews_data, indent=2),
            schema=schema_json
        )
        
        try:
            response_data = llm_service.generate_json(prompt)
            return ReviewAnalysis(**response_data)
        except Exception as e:
            print(f"Error during AI review analysis, using fallback: {e}")
            return self._mock_analyze(product_id, product_name, reviews)
            
    def _empty_analysis(self, product_id: str, product_name: str) -> ReviewAnalysis:
        return ReviewAnalysis(
            product_id=product_id,
            product_name=product_name,
            review_count=0,
            average_rating=0.0,
            positive_count=0,
            neutral_count=0,
            negative_count=0,
            overall_sentiment="Neutral",
            positive_themes=[],
            negative_themes=[],
            common_complaints=[],
            common_strengths=[],
            summary="No reviews available for this product."
        )

    def _mock_analyze(self, product_id: str, product_name: str, reviews: List[Review]) -> ReviewAnalysis:
        if not reviews:
            return self._empty_analysis(product_id, product_name)
            
        pos = 0
        neu = 0
        neg = 0
        total_rating = 0
        
        pos_themes = set()
        neg_themes = set()
        
        theme_keywords = {
            "battery": "Battery", "performance": "Performance", "fast": "Performance", "slow": "Performance",
            "camera": "Camera", "display": "Display", "screen": "Display", "build": "Build Quality",
            "sturdy": "Build Quality", "sound": "Audio/Sound", "audio": "Audio/Sound", "comfort": "Comfort",
            "price": "Price/Value", "value": "Price/Value", "software": "Software", "heating": "Heating",
            "warm": "Heating", "hot": "Heating", "charging": "Charging", "design": "Design", "look": "Design"
        }
        
        for r in reviews:
            total_rating += r.rating
            text_lower = r.review_text.lower()
            
            if r.rating >= 4:
                pos += 1
                for kw, theme in theme_keywords.items():
                    if kw in text_lower: pos_themes.add(theme)
            elif r.rating == 3:
                neu += 1
                for kw, theme in theme_keywords.items():
                    if kw in text_lower: 
                        pos_themes.add(theme)
                        neg_themes.add(theme)
            else:
                neg += 1
                for kw, theme in theme_keywords.items():
                    if kw in text_lower: neg_themes.add(theme)
                    
        avg = total_rating / len(reviews)
        
        if avg >= 4.0:
            sentiment = "Positive"
            summary = "Reviews are mostly positive, with users praising various features."
        elif avg <= 2.5:
            sentiment = "Negative"
            summary = "Reviews are mostly negative, with users highlighting several issues."
        else:
            sentiment = "Mixed"
            summary = "Reviews are mixed, with both praise and criticism."
            
        return ReviewAnalysis(
            product_id=product_id,
            product_name=product_name,
            review_count=len(reviews),
            average_rating=round(avg, 1),
            positive_count=pos,
            neutral_count=neu,
            negative_count=neg,
            overall_sentiment=sentiment,
            positive_themes=sorted(list(pos_themes))[:5],
            negative_themes=sorted(list(neg_themes))[:5],
            common_complaints=sorted(list(neg_themes))[:3],
            common_strengths=sorted(list(pos_themes))[:3],
            summary=summary
        )
