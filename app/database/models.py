from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Product:
    product_id: str
    name: str
    brand: str
    category: str
    price: float
    currency: str
    rating: float
    review_count: int
    description: str
    specifications: Dict[str, Any]

@dataclass
class Review:
    review_id: str
    product_id: str
    rating: int
    review_text: str
    sentiment_hint: str
