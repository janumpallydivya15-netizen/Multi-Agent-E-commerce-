import json
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.llm import llm_service
from app.database.models import Product
from app.agents.requirement_agent import ShoppingRequirements

USD_TO_INR_RATE = 83.0

class ProductComparison(BaseModel):
    product_id: str
    product_name: str
    price: float
    budget: Optional[float]
    within_budget: bool
    required_matches: int
    required_total: int
    preferred_matches: int
    preferred_total: int
    specification_comparison: Dict[str, str]
    score: float
    strengths: List[str]
    weaknesses: List[str]

class ComparisonResult(BaseModel):
    products: List[ProductComparison]
    best_value_product: str
    best_overall_product: str
    summary: str

class PriceSpecsAgent:
    def __init__(self):
        self.system_prompt = """You are a Price & Specification Comparison Agent.
Your job is to compare a list of products against the user's requirements and provide a helpful summary.

We have already calculated the numeric scores, rankings, and hard filter checks.
Do NOT invent new specifications or prices.

PRODUCTS:
{products_json}

REQUIREMENTS:
{requirements_json}

CRITICAL RULES:
1. Provide a concise 2-3 sentence summary explaining the best overall product and the best value product based on the provided data.
2. Return a JSON object containing the summary and the product IDs of the best overall and best value.
3. Return EXACTLY a JSON object matching this schema:
{{
  "summary": "...",
  "best_value_product_id": "...",
  "best_overall_product_id": "..."
}}
"""

    def compare(self, requirements: ShoppingRequirements, products: List[Product]) -> ComparisonResult:
        if not products:
            return ComparisonResult(
                products=[],
                best_value_product="None",
                best_overall_product="None",
                summary="No products were provided for comparison."
            )
            
        comparisons = []
        for p in products:
            comp = self._evaluate_product(requirements, p)
            comparisons.append(comp)
            
        # Sort by score descending
        comparisons.sort(key=lambda x: x.score, reverse=True)
        
        mock_mode = os.getenv("PRICE_SPECS_AGENT_MOCK_MODE", "false").lower() == "true"
        if mock_mode:
            return self._mock_summary(comparisons)
            
        return self._gemini_summary(requirements, comparisons)

    def _evaluate_product(self, requirements: ShoppingRequirements, p: Product) -> ProductComparison:
        price_inr = p.price * USD_TO_INR_RATE
        
        # Build conditions
        required_conds = []
        if requirements.category:
            required_conds.append(("category", requirements.category))
        if requirements.budget is not None:
            required_conds.append(("budget", requirements.budget))
        for feat in requirements.required_features:
            required_conds.append(("feature", feat))
        for spec in requirements.important_specifications:
            required_conds.append(("feature", spec))
            
        preferred_conds = []
        for purp in requirements.purpose:
            preferred_conds.append(("feature", purp))
        for b in requirements.preferred_brands:
            preferred_conds.append(("brand", b))
        for pf in requirements.preferred_features:
            preferred_conds.append(("feature", pf))
        if requirements.minimum_rating is not None:
            preferred_conds.append(("rating", requirements.minimum_rating))
            
        req_matches = 0
        req_total = len(required_conds)
        pref_matches = 0
        pref_total = len(preferred_conds)
        
        strengths = []
        weaknesses = []
        
        c_text = (p.name + " " + p.description + " " + json.dumps(p.specifications)).lower()
        
        within_budget = True
        
        for kind, val in required_conds:
            if kind == "category":
                if p.category.lower() == val.lower():
                    req_matches += 1
                else:
                    weaknesses.append(f"Different category: {p.category}")
            elif kind == "budget":
                if price_inr <= val:
                    req_matches += 1
                else:
                    within_budget = False
                    weaknesses.append(f"Over budget by \u20b9{(price_inr - val):,.0f}")
            elif kind == "feature":
                if all(word in c_text for word in val.lower().split()):
                    req_matches += 1
                    strengths.append(f"Has {val}")
                else:
                    weaknesses.append(f"Missing {val}")
                    
        for kind, val in preferred_conds:
            if kind == "feature":
                if all(word in c_text for word in val.lower().split()):
                    pref_matches += 1
                    strengths.append(f"Has {val}")
            elif kind == "brand":
                if val.lower() in p.brand.lower():
                    pref_matches += 1
            elif kind == "rating":
                if p.rating >= val:
                    pref_matches += 1
                    
        # Extract specs dynamically based on category
        specs_to_compare = {}
        if p.category.lower() == "smartphones":
            keys = ['processor', 'ram', 'storage', 'display', 'battery', 'camera']
        elif p.category.lower() == "laptops":
            keys = ['processor', 'ram', 'storage', 'display', 'battery']
        elif p.category.lower() == "headphones":
            keys = ['driver_size', 'battery_life', 'noise_cancellation', 'connectivity', 'weight']
        elif p.category.lower() == "smartwatches":
            keys = ['display', 'battery_life', 'gps', 'sensors', 'water_resistance', 'compatibility']
        else:
            keys = list(p.specifications.keys())[:5]
            
        for k in keys:
            if k in p.specifications:
                specs_to_compare[k] = str(p.specifications[k])
                
        # Score Calculation
        # 70% required, 20% preferred, 10% price
        score_req = (req_matches / req_total * 70) if req_total > 0 else 70
        score_pref = (pref_matches / pref_total * 20) if pref_total > 0 else 20
        
        # Price score logic
        if requirements.budget and requirements.budget > 0:
            if price_inr <= requirements.budget:
                score_price = 10 * (1.0 - (price_inr / (requirements.budget * 1.5)))
                score_price = max(0, min(10, score_price))
            else:
                score_price = 0
        else:
            score_price = 5 # Default if no budget
            
        score = score_req + score_pref + score_price
        
        # Hard requirement penalty
        if req_matches < req_total:
            score = min(69.0, score * 0.7) # Cap at 69, heavily penalize
            
        return ProductComparison(
            product_id=p.product_id,
            product_name=p.name,
            price=price_inr,
            budget=requirements.budget,
            within_budget=within_budget,
            required_matches=req_matches,
            required_total=req_total,
            preferred_matches=pref_matches,
            preferred_total=pref_total,
            specification_comparison=specs_to_compare,
            score=round(score, 1),
            strengths=strengths,
            weaknesses=weaknesses
        )

    def _mock_summary(self, comparisons: List[ProductComparison]) -> ComparisonResult:
        if not comparisons:
            return ComparisonResult(
                products=[],
                best_value_product="None",
                best_overall_product="None",
                summary="No products available."
            )
        best_overall = comparisons[0]
        # Best value: cheapest among those meeting all required (or just highest score/price ratio)
        valid_comps = [c for c in comparisons if c.required_matches == c.required_total]
        if valid_comps:
            best_value = min(valid_comps, key=lambda x: x.price)
        else:
            best_value = comparisons[0]
            
        summary = f"The {best_overall.product_name} is the best overall choice scoring {best_overall.score}/100. The {best_value.product_name} offers the best value."
        
        return ComparisonResult(
            products=comparisons,
            best_value_product=best_value.product_id,
            best_overall_product=best_overall.product_id,
            summary=summary
        )

    def _gemini_summary(self, requirements: ShoppingRequirements, comparisons: List[ProductComparison]) -> ComparisonResult:
        if not llm_service.is_configured():
            return self._mock_summary(comparisons)
            
        comps_data = []
        for c in comparisons:
            comps_data.append({
                "id": c.product_id,
                "name": c.product_name,
                "score": c.score,
                "price": c.price,
                "required_met": f"{c.required_matches}/{c.required_total}",
                "strengths": c.strengths,
                "weaknesses": c.weaknesses
            })
            
        prompt = self.system_prompt.format(
            requirements_json=requirements.model_dump_json(indent=2),
            products_json=json.dumps(comps_data, indent=2)
        )
        
        try:
            response_data = llm_service.generate_json(prompt)
            return ComparisonResult(
                products=comparisons,
                best_value_product=response_data.get("best_value_product_id", comparisons[0].product_id),
                best_overall_product=response_data.get("best_overall_product_id", comparisons[0].product_id),
                summary=response_data.get("summary", "Analysis complete.")
            )
        except Exception as e:
            print(f"Error during AI price specs analysis, using fallback: {e}")
            return self._mock_summary(comparisons)
