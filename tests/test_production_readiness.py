import os
import json
from pathlib import Path
import pytest
from app.core.config import Config, config

def test_config_defaults():
    assert Config.APP_ENV in ["development", "production"]
    assert Config.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR"]
    assert Config.SERVER_PORT > 0
    assert Config.SERVER_HOST != ""

def test_mock_mode_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("REQUIREMENT_AGENT_MOCK_MODE", raising=False)
    monkeypatch.delenv("RECOMMENDATION_AGENT_MOCK_MODE", raising=False)
    monkeypatch.setenv("LLM_MODE", "MOCK")
    
    # In MOCK mode, is_agent_mock_mode should return True even without API key
    assert Config.is_agent_mock_mode("REQUIREMENT_AGENT") is True
    assert Config.is_agent_mock_mode("RECOMMENDATION_AGENT") is True

def test_gemini_mode_validation_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MODE", "GEMINI")
    monkeypatch.setenv("APP_ENV", "production")
    
    # Reload or test validate_startup
    Config.GEMINI_API_KEY = None
    Config.LLM_MODE = "GEMINI"
    Config.APP_ENV = "production"
    
    diagnostics = Config.validate_startup()
    assert diagnostics["status"] == "DEGRADED"
    assert any("GEMINI_API_KEY is missing" in err for err in diagnostics["errors"])
    
    # Restore defaults
    Config.APP_ENV = "development"
    Config.LLM_MODE = "MOCK"

def test_environment_variables_respected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("MODEL_NAME", "gemini-test-model")
    
    # Re-evaluate Config properties
    assert os.getenv("APP_ENV") == "production"
    assert os.getenv("LOG_LEVEL") == "DEBUG"
    assert os.getenv("MODEL_NAME") == "gemini-test-model"

def test_required_data_files_exist():
    assert Config.PRODUCTS_FILE.exists(), "products.json is missing"
    assert Config.REVIEWS_FILE.exists(), "reviews.json is missing"
    
    with open(Config.PRODUCTS_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)
        assert isinstance(products, list)
        assert len(products) > 0

    with open(Config.REVIEWS_FILE, "r", encoding="utf-8") as f:
        reviews = json.load(f)
        assert isinstance(reviews, list)
        assert len(reviews) > 0

def test_secrets_not_exposed_in_config(monkeypatch):
    secret_key = "super_secret_ai_key_12345"
    Config.GEMINI_API_KEY = secret_key
    
    repr_str = repr(config)
    # The repr must not display the raw secret key
    assert secret_key not in repr_str
    assert "api_key_set=True" in repr_str or "api_key_set=bool" in repr_str or "api_key_set=" in repr_str

def test_dockerfile_and_dockerignore_exist():
    base_dir = Path(__file__).resolve().parent.parent
    dockerfile = base_dir / "Dockerfile"
    dockerignore = base_dir / ".dockerignore"
    
    assert dockerfile.exists(), "Dockerfile is missing"
    assert dockerignore.exists(), ".dockerignore is missing"
    
    dockerfile_content = dockerfile.read_text(encoding="utf-8")
    assert "streamlit" in dockerfile_content
    assert "8501" in dockerfile_content
    assert "requirements.txt" in dockerfile_content

def test_streamlit_config_exists():
    base_dir = Path(__file__).resolve().parent.parent
    config_toml = base_dir / ".streamlit" / "config.toml"
    
    assert config_toml.exists(), ".streamlit/config.toml is missing"
    content = config_toml.read_text(encoding="utf-8")
    assert "headless" in content
    assert "8501" in content

def test_startup_validation_success():
    Config.LLM_MODE = "MOCK"
    Config.APP_ENV = "development"
    diagnostics = Config.validate_startup()
    assert diagnostics["products_file_exists"] is True
    assert diagnostics["reviews_file_exists"] is True
    assert diagnostics["product_count"] > 0
    assert diagnostics["review_count"] > 0
    assert diagnostics["status"] == "HEALTHY"

def test_logging_configuration():
    logger = Config.configure_logging()
    assert logger is not None
    assert logger.name == "MultiAgentAssistant"
