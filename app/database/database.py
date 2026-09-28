import json
import os
from typing import List, Optional
from .models import Product, Review

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
REVIEWS_FILE = os.path.join(DATA_DIR, "reviews.json")

def load_products() -> List[Product]:
    if not os.path.exists(PRODUCTS_FILE):
        print(f"Error: Products file not found at {PRODUCTS_FILE}")
        return []
        
    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        products = []
        for item in data:
            try:
                products.append(Product(**item))
            except TypeError as e:
                print(f"Error validating product record: {e} - Data: {item}")
        return products
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {PRODUCTS_FILE}")
        return []
    except Exception as e:
        print(f"Error loading products: {e}")
        return []

def load_reviews() -> List[Review]:
    if not os.path.exists(REVIEWS_FILE):
        print(f"Error: Reviews file not found at {REVIEWS_FILE}")
        return []
        
    try:
        with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        reviews = []
        for item in data:
            try:
                reviews.append(Review(**item))
            except TypeError as e:
                print(f"Error validating review record: {e} - Data: {item}")
        return reviews
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {REVIEWS_FILE}")
        return []
    except Exception as e:
        print(f"Error loading reviews: {e}")
        return []

def get_product_by_id(product_id: str) -> Optional[Product]:
    products = load_products()
    for p in products:
        if p.product_id == product_id:
            return p
    return None

def get_products_by_category(category: str) -> List[Product]:
    products = load_products()
    return [p for p in products if p.category.lower() == category.lower()]

def get_reviews_for_product(product_id: str) -> List[Review]:
    reviews = load_reviews()
    return [r for r in reviews if r.product_id == product_id]
