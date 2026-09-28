import os
import json
import logging
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from app.core.config import config, logger

load_dotenv()

class LLMService:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        if self.api_key:
            try:
                from google import genai
                # Use api_key parameter to authenticate using API key instead of OAuth/Vertex
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini LLMService initialized with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.client = None
        else:
            self.client = None
            
    def is_configured(self) -> bool:
        return self.client is not None

    def generate_json(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generates a JSON response from the LLM based on the prompt.
        If the API is not configured, it raises a ValueError.
        """
        if not self.is_configured():
            logger.error("LLM generation called but Gemini is not configured")
            raise ValueError("LLM is not configured. Please set the GEMINI_API_KEY environment variable.")

        try:
            from google.genai import types
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            
            # The response.text should be valid JSON
            text = response.text.strip()
            
            # Strip markdown blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
                
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise RuntimeError(f"LLM generation failed: {e}")

llm_service = LLMService()
