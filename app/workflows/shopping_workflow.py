import os
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, START, END

from app.agents.requirement_agent import RequirementAgent, ShoppingRequirements
from app.agents.product_search_agent import ProductSearchAgent, SearchResult
from app.agents.review_agent import ReviewAnalysisAgent, ReviewAnalysis
from app.agents.price_specs_agent import PriceSpecsAgent, ComparisonResult
from app.agents.recommendation_agent import RecommendationAgent, RecommendationResult
from app.database.database import load_products

class ShoppingState(TypedDict):
    user_request: str
    requirements: Optional[ShoppingRequirements]
    search_results: List[SearchResult]
    review_results: Dict[str, ReviewAnalysis]
    comparison_results: Optional[ComparisonResult]
    recommendation_result: Optional[RecommendationResult]
    error: Optional[str]
    current_step: str

def requirement_node(state: ShoppingState) -> ShoppingState:
    try:
        agent = RequirementAgent()
        reqs = agent.extract_requirements(state["user_request"])
        return {"requirements": reqs, "current_step": "requirements"}
    except Exception as e:
        return {"error": f"Requirement extraction failed: {str(e)}", "current_step": "requirements"}

def product_search_node(state: ShoppingState) -> ShoppingState:
    if state.get("error"):
        return state
    try:
        agent = ProductSearchAgent()
        # Using relaxed_budget=True as designed in Phase 8
        results = agent.search(state["requirements"], relaxed_budget=True)
        return {"search_results": results, "current_step": "product_search"}
    except Exception as e:
        return {"error": f"Product search failed: {str(e)}", "current_step": "product_search"}

def review_analysis_node(state: ShoppingState) -> ShoppingState:
    if state.get("error"):
        return state
    try:
        agent = ReviewAnalysisAgent()
        reviews_data = {}
        # Avoid reloading all products, just get product IDs from search results
        for res in state["search_results"]:
            analysis = agent.analyze(res.product_id)
            if analysis:
                reviews_data[res.product_id] = analysis
        return {"review_results": reviews_data, "current_step": "review_analysis"}
    except Exception as e:
        return {"error": f"Review analysis failed: {str(e)}", "current_step": "review_analysis"}

def price_specs_node(state: ShoppingState) -> ShoppingState:
    if state.get("error"):
        return state
    try:
        agent = PriceSpecsAgent()
        # Get actual products from DB for the search results
        search_ids = {r.product_id for r in state["search_results"]}
        products = [p for p in load_products() if p.product_id in search_ids]
        
        comp_res = agent.compare(state["requirements"], products)
        return {"comparison_results": comp_res, "current_step": "price_specs"}
    except Exception as e:
        return {"error": f"Price and specification comparison failed: {str(e)}", "current_step": "price_specs"}

def recommendation_node(state: ShoppingState) -> ShoppingState:
    if state.get("error"):
        return state
    try:
        agent = RecommendationAgent()
        rec_res = agent.recommend(
            state["requirements"],
            state["comparison_results"],
            state["review_results"]
        )
        return {"recommendation_result": rec_res, "current_step": "recommendation"}
    except Exception as e:
        return {"error": f"Recommendation generation failed: {str(e)}", "current_step": "recommendation"}

def build_workflow() -> StateGraph:
    workflow = StateGraph(ShoppingState)
    
    workflow.add_node("requirement_node", requirement_node)
    workflow.add_node("product_search_node", product_search_node)
    workflow.add_node("review_analysis_node", review_analysis_node)
    workflow.add_node("price_specs_node", price_specs_node)
    workflow.add_node("recommendation_node", recommendation_node)
    
    workflow.add_edge(START, "requirement_node")
    workflow.add_edge("requirement_node", "product_search_node")
    workflow.add_edge("product_search_node", "review_analysis_node")
    workflow.add_edge("review_analysis_node", "price_specs_node")
    workflow.add_edge("price_specs_node", "recommendation_node")
    workflow.add_edge("recommendation_node", END)
    
    return workflow.compile()

def run_shopping_workflow(user_request: str) -> ShoppingState:
    initial_state = ShoppingState(
        user_request=user_request,
        requirements=None,
        search_results=[],
        review_results={},
        comparison_results=None,
        recommendation_result=None,
        error=None,
        current_step="start"
    )
    
    app = build_workflow()
    final_state = app.invoke(initial_state)
    return final_state
