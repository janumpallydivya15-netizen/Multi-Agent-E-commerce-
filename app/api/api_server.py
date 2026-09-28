"""
FastAPI backend for the Multi-Agent E-Commerce Assistant.
Wraps existing agents without duplicating any business logic.
"""
import dataclasses
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Ensure project root is on path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load .env
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

# Import existing agents (no logic duplication)
from app.agents.requirement_agent import RequirementAgent, ShoppingRequirements
from app.agents.product_search_agent import ProductSearchAgent
from app.agents.review_agent import ReviewAnalysisAgent
from app.agents.price_specs_agent import PriceSpecsAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.database.database import load_products, get_product_by_id
from app.database.models import Product
from app.core.config import Config
from app.workflows.shopping_workflow import run_shopping_workflow

# ─── App Setup ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Multi-Agent E-Commerce Assistant API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Serialization Helpers ──────────────────────────────────────────────────

def product_to_dict(p: Product) -> Dict[str, Any]:
    """Convert a Product dataclass to a JSON-serialisable dict."""
    return {
        "product_id": p.product_id,
        "name": p.name,
        "brand": p.brand,
        "category": p.category,
        "price_usd": p.price,
        "price_inr": round(p.price * 83.0, 2),
        "currency": p.currency,
        "rating": p.rating,
        "review_count": p.review_count,
        "description": p.description,
        "specifications": p.specifications,
    }


def ok(data: Any) -> Dict:
    return {"success": True, "data": data}


def err(message: str) -> Dict:
    return {"success": False, "error": message}


# ─── Request Models ─────────────────────────────────────────────────────────

class RequirementsRequest(BaseModel):
    request: str


class ProductSearchRequest(BaseModel):
    requirements: Dict[str, Any]
    relaxed_budget: bool = False


class CompareRequest(BaseModel):
    requirements: Dict[str, Any]
    product_ids: List[str]


class RecommendationRequest(BaseModel):
    requirements: Dict[str, Any]
    product_ids: List[str]


class ShoppingRequest(BaseModel):
    request: str


# ─── API Endpoints ──────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    """System health check."""
    try:
        diagnostics = Config.validate_startup()
        return ok(diagnostics)
    except Exception as e:
        return err(str(e))


@app.post("/api/requirements")
def extract_requirements(body: RequirementsRequest):
    """Phase 4 — Requirement Agent: extract structured requirements from natural language."""
    try:
        agent = RequirementAgent()
        reqs = agent.extract_requirements(body.request)
        return ok(reqs.model_dump())
    except RuntimeError as e:
        return err(str(e))
    except Exception as e:
        return err(f"Unable to analyze requirements: {str(e)}")


@app.post("/api/products/search")
def search_products(body: ProductSearchRequest):
    """Phase 5 — Product Search Agent: find products matching requirements."""
    try:
        # Reconstruct ShoppingRequirements from the dict
        reqs = ShoppingRequirements(**body.requirements)
        agent = ProductSearchAgent()
        search_results = agent.search(reqs, relaxed_budget=body.relaxed_budget)

        # Merge search results with full product data
        all_products = {p.product_id: p for p in load_products()}
        merged = []
        for sr in search_results:
            p = all_products.get(sr.product_id)
            if p:
                d = product_to_dict(p)
                d["match_score"] = sr.match_score
                d["match_reason"] = sr.reason
                merged.append(d)

        strict_matches = [d for d in merged if reqs.budget is None or d["price_inr"] <= reqs.budget]
        over_budget_candidates = [d for d in merged if reqs.budget is not None and d["price_inr"] > reqs.budget]

        return ok({
            "products": merged,
            "strict_matches": strict_matches,
            "over_budget_candidates": over_budget_candidates,
            "strict_count": len(strict_matches),
            "in_budget_count": len(strict_matches),
            "over_budget_count": len(over_budget_candidates),
            "total": len(merged),
            "relaxed_budget": body.relaxed_budget,
        })
    except Exception as e:
        return err(f"Product search failed: {str(e)}")


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    """Get a single product by ID."""
    p = get_product_by_id(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return ok(product_to_dict(p))


@app.get("/api/products/{product_id}/reviews")
def get_product_reviews(product_id: str):
    """Phase 6 — Review Analysis Agent: analyse reviews for a product."""
    try:
        agent = ReviewAnalysisAgent()
        analysis = agent.analyze(product_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Product not found")
        return ok(analysis.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        return err(f"Review analysis failed: {str(e)}")


@app.post("/api/compare")
def compare_products(body: CompareRequest):
    """Phase 7 — Price & Specification Agent: compare selected products."""
    try:
        reqs = ShoppingRequirements(**body.requirements)
        products = [p for p in load_products() if p.product_id in body.product_ids]
        if not products:
            return ok({"products": [], "best_value_product": None, "best_overall_product": None, "summary": "No products to compare."})

        agent = PriceSpecsAgent()
        result = agent.compare(reqs, products)
        return ok({
            "products": [pc.model_dump() for pc in result.products],
            "best_value_product": result.best_value_product,
            "best_overall_product": result.best_overall_product,
            "summary": result.summary,
        })
    except Exception as e:
        return err(f"Comparison failed: {str(e)}")


@app.post("/api/recommendations")
def get_recommendations(body: RecommendationRequest):
    """Phase 8 — Recommendation Agent: generate ranked recommendations."""
    try:
        reqs = ShoppingRequirements(**body.requirements)
        products = [p for p in load_products() if p.product_id in body.product_ids]
        if not products:
            return ok({"has_valid_matches": False, "match_case": "no_products", "decision_summary": "No products provided.", "best_overall": None, "best_value": None, "alternatives": []})

        # Run review analysis for each product
        review_agent = ReviewAnalysisAgent()
        reviews = {}
        for p in products:
            analysis = review_agent.analyze(p.product_id)
            if analysis:
                reviews[p.product_id] = analysis

        # Compare
        price_agent = PriceSpecsAgent()
        comparison = price_agent.compare(reqs, products)

        # Recommend
        rec_agent = RecommendationAgent()
        result = rec_agent.recommend(reqs, comparison, reviews)

        def rec_to_dict(r):
            if r is None:
                return None
            return r.model_dump()

        return ok({
            "has_valid_matches": result.has_valid_matches,
            "match_case": result.match_case,
            "decision_summary": result.decision_summary,
            "best_overall": rec_to_dict(result.best_overall),
            "best_value": rec_to_dict(result.best_value),
            "alternatives": [rec_to_dict(a) for a in result.alternatives if a is not None],
            "llm_explanation_available": result.llm_explanation_available,
        })
    except Exception as e:
        return err(f"Recommendation failed: {str(e)}")


@app.post("/api/shopping")
def full_shopping_workflow(body: ShoppingRequest):
    """Full multi-agent workflow via LangGraph."""
    try:
        state = run_shopping_workflow(body.request)

        # Serialize state carefully — mix of Pydantic models and dataclasses
        reqs_data = state["requirements"].model_dump() if state.get("requirements") else None

        search_data = []
        if state.get("search_results"):
            all_products = {p.product_id: p for p in load_products()}
            for sr in state["search_results"]:
                p = all_products.get(sr.product_id)
                if p:
                    d = product_to_dict(p)
                    d["match_score"] = sr.match_score
                    d["match_reason"] = sr.reason
                    search_data.append(d)

        reviews_data = {}
        if state.get("review_results"):
            for pid, ra in state["review_results"].items():
                reviews_data[pid] = ra.model_dump()

        comparison_data = None
        if state.get("comparison_results"):
            cr = state["comparison_results"]
            comparison_data = {
                "products": [pc.model_dump() for pc in cr.products],
                "best_value_product": cr.best_value_product,
                "best_overall_product": cr.best_overall_product,
                "summary": cr.summary,
            }

        recommendation_data = None
        if state.get("recommendation_result"):
            rr = state["recommendation_result"]
            recommendation_data = {
                "has_valid_matches": rr.has_valid_matches,
                "match_case": getattr(rr, "match_case", "no_products"),
                "decision_summary": rr.decision_summary,
                "best_overall": rr.best_overall.model_dump() if rr.best_overall else None,
                "best_value": rr.best_value.model_dump() if rr.best_value else None,
                "alternatives": [a.model_dump() for a in rr.alternatives if a is not None],
                "llm_explanation_available": getattr(rr, "llm_explanation_available", True),
            }

        return ok({
            "user_request": state["user_request"],
            "requirements": reqs_data,
            "products": search_data,
            "reviews": reviews_data,
            "comparison": comparison_data,
            "recommendations": recommendation_data,
            "error": state.get("error"),
            "steps_completed": _get_completed_steps(state),
        })
    except Exception as e:
        return err(f"Workflow failed: {str(e)}")


def _get_completed_steps(state: dict) -> List[str]:
    steps = []
    if state.get("requirements"):
        steps.append("requirements")
    if state.get("search_results"):
        steps.append("products")
    if state.get("review_results"):
        steps.append("reviews")
    if state.get("comparison_results"):
        steps.append("comparison")
    if state.get("recommendation_result"):
        steps.append("recommendations")
    return steps


# ─── Static File Serving ────────────────────────────────────────────────────

FRONTEND_DIR = BASE_DIR / "frontend"

@app.get("/")
def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/pages/{page_name}")
def serve_page(page_name: str):
    page_path = FRONTEND_DIR / "pages" / page_name
    if page_path.exists():
        return FileResponse(str(page_path))
    raise HTTPException(status_code=404, detail="Page not found")

# Mount static assets (css, js)
if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
