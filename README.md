# 🛒 Multi-Agent E-Commerce Shopping Assistant

A robust, production-ready AI-powered shopping assistant built with **LangGraph**, **Google Gemini**, **FastAPI**, and an interactive **HTML/CSS/JavaScript** frontend (along with a Streamlit interface). Multiple specialized AI agents collaborate sequentially to extract customer requirements, search product catalogs, analyze sentiment from customer reviews, perform price and specification comparisons, and deliver explainable, ranked recommendations.

---

## 🏗️ Multi-Agent Architecture

The assistant executes a deterministic 5-stage sequential workflow orchestrated via **LangGraph**:

```
Customer Request
       │
       ▼
1. [ Requirement Agent ] ──► Extracts category, budget (INR), use-case & specs
       │
       ▼
2. [ Product Search Agent ] ──► Filters catalog & retrieves in-budget & relaxed candidates
       │
       ▼
3. [ Review Analysis Agent ] ──► Evaluates ratings, sentiment & common strengths/complaints
       │
       ▼
4. [ Price & Specs Agent ] ──► Deterministic comparison, spec extraction & constraint scoring
       │
       ▼
5. [ Recommendation Agent ] ──► Selects Best Overall, Best Value, and Alternatives
       │
       ▼
Final Explainable Recommendations
```

### Specialized Agents:
1. **Requirement Agent (`app/agents/requirement_agent.py`)**: Parses unstructured customer prompts into a typed `ShoppingRequirements` model.
2. **Product Search Agent (`app/agents/product_search_agent.py`)**: Queries product catalog (`data/products.json`), matching categories, features, and budget constraints.
3. **Review Analysis Agent (`app/agents/review_agent.py`)**: Aggregates customer feedback (`data/reviews.json`), computing sentiment, review counts, and key themes.
4. **Price & Specification Agent (`app/agents/price_specs_agent.py`)**: Performs price-to-budget evaluation, constraint verification, and specification scoring out of 100.
5. **Recommendation Agent (`app/agents/recommendation_agent.py`)**: Combines spec scores with review sentiment, enforces over-budget penalties, and outputs ranked recommendations (Best Overall, Best Value, Alternatives).
6. **LangGraph Workflow (`app/workflows/shopping_workflow.py`)**: Orchestrates the state graph across all 5 nodes with error handling and fallback capabilities.

---

## 💻 Technologies Used

- **Language**: Python 3.11 / 3.12
- **Orchestration**: LangGraph, LangChain Core
- **LLM**: Google Gemini (`google-genai` SDK)
- **Backend API**: FastAPI, Uvicorn, Pydantic
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Streamlit
- **Data Storage**: JSON catalog (`data/products.json`, `data/reviews.json`)
- **Testing & Quality**: pytest, unit & integration test suite
- **Containerization**: Docker

---

## 📁 Project Structure

```
MultiAgent_Ecommerce_Assistant/
├── app/
│   ├── agents/                 # 5 Specialized AI Agents
│   │   ├── requirement_agent.py
│   │   ├── product_search_agent.py
│   │   ├── review_agent.py
│   │   ├── price_specs_agent.py
│   │   └── recommendation_agent.py
│   ├── api/                    # FastAPI Endpoints & Static Server
│   │   └── api_server.py
│   ├── core/                   # Configuration & LLM Initialization
│   │   ├── config.py
│   │   └── llm.py
│   ├── database/               # Data Access & Dataclass Models
│   │   ├── database.py
│   │   └── models.py
│   ├── ui/                     # Streamlit UI Interface
│   │   └── streamlit_app.py
│   └── workflows/              # LangGraph Orchestration StateGraph
│       └── shopping_workflow.py
├── data/                       # Product Catalog & Reviews JSON
│   ├── products.json
│   └── reviews.json
├── frontend/                   # Web Application (HTML / CSS / JS)
│   ├── css/
│   ├── js/
│   ├── pages/
│   └── index.html
├── tests/                      # Automated Unit & Integration Tests
│   ├── test_agent.py
│   ├── test_basic.py
│   ├── test_consolidated_fixes.py
│   ├── test_price_specs_agent.py
│   ├── test_production_readiness.py
│   ├── test_recommendation_agent.py
│   ├── test_review_agent.py
│   ├── test_search_agent.py
│   └── test_shopping_workflow.py
├── .env.example                # Environment Variable Template
├── .gitignore                  # Git Ignore Definitions
├── Dockerfile                  # Container Production Build
├── README.md                   # Project Documentation
├── requirements.txt            # Python Dependencies
├── run.py                      # Streamlit App Runner
└── run_api.py                  # FastAPI & HTML/CSS/JS Server Runner
```

---

## 📋 Prerequisites & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/multiagent-ecommerce-assistant.git
cd multiagent-ecommerce-assistant
```

### 2. Create & Activate Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

---

## ⚙️ Environment Variables & Configuration

Configured through environment variables managed in `app/core/config.py`:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | String | `development` | Environment mode (`development` / `production`). |
| `LOG_LEVEL` | String | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `LLM_MODE` | String | `MOCK` | Global mode: `MOCK` for offline zero-cost dev, or `GEMINI` for live LLM. |
| `MODEL_NAME` | String | `gemini-2.5-flash` | Gemini model name used for live inference. |
| `GEMINI_API_KEY` | String | *None* | Google GenAI API Key (Required when `LLM_MODE=GEMINI`). |
| `SERVER_PORT` | Integer | `8501` | Port for web server. |
| `SERVER_HOST` | String | `0.0.0.0` | Host address for web server. |

### Mock Overrides per Agent (Optional):
- `REQUIREMENT_AGENT_MOCK_MODE=true`
- `PRODUCT_SEARCH_AGENT_MOCK_MODE=true`
- `REVIEW_AGENT_MOCK_MODE=true`
- `PRICE_SPECS_AGENT_MOCK_MODE=true`
- `RECOMMENDATION_AGENT_MOCK_MODE=true`

---

## 🔄 Execution Modes

### 🟢 MOCK Mode (Offline / Zero-Cost)
- 100% deterministic local evaluation.
- No external network calls or Gemini API keys required.
- Ideal for automated testing, CI/CD pipelines, and offline development.
- Activated by setting `LLM_MODE=MOCK` or omitting `GEMINI_API_KEY`.

### 🔵 GEMINI Mode (Live AI Inference)
- Connects to Google Gemini (`google-genai` SDK) using API key authentication.
- Evaluates natural language user requirements and generates explainable recommendations.
- Numerical rankings, filtering, and constraint math are computed deterministically in Python to prevent LLM hallucinations.
- Activated by setting `LLM_MODE=GEMINI` and adding `GEMINI_API_KEY=your_key` in `.env`.

---

## 🚀 Running the Application

### Running the HTML / CSS / JS Web Application & Backend API
Launch the FastAPI server which serves both the REST API endpoints and the static HTML/CSS/JS frontend:
```bash
python run_api.py
```
- **Web App UI:** [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Docs:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

### Running the Streamlit Interface
Alternatively, launch the Streamlit interface:
```bash
python run.py
# or
streamlit run app/ui/streamlit_app.py
```
- Access at: [http://localhost:8501](http://localhost:8501)

---

## 🧪 Running Automated Tests

Run the complete test suite (95 unit and integration tests):
```bash
python -m pytest
```

Run with verbose output:
```bash
python -m pytest -v
```

---

## 🐳 Docker Production Deployment

```bash
# 1. Build Image
docker build -t ecommerce-assistant:latest .

# 2. Run Container (MOCK Mode)
docker run -d -p 8000:8000 --name ecommerce-app ecommerce-assistant:latest

# 3. Run Container (GEMINI Live Mode)
docker run -d -p 8000:8000 \
  -e LLM_MODE=GEMINI \
  -e GEMINI_API_KEY="your_api_key_here" \
  --name ecommerce-app ecommerce-assistant:latest
```

---

## 📄 License
This project is licensed under the MIT License.
