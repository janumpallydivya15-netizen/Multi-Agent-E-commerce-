import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

class Config:
    """
    Centralized configuration management for Multi-Agent E-Commerce Assistant.
    Provides production-safe defaults and dynamic environment variable resolution.
    """
    
    # Base Directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    PRODUCTS_FILE: Path = DATA_DIR / "products.json"
    REVIEWS_FILE: Path = DATA_DIR / "reviews.json"
    
    # Application Environment
    APP_ENV: str = os.getenv("APP_ENV", "development").lower()
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Model and LLM Configuration
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    LLM_MODE: str = os.getenv("LLM_MODE", "MOCK" if not os.getenv("GEMINI_API_KEY") else "GEMINI").upper()
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-2.5-flash")
    
    # Server configuration
    SERVER_PORT: int = int(os.getenv("PORT", os.getenv("SERVER_PORT", "8501")))
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")

    @classmethod
    def is_production(cls) -> bool:
        return cls.APP_ENV == "production"

    @classmethod
    def is_agent_mock_mode(cls, agent_prefix: str) -> bool:
        """
        Check if a specific agent is in mock mode.
        Checks specific env var (e.g., REQUIREMENT_AGENT_MOCK_MODE),
        falling back to global LLM_MODE or missing API key if unset.
        """
        env_var = f"{agent_prefix.upper()}_MOCK_MODE"
        val = os.getenv(env_var)
        if val is not None and val.strip() != "":
            return val.strip().lower() == "true"
            
        llm_mode = os.getenv("LLM_MODE", cls.LLM_MODE).upper()
        api_key = os.getenv("GEMINI_API_KEY", cls.GEMINI_API_KEY)
        return llm_mode == "MOCK" or not bool(api_key)

    @classmethod
    def configure_logging(cls) -> logging.Logger:
        """
        Configures and returns the central logger for the application.
        Ensures no secrets are logged.
        """
        level = getattr(logging, cls.LOG_LEVEL, logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        logger = logging.getLogger("MultiAgentAssistant")
        logger.setLevel(level)
        return logger

    @classmethod
    def validate_startup(cls) -> Dict[str, Any]:
        """
        Lightweight production startup validation.
        Validates data files, dependencies, and environment credentials.
        Returns a dictionary with validation status and diagnostics.
        """
        diagnostics = {
            "app_env": cls.APP_ENV,
            "llm_mode": cls.LLM_MODE,
            "model_name": cls.MODEL_NAME,
            "products_file_exists": cls.PRODUCTS_FILE.exists(),
            "reviews_file_exists": cls.REVIEWS_FILE.exists(),
            "gemini_api_key_configured": bool(cls.GEMINI_API_KEY),
            "errors": [],
            "warnings": []
        }
        
        # 1. Validate data files
        if not cls.PRODUCTS_FILE.exists():
            diagnostics["errors"].append(f"Missing required data file: {cls.PRODUCTS_FILE}")
        else:
            try:
                with open(cls.PRODUCTS_FILE, "r", encoding="utf-8") as f:
                    products = json.load(f)
                    if not isinstance(products, list) or len(products) == 0:
                        diagnostics["errors"].append("products.json is empty or invalid format")
                    diagnostics["product_count"] = len(products) if isinstance(products, list) else 0
            except Exception as e:
                diagnostics["errors"].append(f"Failed to parse products.json: {e}")

        if not cls.REVIEWS_FILE.exists():
            diagnostics["errors"].append(f"Missing required data file: {cls.REVIEWS_FILE}")
        else:
            try:
                with open(cls.REVIEWS_FILE, "r", encoding="utf-8") as f:
                    reviews = json.load(f)
                    if not isinstance(reviews, list) or len(reviews) == 0:
                        diagnostics["errors"].append("reviews.json is empty or invalid format")
                    diagnostics["review_count"] = len(reviews) if isinstance(reviews, list) else 0
            except Exception as e:
                diagnostics["errors"].append(f"Failed to parse reviews.json: {e}")

        # 2. Validate LLM credentials if in GEMINI mode
        if cls.LLM_MODE == "GEMINI" and not cls.GEMINI_API_KEY:
            msg = "LLM_MODE is set to 'GEMINI' but GEMINI_API_KEY is missing or empty."
            if cls.is_production():
                diagnostics["errors"].append(msg)
            else:
                diagnostics["warnings"].append(msg + " Falling back to MOCK mode is recommended.")

        # 3. Validate dependencies
        try:
            import google.genai
            diagnostics["google_genai_available"] = True
        except ImportError:
            diagnostics["google_genai_available"] = False
            if cls.LLM_MODE == "GEMINI":
                diagnostics["errors"].append("google-genai package is not installed.")

        try:
            import langgraph
            diagnostics["langgraph_available"] = True
        except ImportError:
            diagnostics["langgraph_available"] = False
            diagnostics["errors"].append("langgraph package is not installed.")

        diagnostics["status"] = "HEALTHY" if len(diagnostics["errors"]) == 0 else "DEGRADED"
        return diagnostics

    def __repr__(self) -> str:
        return (
            f"<Config env={self.APP_ENV} mode={self.LLM_MODE} "
            f"model={self.MODEL_NAME} api_key_set={bool(self.GEMINI_API_KEY)}>"
        )

# Initialize singleton config and logger
config = Config()
logger = Config.configure_logging()
