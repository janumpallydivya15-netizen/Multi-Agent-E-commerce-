import json
import os
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from app.core.llm import llm_service
from app.agents.requirement_agent import ShoppingRequirements
from app.agents.price_specs_agent import ComparisonResult, ProductComparison
from app.agents.review_agent import ReviewAnalysis

class Recommendation(BaseModel):
    product_id: str
    product_name: str
    rank: int
    overall_score: float
    recommendation_type: str
    why_recommended: List[str]
    strengths: List[str]
    weaknesses: List[str]
    review_summary: str
    price_summary: str
    requirement_match_summary: str

class RecommendationResult(BaseModel):
    best_overall: Optional[Recommendation] = None
    best_value: Optional[Recommendation] = None
    alternatives: List[Recommendation] = Field(default_factory=list)
    decision_summary: str = ""
    has_valid_matches: bool = False
    match_case: str = Field("no_products", description="One of: 'full_match', 'partial_match', 'no_budget_match', 'no_products'")
    llm_explanation_available: bool = True

class RecommendationAgent:
    def __init__(self):
        self.system_prompt = """You are a Recommendation Agent.
Your job is to provide clear, explainable summaries for product recommendations based on existing numeric scores and assignments.

We have already selected the Best Overall, Best Value, and Alternatives, and scored them.
DO NOT change the assignments, scores, or product selections.

INPUT DATA:
{input_json}

CRITICAL RULES:
1. For each product provided, generate a list of 2-3 specific reasons it is recommended (`why_recommended`).
2. Generate an overall `decision_summary` explaining the recommendations as a whole.
3. Be specific, referencing actual reviews, specs, and price. Do not invent data.
4. Return a JSON object matching this exact schema:
{{
  "decision_summary": "...",
  "recommendations": {{
    "P123": {{
      "why_recommended": ["...", "..."]
    }},
    "P456": {{
      "why_recommended": ["...", "..."]
    }}
  }}
}}
"""

    def recommend(self, requirements: ShoppingRequirements, price_comparisons: ComparisonResult, reviews: Dict[str, ReviewAnalysis]) -> RecommendationResult:
        if not price_comparisons.products:
            return RecommendationResult(
                best_overall=None,
                best_value=None,
                alternatives=[],
                decision_summary="No products found for the requested category.",
                has_valid_matches=False,
                match_case="no_products"
            )

        scored_products = []
        for comp in price_comparisons.products:
            review = reviews.get(comp.product_id)
            
            # Review Impact (20% weight if valid)
            if review and review.review_count > 0:
                review_score = (review.average_rating / 5.0) * 100
                review_summary = f"{review.average_rating}/5 stars from {review.review_count} reviews. {review.overall_sentiment} sentiment."
            else:
                review_score = 60.0 # Neutral fallback
                review_summary = "Limited review data available."

            # Calculate Final Score: PriceSpecs (80%) + Reviews (20%)
            final_score = (comp.score * 0.8) + (review_score * 0.2)
            
            in_budget = comp.within_budget
            full_req = (comp.required_matches == comp.required_total)
            
            if not in_budget:
                rec_type = "Over Budget"
            elif not full_req:
                rec_type = "Partial Match"
            else:
                rec_type = "Valid"

            strengths = comp.strengths.copy()
            weaknesses = comp.weaknesses.copy()
            if review:
                strengths.extend(review.positive_themes[:2])
                weaknesses.extend(review.common_complaints[:2])

            scored_products.append({
                "comp": comp,
                "review": review,
                "final_score": final_score,
                "in_budget": in_budget,
                "full_req": full_req,
                "rec_type": rec_type,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "review_summary": review_summary
            })

        # Sort all products by score descending
        scored_products.sort(key=lambda x: x["final_score"], reverse=True)

        in_budget_full = [p for p in scored_products if p["in_budget"] and p["full_req"]]
        in_budget_partial = [p for p in scored_products if p["in_budget"] and not p["full_req"]]
        in_budget_all = [p for p in scored_products if p["in_budget"]]
        over_budget_all = [p for p in scored_products if not p["in_budget"]]

        best_overall = None
        best_value = None
        alternatives = []

        if len(in_budget_full) > 0:
            # CASE C — FULL REQUIREMENT MATCH
            match_case = "full_match"
            has_valid = True
            
            best_overall_data = in_budget_full[0]
            best_overall_data["rec_type"] = "Best Overall"
            best_overall = self._build_recommendation(best_overall_data, 1)

            if len(in_budget_full) > 1:
                value_candidates = in_budget_full[1:]
                best_value_data = max(value_candidates, key=lambda x: x["final_score"] / max(x["comp"].price, 1))
                best_value_data["rec_type"] = "Best Value"
                best_value = self._build_recommendation(best_value_data, 2)

                used_ids = {best_overall.product_id, best_value.product_id}
                alt_rank = 3
                for p in in_budget_full:
                    if p["comp"].product_id not in used_ids and len(alternatives) < 2:
                        p["rec_type"] = "Alternative"
                        alternatives.append(self._build_recommendation(p, alt_rank))
                        alt_rank += 1
        elif len(in_budget_all) > 0:
            # CASE B — PRODUCTS WITHIN BUDGET BUT NOT ALL REQUIREMENTS MATCH
            match_case = "partial_match"
            has_valid = True  # We have in-budget options!
            
            best_overall_data = in_budget_all[0]
            best_overall_data["rec_type"] = "Best Available Match"
            best_overall = self._build_recommendation(best_overall_data, 1)

            if len(in_budget_all) > 1:
                value_candidates = in_budget_all[1:]
                best_value_data = max(value_candidates, key=lambda x: x["final_score"] / max(x["comp"].price, 1))
                best_value_data["rec_type"] = "Best Value"
                best_value = self._build_recommendation(best_value_data, 2)

                used_ids = {best_overall.product_id, best_value.product_id}
                alt_rank = 3
                for p in in_budget_all:
                    if p["comp"].product_id not in used_ids and len(alternatives) < 2:
                        p["rec_type"] = "Alternative"
                        alternatives.append(self._build_recommendation(p, alt_rank))
                        alt_rank += 1
        else:
            # CASE A — NO PRODUCTS WITHIN BUDGET
            match_case = "no_budget_match"
            has_valid = False
            best_overall = None
            best_value = None

            alt_rank = 1
            for p in over_budget_all[:3]:
                p["rec_type"] = "Over Budget"
                alternatives.append(self._build_recommendation(p, alt_rank))
                alt_rank += 1

        result = RecommendationResult(
            best_overall=best_overall,
            best_value=best_value,
            alternatives=alternatives,
            decision_summary="",
            has_valid_matches=has_valid,
            match_case=match_case
        )

        mock_mode = os.getenv("RECOMMENDATION_AGENT_MOCK_MODE", "false").lower() == "true"
        if mock_mode:
            return self._mock_explain(result, requirements)
        return self._gemini_explain(result, requirements)

    def _build_recommendation(self, data: Dict, rank: int) -> Recommendation:
        comp = data["comp"]
        return Recommendation(
            product_id=comp.product_id,
            product_name=comp.product_name,
            rank=rank,
            overall_score=round(data["final_score"], 1),
            recommendation_type=data["rec_type"],
            why_recommended=[],
            strengths=list(set(data["strengths"])),
            weaknesses=list(set(data["weaknesses"])),
            review_summary=data["review_summary"],
            price_summary=f"\u20b9{comp.price:,.0f} (Budget: \u20b9{comp.budget:,.0f})" if comp.budget else f"\u20b9{comp.price:,.0f}",
            requirement_match_summary=f"Required: {comp.required_matches}/{comp.required_total} | Preferred: {comp.preferred_matches}/{comp.preferred_total}"
        )

    def _mock_explain(self, result: RecommendationResult, requirements: ShoppingRequirements) -> RecommendationResult:
        result.llm_explanation_available = False
        
        if result.match_case == "no_budget_match":
            if requirements.budget:
                result.decision_summary = f"⚠️ No products satisfy your \u20b9{requirements.budget:,.0f} budget constraint. Showing over-budget alternatives."
            else:
                result.decision_summary = "⚠️ No products satisfy your budget constraint. Showing over-budget alternatives."
        elif result.match_case == "partial_match":
            result.decision_summary = "\u26a0\ufe0f No product fully matches all your requirements. Showing best available in-budget candidates based on price and specification analysis."
        elif result.match_case == "no_products":
            result.decision_summary = "No products found for the requested category."
        else:
            result.decision_summary = "Based on your requirements, here are the top recommendations balancing specifications, reviews, and budget."
            
        for rec in [result.best_overall, result.best_value] + result.alternatives:
            if not rec:
                continue
            if rec.recommendation_type in ("Best Overall", "Best Available Match"):
                rec.why_recommended = ["Strongest overall fit within budget", "Positive customer review consensus", "Solid specification balance"]
            elif rec.recommendation_type == "Best Value":
                rec.why_recommended = ["Excellent price-to-performance ratio within budget", "Meets key specifications efficiently"]
            elif "Over Budget" in rec.recommendation_type:
                rec.why_recommended = ["Strong features but exceeds requested budget"]
            else:
                rec.why_recommended = ["Solid alternative option within budget", "Meets core requirements"]
                
        return result

    def _gemini_explain(self, result: RecommendationResult, requirements: ShoppingRequirements) -> RecommendationResult:
        if not llm_service.is_configured():
            return self._mock_explain(result, requirements)
            
        state_data = {
            "match_case": result.match_case,
            "has_valid_matches": result.has_valid_matches,
            "budget": requirements.budget,
            "products": {}
        }
        
        for rec in [result.best_overall, result.best_value] + result.alternatives:
            if rec:
                state_data["products"][rec.product_id] = {
                    "name": rec.product_name,
                    "type": rec.recommendation_type,
                    "strengths": rec.strengths,
                    "weaknesses": rec.weaknesses,
                    "review_summary": rec.review_summary
                }
                
        prompt = self.system_prompt.format(input_json=json.dumps(state_data, indent=2))
        
        try:
            response_data = llm_service.generate_json(prompt)
            result.decision_summary = response_data.get("decision_summary", "Recommendations prepared.")
            recs_data = response_data.get("recommendations", {})
            
            for rec in [result.best_overall, result.best_value] + result.alternatives:
                if rec and rec.product_id in recs_data:
                    rec.why_recommended = recs_data[rec.product_id].get("why_recommended", ["Selected based on match."])
                    
            result.llm_explanation_available = True
            return result
        except Exception as e:
            print(f"Error during AI recommendation explanation, using fallback: {e}")
            result = self._mock_explain(result, requirements)
            result.decision_summary = f"AI explanation is temporarily unavailable. Recommendations are based on product, price, specification, and review analysis. {result.decision_summary}"
            return result
