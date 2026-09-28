import json
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError

from app.core.llm import llm_service
from app.database.database import load_products
from app.database.models import Product
from app.agents.requirement_agent import ShoppingRequirements

USD_TO_INR_RATE = 83.0

class SearchResult(BaseModel):
    product_id: str
    match_score: int = Field(description="Score out of 10 indicating how well it matches")
    reason: str = Field(description="Short explanation of why it matches")

class ProductSearchAgent:
    def __init__(self):
        self.system_prompt = """You are a Product Search Agent.
Your job is to match a set of customer shopping requirements against a list of candidate products.
Evaluate each product and return a scored shortlist of the best matches.

CUSTOMER REQUIREMENTS:
{requirements}

CANDIDATE PRODUCTS:
{candidates}

CRITICAL RULES:
1. ONLY return products that are present in the CANDIDATE PRODUCTS list.
2. Rank the products from best match to worst match based on the customer requirements.
3. Keep the reason concise (1-2 sentences).
4. Return a JSON list of matches following this EXACT schema:
[
  {{
    "product_id": "P123",
    "match_score": 9,
    "reason": "Matches 16GB RAM and programming use case."
  }}
]
"""

    def search(self, requirements: ShoppingRequirements, relaxed_budget: bool = False) -> List[SearchResult]:
        """
        Executes a search for products matching the provided requirements.
        Returns a ranked list of SearchResult objects.
        If relaxed_budget is True, products over budget are included as candidates.
        """
        # 1. Hard Filtering
        products = load_products()
        candidates = []
        
        for p in products:
            # Filter by category
            if requirements.category and p.category.lower() != requirements.category.lower():
                continue
                
            # Filter by budget (convert USD to INR)
            price_inr = p.price * USD_TO_INR_RATE
            if not relaxed_budget and requirements.budget and price_inr > requirements.budget:
                continue
                
            # Filter by minimum rating
            if requirements.minimum_rating and p.rating < requirements.minimum_rating:
                continue
                
            candidates.append(p)
            
        if not candidates:
            return []
            
        # 2. Check for Mock Mode
        mock_mode = os.getenv("REQUIREMENT_AGENT_MOCK_MODE", "false").lower() == "true"
        if mock_mode:
            return self._mock_search(requirements, candidates)

        # 3. LLM AI-Powered Soft Matching
        if not llm_service.is_configured():
            return self._mock_search(requirements, candidates)
            
        # Format candidates for the prompt
        candidates_json = []
        for c in candidates:
            c_dict = {
                "id": c.product_id,
                "name": c.name,
                "brand": c.brand,
                "price_usd": c.price,
                "price_inr": c.price * USD_TO_INR_RATE,
                "description": c.description,
                "specifications": c.specifications
            }
            candidates_json.append(c_dict)
            
        prompt = self.system_prompt.format(
            requirements=requirements.model_dump_json(indent=2),
            candidates=json.dumps(candidates_json, indent=2)
        )
        
        try:
            response_data = llm_service.generate_json(prompt)
            # Response could be a list directly, or wrapped in a dict depending on LLM parsing
            if isinstance(response_data, dict) and "matches" in response_data:
                response_data = response_data["matches"]
            elif not isinstance(response_data, list):
                # Fallback, wrap in list if the LLM returns a single object
                response_data = [response_data]
                
            results = []
            for item in response_data:
                results.append(SearchResult(**item))
                
            # Sort by match_score descending
            results.sort(key=lambda x: x.match_score, reverse=True)
            return results
        except Exception as e:
            print(f"Error during AI product search, using fallback: {e}")
            return self._mock_search(requirements, candidates)

    def _mock_search(self, requirements: ShoppingRequirements, candidates: List[Product]) -> List[SearchResult]:
        """Deterministic mock search for tests and local dev."""
        results = []
        for c in candidates:
            score = 5 # Base score
            reason = []
            
            # Simple keyword matching for mock
            c_text = (c.name + " " + c.description + " " + json.dumps(c.specifications)).lower()
            
            if requirements.preferred_brands:
                if any(b.lower() in c.brand.lower() for b in requirements.preferred_brands):
                    score += 2
                    reason.append(f"Brand matches ({c.brand})")
            
            req_matched = 0
            for req in requirements.required_features + requirements.important_specifications:
                # Basic string match
                if any(word.lower() in c_text for word in req.split()):
                    score += 1
                    req_matched += 1
                    
            if req_matched > 0:
                reason.append(f"Matches specs/features")
            else:
                reason.append(f"Fits budget and category")
                
            results.append(SearchResult(
                product_id=c.product_id,
                match_score=min(10, score),
                reason="; ".join(reason)
            ))
            
        results.sort(key=lambda x: x.match_score, reverse=True)
        return results[:3] # Return top 3 for mock
