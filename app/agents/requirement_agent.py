import json
import os
import re
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError
from app.core.llm import llm_service

class ShoppingRequirements(BaseModel):
    category: Optional[str] = Field(
        None, 
        description="Must be one of: 'Laptops', 'Smartphones', 'Headphones', 'Smartwatches'. Null if unresolved."
    )
    product_type: Optional[str] = Field(None, description="More specific product type if mentioned")
    budget: Optional[float] = Field(None, description="Maximum budget converted to numeric INR. E.g., '70k' -> 70000.")
    currency: Optional[str] = Field("INR", description="Currency code")
    purpose: Optional[List[str]] = Field(default_factory=list, description="List of purposes or use cases")
    preferred_brands: Optional[List[str]] = Field(default_factory=list, description="Brands the customer explicitly asked for")
    required_features: Optional[List[str]] = Field(default_factory=list, description="Features the customer explicitly needs")
    preferred_features: Optional[List[str]] = Field(default_factory=list, description="Features the customer would prefer but are not mandatory")
    minimum_rating: Optional[float] = Field(None, description="Minimum star rating requested")
    important_specifications: Optional[List[str]] = Field(default_factory=list, description="Specific tech specs requested (e.g., '16GB RAM')")
    constraints: Optional[List[str]] = Field(default_factory=list, description="Other constraints or limitations")

class RequirementAgent:
    BRAND_MAP = {
        "hp": "HP", "hewlett": "HP",
        "dell": "Dell",
        "lenovo": "Lenovo", "thinkpad": "Lenovo", "ideapad": "Lenovo", "legion": "Lenovo",
        "samsung": "Samsung",
        "apple": "Apple", "macbook": "Apple",
        "asus": "Asus",
        "acer": "Acer",
        "msi": "MSI",
        "lg": "LG",
        "sony": "Sony",
        "oneplus": "OnePlus",
        "xiaomi": "Xiaomi", "redmi": "Xiaomi",
        "realme": "Realme",
        "oppo": "Oppo",
        "vivo": "Vivo",
        "motorola": "Motorola",
        "nokia": "Nokia",
        "google": "Google",
    }

    def __init__(self):
        self.system_prompt = """You are a shopping requirement extraction agent.
Your job is ONLY to identify what the customer wants from their natural language request.

CRITICAL RULES:
- Do NOT recommend products.
- Do NOT rank products.
- Do NOT invent products, prices, or specifications.
- Do NOT analyze reviews or make purchasing decisions.
- Extract ONLY information present in the user's request.
- If information is missing, leave the corresponding field empty/null/empty list.

DATA NORMALIZATION RULES:
1. CATEGORY: Normalize product categories to exactly one of: ["Laptops", "Smartphones", "Headphones", "Smartwatches"].
   - "notebook" -> "Laptops"
   - "mobile", "cell phone" -> "Smartphones"
   - "earphones", "wireless headphones" -> "Headphones"
   - "smart watch" -> "Smartwatches"
   If unclear, leave category as null.
2. BUDGET: Support Indian price expressions and convert to a numeric INR value.
   - "Rs.70,000" -> 70000
   - "70k" -> 70000
   - "under 50k" -> 50000
   - "maximum 60000" -> 60000
   Do not guess a budget if none was provided.
3. PRIORITY: Distinguish between REQUIRED and PREFERRED features.
   - "I need 16GB RAM and preferably Lenovo" -> "16GB RAM" is important_specifications, "Lenovo" is preferred_brands.
4. BRANDS: Extract ALL brand names mentioned as preferences into preferred_brands as a list.
   - "from HP, Dell, or Lenovo" -> preferred_brands: ["HP", "Dell", "Lenovo"]
   - "HP, Dell, Lenovo" -> preferred_brands: ["HP", "Dell", "Lenovo"]
   - "brands like HP, Dell, Lenovo" -> preferred_brands: ["HP", "Dell", "Lenovo"]
   - "I prefer HP, Dell, Lenovo" -> preferred_brands: ["HP", "Dell", "Lenovo"]
   - "preferably from Samsung" -> preferred_brands: ["Samsung"]
   Do NOT put brand names into required_features.
   Do NOT treat preferred brands as mandatory unless the user says "must be" or "only".

CUSTOMER REQUEST:
"{request}"

RESPOND EXACTLY WITH A JSON OBJECT MATCHING THIS SCHEMA:
{schema}
"""

    def extract_requirements(self, customer_request: str) -> ShoppingRequirements:
        """Parses a natural language request into structured ShoppingRequirements."""
        if not customer_request or not customer_request.strip():
            return ShoppingRequirements()
            
        mock_mode = os.getenv("REQUIREMENT_AGENT_MOCK_MODE", "false").lower() == "true"
        if mock_mode:
            return self._mock_extract(customer_request)
            
        if not llm_service.is_configured():
            raise RuntimeError("LLM is not configured. Please set the GEMINI_API_KEY environment variable.")
            
        schema_json = json.dumps(ShoppingRequirements.model_json_schema(), indent=2)
        prompt = self.system_prompt.format(request=customer_request, schema=schema_json)
        
        try:
            response_data = llm_service.generate_json(prompt)
            requirements = ShoppingRequirements(**response_data)
            return requirements
        except Exception as e:
            print(f"Error during AI requirement extraction, using fallback: {e}")
            return self._mock_extract(customer_request)

    def _extract_brands(self, request: str) -> List[str]:
        """
        Extract brand names from a natural language request.
        Handles multi-brand patterns:
          "from HP, Dell, or Lenovo"
          "brands like HP, Dell, Lenovo"
          "I prefer HP, Dell, Lenovo"
        Falls back to per-keyword word-boundary scan.
        """
        found: List[str] = []
        req_lower = request.lower()
        brand_map = self.BRAND_MAP

        # Strategy 1: explicit brand-list phrases
        brand_list_pattern = re.compile(
            r'(?:from|by|brands?\s+like|prefer(?:red|ably)?|such\s+as)\s+'
            r'((?:[\w]+)(?:\s*,\s*(?:[\w]+))*(?:\s+or\s+(?:[\w]+))?)',
            re.IGNORECASE
        )
        for m in brand_list_pattern.finditer(request):
            segment = m.group(1)
            parts = re.split(r'\s*,\s*|\s+or\s+', segment, flags=re.IGNORECASE)
            for part in parts:
                part_lower = part.strip().lower()
                for keyword, brand in brand_map.items():
                    if part_lower == keyword or part_lower.startswith(keyword + ' '):
                        if brand not in found:
                            found.append(brand)

        # Strategy 2: word-boundary scan for any brand keywords in the full text
        for keyword, brand in brand_map.items():
            if re.search(r'\b' + re.escape(keyword) + r'\b', req_lower):
                if brand not in found:
                    found.append(brand)

        return found

    def _mock_extract(self, request: str) -> ShoppingRequirements:
        reqs = ShoppingRequirements()
        req_lower = request.lower()
        
        # Category
        if re.search(r'\b(laptop|laptops|notebook)\b', req_lower):
            reqs.category = "Laptops"
        elif re.search(r'\b(smartphone|smartphones|mobile|mobile phone|cell phone)\b', req_lower):
            reqs.category = "Smartphones"
        elif re.search(r'\b(headphone|headphones|earphones)\b', req_lower):
            reqs.category = "Headphones"
        elif re.search(r'\b(smartwatch|smartwatches|smart watch)\b', req_lower):
            reqs.category = "Smartwatches"
            
        # Budget
        k_match = re.search(r'(\d+)\s*k\b', req_lower)
        if k_match:
            reqs.budget = float(k_match.group(1)) * 1000
        else:
            num_match = re.search(r'[\u20b9]?\s*(\d[\d,]*\d|\d{4,})', req_lower)
            if num_match:
                raw = num_match.group(1).replace(',', '')
                val = float(raw)
                if val >= 500:
                    reqs.budget = val

        # Purpose
        if "programming" in req_lower or "coding" in req_lower:
            reqs.purpose.append("programming")
        if "gaming" in req_lower:
            reqs.purpose.append("gaming")
        if "fitness" in req_lower:
            reqs.purpose.append("fitness")
        if "work" in req_lower or "office" in req_lower or "business" in req_lower:
            reqs.purpose.append("work")
        if "travel" in req_lower:
            reqs.purpose.append("travel")

        # Important Specifications
        ram_match = re.search(r'(\d+)\s*gb\s*ram', req_lower)
        if ram_match:
            reqs.important_specifications.append(f"{ram_match.group(1)}GB RAM")

        storage_match = re.search(r'(\d+)\s*(gb|tb)\s*(ssd|storage|hdd)', req_lower)
        if storage_match:
            reqs.important_specifications.append(
                f"{storage_match.group(1)}{storage_match.group(2).upper()} {storage_match.group(3).upper()}"
            )

        # Preferred features
        if "battery life" in req_lower or "good battery" in req_lower or "long battery" in req_lower:
            reqs.preferred_features.append("good battery life")
        if "lightweight" in req_lower or "light weight" in req_lower:
            reqs.preferred_features.append("lightweight")
        if "4k" in req_lower:
            reqs.preferred_features.append("4K display")

        # Required features
        if "noise cancellation" in req_lower or "noise-cancellation" in req_lower:
            reqs.required_features.append("noise cancellation")
        if "camera" in req_lower:
            reqs.required_features.append("camera")
        if "gps" in req_lower:
            reqs.required_features.append("GPS")

        # Preferred Brands
        reqs.preferred_brands = self._extract_brands(request)

        return reqs
