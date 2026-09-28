import streamlit as st
import sys
import os

# Add project root to sys.path to allow imports when running via streamlit run
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database.database import load_products, get_reviews_for_product
from dotenv import load_dotenv

load_dotenv()

# Constants
USD_TO_INR_RATE = 83.0

def convert_to_inr(price_usd: float) -> float:
    return price_usd * USD_TO_INR_RATE

def format_inr(amount: float) -> str:
    return f"₹{amount:,.0f}"

from app.core.config import config, logger

def render_sidebar():
    st.sidebar.title("Multi-Agent E-Commerce")
    st.sidebar.markdown("### How it works")
    st.sidebar.markdown("""
    1. Understand your requirements
    2. Search relevant products
    3. Analyze reviews
    4. Compare price and specifications
    5. Recommend the best options
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ System Status")
    mode_badge = "🟢 MOCK (Offline)" if config.LLM_MODE == "MOCK" or not config.GEMINI_API_KEY else "🔵 GEMINI (Live)"
    st.sidebar.caption(f"**Mode:** {mode_badge}")
    st.sidebar.caption(f"**Environment:** {config.APP_ENV.title()}")
    st.sidebar.caption(f"**Model:** {config.MODEL_NAME}")
    
    # Startup validation check
    validation = config.validate_startup()
    if validation["status"] == "HEALTHY":
        st.sidebar.success("System: Healthy & Ready")
    else:
        st.sidebar.warning(f"System: {validation['status']}")
        for err in validation.get("errors", []):
            st.sidebar.error(err)

def render_main():
    st.title("🛒 Multi-Agent E-Commerce Shopping Assistant")
    st.markdown("##### *Find the right product with intelligent search, comparison, review analysis, and personalized recommendations.*")
    
    # Customer Request Section
    st.markdown("### What are you looking for?")
    request_text = st.text_area(
        label="Description",
        placeholder="I need a laptop under ₹70,000 for programming with 16GB RAM and good battery life.",
        label_visibility="collapsed"
    )
    st.caption("Example: I need a laptop under ₹70,000 for programming with 16GB RAM and good battery life.")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox(
            "Category",
            options=["All Categories", "Laptops", "Smartphones", "Headphones", "Smartwatches"]
        )
    with col2:
        budget = st.number_input(
            "Maximum Budget (₹)",
            min_value=0,
            value=100000,
            step=1000
        )
    
    # Search Button
    if st.button("🔍 Find Products", type="primary"):
        st.session_state["has_searched"] = True
        st.session_state["search_params"] = {
            "category": category,
            "budget": budget,
            "request_text": request_text
        }
    
    # Initial State or Results
    if not st.session_state.get("has_searched", False):
        st.info("Describe what you need, choose optional filters, and our AI shopping team will eventually analyze products, reviews, prices, and specifications to find the best match.")
    else:
        st.markdown("---")
        display_results(
            category=st.session_state["search_params"]["category"],
            budget=st.session_state["search_params"]["budget"]
        )

    # Phase 4 - Requirement Agent Test (Development)
    st.markdown("---")
    
    mock_mode = os.getenv("REQUIREMENT_AGENT_MOCK_MODE", "false").lower() == "true"
    mode_text = "MOCK" if mock_mode else "GEMINI"
    
    with st.expander("🛠️ Development Tool: Requirement Agent Test (Phase 4)", expanded=True):
        st.write("Test the Requirement Agent extraction logic.")
        st.caption(f"**Requirement Agent Mode: {mode_text}**")
        
        test_request = st.text_area("Customer Request to Analyze:", key="req_agent_test")
        if st.button("Analyze Requirements"):
            from app.agents.requirement_agent import RequirementAgent
            from app.core.llm import llm_service
            
            if not mock_mode and not llm_service.is_configured():
                st.error("LLM configuration is missing or invalid. Please configure the required API key in .env.")
            else:
                try:
                    agent = RequirementAgent()
                    reqs = agent.extract_requirements(test_request)
                    st.success("Analysis Complete")
                    
                    st.markdown(f"**Category:** {reqs.category}")
                    st.markdown(f"**Product Type:** {reqs.product_type}")
                    st.markdown(f"**Budget:** {reqs.budget}")
                    st.markdown(f"**Currency:** {reqs.currency}")
                    st.markdown(f"**Purpose:** {', '.join(reqs.purpose) if reqs.purpose else 'None'}")
                    
                    st.markdown("**Required Specifications:**")
                    combined_reqs = []
                    if reqs.important_specifications: combined_reqs.extend(reqs.important_specifications)
                    if reqs.required_features: combined_reqs.extend(reqs.required_features)
                    if combined_reqs:
                        for spec in combined_reqs:
                            st.markdown(f"- {spec}")
                    else:
                        st.markdown("- None")
                        
                    st.markdown("**Preferred Features:**")
                    combined_prefs = []
                    if reqs.preferred_features: combined_prefs.extend(reqs.preferred_features)
                    if reqs.preferred_brands: combined_prefs.extend(reqs.preferred_brands)
                    if combined_prefs:
                        for feat in combined_prefs:
                            st.markdown(f"- {feat}")
                    else:
                        st.markdown("- None")
                        
                except Exception as e:
                    error_msg = str(e)
                    if "LLM is not configured" in error_msg:
                        st.error("LLM configuration is missing or invalid. Please configure the required API key in .env.")
                    elif "429" in error_msg or "quota" in error_msg.lower():
                        st.error("Gemini API quota has been exceeded. Enable mock mode for local testing or try again after the quota resets.")
                    else:
                        st.error(f"Error during analysis: {e}")

    # Phase 5 - Product Search Agent Test (Development)
    st.markdown("---")
    with st.expander("🛠️ Development Tool: Product Search Agent Test (Phase 5)", expanded=False):
        st.write("Test the Product Search Agent matching logic.")
        st.caption(f"**Search Agent Mode: {mode_text}**")
        
        search_request = st.text_area("Customer Request to Search For:", key="search_agent_test")
        
        # Clear results if input is empty or has changed
        if "phase5_last_request" not in st.session_state or st.session_state["phase5_last_request"] != search_request:
            st.session_state["phase5_results"] = None
            st.session_state["phase5_last_request"] = search_request
            
        if st.button("Search Products"):
            if not search_request or not search_request.strip():
                st.session_state["phase5_results"] = "empty"
            else:
                from app.agents.requirement_agent import RequirementAgent
                from app.agents.product_search_agent import ProductSearchAgent
                from app.core.llm import llm_service
                
                if not mock_mode and not llm_service.is_configured():
                    st.error("LLM configuration is missing or invalid. Please configure the required API key in .env.")
                else:
                    try:
                        req_agent = RequirementAgent()
                        reqs = req_agent.extract_requirements(search_request)
                        
                        search_agent = ProductSearchAgent()
                        results = search_agent.search(reqs)
                        
                        st.session_state["phase5_results"] = results
                            
                    except Exception as e:
                        error_msg = str(e)
                        if "LLM is not configured" in error_msg:
                            st.error("LLM configuration is missing or invalid. Please configure the required API key in .env.")
                        elif "429" in error_msg or "quota" in error_msg.lower():
                            st.error("Gemini API quota has been exceeded. Enable mock mode for local testing or try again after the quota resets.")
                        else:
                            st.error(f"Error during search: {e}")

        # Display results from state
        if st.session_state.get("phase5_results") == "empty" or not search_request.strip():
            st.info("Enter a request to search for products.")
        elif st.session_state.get("phase5_results") is not None:
            results = st.session_state["phase5_results"]
            if len(results) == 0:
                st.warning("0 strict matches: No products in the database satisfy all your required criteria (e.g., budget).")
            else:
                st.success(f"Search Complete: Found {len(results)} matches.")
                for res in results:
                    st.markdown(f"**Product ID:** {res.product_id} | **Score:** {res.match_score}/10")
                    st.markdown(f"**Reason:** {res.reason}")
                    st.markdown("---")


    # Phase 6 - Review Analysis Agent Test (Development)
    st.markdown("---")
    
    review_mock_mode = os.getenv("REVIEW_AGENT_MOCK_MODE", "false").lower() == "true"
    review_mode_text = "MOCK" if review_mock_mode else "GEMINI"
    
    with st.expander("🛠️ Development Tool: Review Analysis Agent Test (Phase 6)", expanded=False):
        st.write("Test the Review Analysis Agent logic.")
        st.caption(f"**Review Agent Mode: {review_mode_text}**")
        
        products = load_products()
        product_options = {"None": None}
        for p in products:
            product_options[f"{p.name} ({p.product_id})"] = p.product_id
            
        selected_label = st.selectbox("Product to Analyze:", options=list(product_options.keys()), key="review_agent_test")
        
        if "phase6_last_request" not in st.session_state or st.session_state["phase6_last_request"] != selected_label:
            st.session_state["phase6_results"] = None
            st.session_state["phase6_last_request"] = selected_label
            
        if st.button("Analyze Reviews"):
            if selected_label == "None":
                st.session_state["phase6_results"] = "empty"
            else:
                from app.agents.review_agent import ReviewAnalysisAgent
                from app.core.llm import llm_service
                
                if not review_mock_mode and not llm_service.is_configured():
                    st.error("LLM configuration is missing or invalid. Please configure the required API key in .env.")
                else:
                    try:
                        review_agent = ReviewAnalysisAgent()
                        analysis = review_agent.analyze(product_options[selected_label])
                        st.session_state["phase6_results"] = analysis
                    except Exception as e:
                        st.error(f"Error during analysis: {e}")

        # Display results
        if st.session_state.get("phase6_results") == "empty" or selected_label == "None":
            st.info("Select a product to analyze its reviews.")
        elif st.session_state.get("phase6_results") is not None:
            analysis = st.session_state["phase6_results"]
            st.success("Review Analysis Complete")
            st.markdown(f"**Product:** {analysis.product_name}")
            st.markdown(f"**Review Count:** {analysis.review_count}")
            st.markdown(f"**Average Rating:** {analysis.average_rating} / 5")
            st.markdown(f"**Overall Sentiment:** {analysis.overall_sentiment}")
            
            st.markdown("**Positive Themes:**")
            if analysis.positive_themes:
                for pt in analysis.positive_themes: st.markdown(f"• {pt}")
            else:
                st.markdown("• None")
                
            st.markdown("**Negative Themes:**")
            if analysis.negative_themes:
                for nt in analysis.negative_themes: st.markdown(f"• {nt}")
            else:
                st.markdown("• None")
                
            st.markdown("**Common Strengths:**")
            if analysis.common_strengths:
                for cs in analysis.common_strengths: st.markdown(f"• {cs}")
            else:
                st.markdown("• None")
                
            st.markdown("**Common Complaints:**")
            if analysis.common_complaints:
                for cc in analysis.common_complaints: st.markdown(f"• {cc}")
            else:
                st.markdown("• None")
                
            st.markdown(f"**Summary:**\n{analysis.summary}")


    # Phase 7 - Price & Specification Agent Test (Development)
    st.markdown("---")
    
    price_mock_mode = os.getenv("PRICE_SPECS_AGENT_MOCK_MODE", "false").lower() == "true"
    price_mode_text = "MOCK" if price_mock_mode else "GEMINI"
    
    with st.expander("🛠️ Development Tool: Price & Specification Agent Test (Phase 7)", expanded=False):
        st.write("Test the Price & Specification comparison logic.")
        st.caption(f"**Price Specs Agent Mode: {price_mode_text}**")
        
        products = load_products()
        product_options = {f"{p.name} ({p.product_id})": p for p in products}
        
        selected_labels = st.multiselect("Products to Compare:", options=list(product_options.keys()), key="price_agent_products")
        price_request = st.text_area("Customer Request:", key="price_agent_request")
        
        state_key = str(selected_labels) + price_request
        if "phase7_last_state" not in st.session_state or st.session_state["phase7_last_state"] != state_key:
            st.session_state["phase7_results"] = None
            st.session_state["phase7_last_state"] = state_key
            
        if st.button("Compare Products"):
            if not selected_labels:
                st.session_state["phase7_results"] = "empty"
            else:
                from app.agents.requirement_agent import RequirementAgent
                from app.agents.price_specs_agent import PriceSpecsAgent
                from app.core.llm import llm_service
                
                if not price_mock_mode and not llm_service.is_configured():
                    st.error("LLM configuration is missing or invalid. Please configure the required API key in .env.")
                else:
                    try:
                        req_agent = RequirementAgent()
                        reqs = req_agent.extract_requirements(price_request)
                        
                        selected_products = [product_options[lbl] for lbl in selected_labels]
                        
                        agent = PriceSpecsAgent()
                        res = agent.compare(reqs, selected_products)
                        st.session_state["phase7_results"] = res
                    except Exception as e:
                        st.error(f"Error during comparison: {e}")

        if st.session_state.get("phase7_results") == "empty" or not selected_labels:
            st.info("Select at least one product to compare.")
        elif st.session_state.get("phase7_results") is not None:
            res = st.session_state["phase7_results"]
            st.success("Comparison Complete")
            
            st.markdown("### PRICE & SPECIFICATION COMPARISON")
            
            import pandas as pd
            table_data = []
            for c in res.products:
                row = {
                    "Product": c.product_name,
                    "Price": f"\u20b9{c.price:,.0f}",
                    "Budget": "✓" if c.within_budget else "Over Budget"
                }
                for k, v in c.specification_comparison.items():
                    row[k.replace('_', ' ').title()] = v
                table_data.append(row)
                
            df = pd.DataFrame(table_data).fillna("-")
            st.table(df)
            
            st.markdown("### Ranking:")
            for i, c in enumerate(res.products):
                st.markdown(f"**{i+1}. {c.product_name}** — {c.score}/100")
                st.markdown(f"*Required Match: {c.required_matches}/{c.required_total} | Preferred Match: {c.preferred_matches}/{c.preferred_total}*")
                
            st.markdown(f"**Summary:** {res.summary}")


    # Phase 8 - Recommendation Agent Test (Development)
    st.markdown("---")
    
    rec_mock_mode = os.getenv("RECOMMENDATION_AGENT_MOCK_MODE", "false").lower() == "true"
    rec_mode_text = "MOCK" if rec_mock_mode else "GEMINI"
    
    with st.expander("🛠️ Development Tool: Recommendation Agent Test (Phase 8)", expanded=False):
        st.write("Test the end-to-end Recommendation Agent logic.")
        st.caption(f"**Recommendation Agent Mode: {rec_mode_text}**")
        
        rec_request = st.text_area("Customer Request:", key="rec_agent_request", placeholder="I want a smartphone under ₹100,000 with good battery life.")
        
        if "phase8_last_request" not in st.session_state or st.session_state["phase8_last_request"] != rec_request:
            st.session_state["phase8_results"] = None
            st.session_state["phase8_last_request"] = rec_request
            
        if st.button("Generate Recommendations"):
            if not rec_request or not rec_request.strip():
                st.session_state["phase8_results"] = "empty"
            else:
                from app.agents.requirement_agent import RequirementAgent
                from app.agents.product_search_agent import ProductSearchAgent
                from app.agents.review_agent import ReviewAnalysisAgent
                from app.agents.price_specs_agent import PriceSpecsAgent
                from app.agents.recommendation_agent import RecommendationAgent
                from app.core.llm import llm_service
                
                if not rec_mock_mode and not llm_service.is_configured():
                    st.error("LLM configuration is missing or invalid. Please configure the required API key in .env.")
                else:
                    try:
                        req_agent = RequirementAgent()
                        reqs = req_agent.extract_requirements(rec_request)
                        
                        search_agent = ProductSearchAgent()
                        search_res = search_agent.search(reqs, relaxed_budget=True)
                        
                        if not search_res:
                            st.session_state["phase8_results"] = "no_match"
                        else:
                            products = [p for p in load_products() if p.product_id in {r.product_id for r in search_res}]
                            
                            review_agent = ReviewAnalysisAgent()
                            reviews_data = {}
                            for p in products:
                                analysis = review_agent.analyze(p.product_id)
                                if analysis:
                                    reviews_data[p.product_id] = analysis
                                    
                            price_agent = PriceSpecsAgent()
                            price_res = price_agent.compare(reqs, products)
                            
                            rec_agent = RecommendationAgent()
                            rec_res = rec_agent.recommend(reqs, price_res, reviews_data)
                            
                            st.session_state["phase8_results"] = rec_res
                    except Exception as e:
                        st.error(f"Error during recommendation generation: {e}")

        if st.session_state.get("phase8_results") == "empty" or not rec_request.strip():
            st.info("Search for products before generating recommendations.")
        elif st.session_state.get("phase8_results") == "no_match":
            st.warning("No products satisfy the required criteria.")
        elif st.session_state.get("phase8_results") is not None:
            res = st.session_state["phase8_results"]
            
            st.markdown("### RECOMMENDATION RESULTS")
            st.markdown(f"*{res.decision_summary}*")
            st.markdown("---")
            
            def render_rec(rec, title):
                st.markdown(f"#### {title}")
                st.markdown(f"**{rec.product_name}**")
                st.markdown(f"*{rec.price_summary}*")
                st.markdown(f"**Overall Score:** {rec.overall_score}/100")
                
                st.markdown("**Why this product:**")
                for r in rec.why_recommended:
                    st.markdown(f"• {r}")
                    
                st.markdown("**Strengths:**")
                for s in rec.strengths:
                    st.markdown(f"• {s}")
                    
                st.markdown("**Potential Concerns:**")
                if rec.weaknesses:
                    for w in rec.weaknesses:
                        st.markdown(f"• {w}")
                else:
                    st.markdown("• None identified")
                    
                st.markdown(f"**Reviews:** {rec.review_summary}")
                st.markdown(f"**Requirements:** {rec.requirement_match_summary}")
                st.markdown("---")
                
            if res.best_overall:
                render_rec(res.best_overall, "🏆 Best Overall")
                
            if res.best_value:
                render_rec(res.best_value, "💰 Best Value")
                
            if res.alternatives:
                if not res.has_valid_matches:
                    st.markdown("#### 🔄 Closest Alternatives — Over Budget")
                else:
                    st.markdown("#### 🔄 Alternatives")
                    
                for i, alt in enumerate(res.alternatives):
                    render_rec(alt, f"Alternative {i+1} — {alt.recommendation_type}" if "Over Budget" in alt.recommendation_type else f"Alternative {i+1}")


    # Phase 9 - Multi-Agent Shopping Workflow (Production)
    st.markdown("---")
    
    with st.expander("🛒 Multi-Agent Shopping Workflow (Phase 9)", expanded=True):
        st.write("Execute the complete end-to-end shopping assistant workflow.")
        
        wf_request = st.text_area("Customer Request:", key="wf_request", placeholder="I want a smartphone under ₹100,000 with good battery life.")
        
        if st.button("Run Shopping Assistant", key="run_wf_btn"):
            if not wf_request or not wf_request.strip():
                st.info("Please enter a shopping request.")
            else:
                from app.workflows.shopping_workflow import run_shopping_workflow
                from app.core.llm import llm_service
                
                # Verify environment
                mock_modes = [
                    os.getenv("REQUIREMENT_AGENT_MOCK_MODE", "false").lower() == "true",
                    os.getenv("PRODUCT_SEARCH_AGENT_MOCK_MODE", "false").lower() == "true",
                    os.getenv("REVIEW_AGENT_MOCK_MODE", "false").lower() == "true",
                    os.getenv("PRICE_SPECS_AGENT_MOCK_MODE", "false").lower() == "true",
                    os.getenv("RECOMMENDATION_AGENT_MOCK_MODE", "false").lower() == "true"
                ]
                
                if not all(mock_modes) and not llm_service.is_configured():
                    st.error("LLM configuration is missing or invalid. Please configure the required API key in .env.")
                else:
                    status_placeholder = st.empty()
                    status_placeholder.info("🔄 Running multi-agent shopping workflow...")
                    
                    try:
                        final_state = run_shopping_workflow(wf_request)
                        
                        if final_state.get("error"):
                            status_placeholder.error("❌ Multi-agent workflow failed.")
                            st.error(final_state["error"])
                            st.write(f"Failed at step: {final_state.get('current_step')}")
                        else:
                            status_placeholder.success("✅ Multi-agent workflow completed successfully.")
                            
                            st.markdown("### PROGRESS")
                            st.markdown("✓ Requirements analyzed")
                            st.markdown("✓ Products searched")
                            st.markdown("✓ Reviews analyzed")
                            st.markdown("✓ Prices & specifications compared")
                            st.markdown("✓ Recommendations generated")
                            
                            st.markdown("---")
                            st.markdown("### FINAL SHOPPING RECOMMENDATION")
                            
                            rec_res = final_state.get("recommendation_result")
                            if not rec_res:
                                st.warning("No recommendations generated.")
                            else:
                                st.markdown(f"*{rec_res.decision_summary}*")
                                st.markdown("---")
                                
                                def render_wf_rec(rec, title):
                                    st.markdown(f"#### {title}")
                                    st.markdown(f"**Product:** {rec.product_name}")
                                    st.markdown(f"**Price:** {rec.price_summary}")
                                    if "Over Budget" not in rec.recommendation_type and "Does not meet" not in rec.recommendation_type:
                                        st.markdown(f"**Score:** {rec.overall_score}/100")
                                    
                                    st.markdown("**Why:**")
                                    for r in rec.why_recommended:
                                        st.markdown(f"• {r}")
                                    st.markdown("---")
                                    
                                if rec_res.best_overall:
                                    render_wf_rec(rec_res.best_overall, "🏆 Best Overall")
                                    
                                if rec_res.best_value:
                                    render_wf_rec(rec_res.best_value, "💰 Best Value")
                                    
                                if rec_res.alternatives:
                                    if not rec_res.has_valid_matches:
                                        st.markdown("#### 🔄 Closest Alternatives — Over Budget")
                                    else:
                                        st.markdown("#### 🔄 Alternatives")
                                        
                                    for i, alt in enumerate(rec_res.alternatives):
                                        render_wf_rec(alt, f"Alternative {i+1} — {alt.recommendation_type}" if "Over Budget" in alt.recommendation_type else f"Alternative {i+1}")

                    except Exception as e:
                        status_placeholder.error("❌ Multi-agent workflow failed.")
                        st.error(f"Unexpected error: {e}")

def display_results(category: str, budget: float):
    products = load_products()
    
    # Filter by category
    if category != "All Categories":
        products = [p for p in products if p.category.lower() == category.lower()]
        
    # Filter by budget
    filtered_products = []
    for p in products:
        price_inr = convert_to_inr(p.price)
        if price_inr <= budget:
            filtered_products.append(p)
            
    if not filtered_products:
        st.warning("No products found matching your current filters. Try increasing your budget or selecting another category.")
        return
        
    st.success(f"Found {len(filtered_products)} products matching your criteria.")
    
    for p in filtered_products:
        price_inr = convert_to_inr(p.price)
        with st.container(border=True):
            st.markdown(f"### {p.name}")
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Brand**: {p.brand} | **Category**: {p.category}")
                st.markdown(f"**Rating**: ⭐ {p.rating} ({p.review_count} reviews)")
                st.markdown(f"{p.description}")
            with col2:
                st.markdown(f"### {format_inr(price_inr)}")
                
            # Product Details Expander
            with st.expander("View Details"):
                st.markdown("#### Specifications")
                for key, value in p.specifications.items():
                    # Format key to title case
                    formatted_key = key.replace('_', ' ').title()
                    st.markdown(f"- **{formatted_key}**: {value}")
                    
            # Review Preview Expander
            with st.expander("View Reviews"):
                reviews = get_reviews_for_product(p.product_id)
                if not reviews:
                    st.info("No reviews available for this product yet.")
                else:
                    # Display up to 3 reviews
                    for review in reviews[:3]:
                        st.markdown(f"⭐ **{review.rating}/5**")
                        st.markdown(f"> {review.review_text}")
                        st.markdown("---")

def run_ui():
    st.set_page_config(page_title="Multi-Agent E-Commerce", page_icon="🛒", layout="wide")
    render_sidebar()
    render_main()

if __name__ == "__main__":
    run_ui()
