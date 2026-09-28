import pytest
from app.database.database import (
    load_products,
    load_reviews,
    get_product_by_id,
    get_reviews_for_product,
)

def test_imports():
    import app.main
    import app.agents.requirement_agent
    import app.core.config
    import app.database.models
    assert True

def test_load_products():
    products = load_products()
    assert len(products) > 0, "Failed to load products or products list is empty"

def test_load_reviews():
    reviews = load_reviews()
    assert len(reviews) > 0, "Failed to load reviews or reviews list is empty"

def test_unique_product_ids():
    products = load_products()
    product_ids = [p.product_id for p in products]
    assert len(product_ids) == len(set(product_ids)), "Product IDs are not unique"

def test_unique_review_ids():
    reviews = load_reviews()
    review_ids = [r.review_id for r in reviews]
    assert len(review_ids) == len(set(review_ids)), "Review IDs are not unique"

def test_review_references_existing_product():
    products = load_products()
    reviews = load_reviews()
    valid_product_ids = {p.product_id for p in products}
    for r in reviews:
        assert r.product_id in valid_product_ids, f"Review {r.review_id} references non-existent product {r.product_id}"

def test_product_categories_valid():
    valid_categories = {"Laptops", "Smartphones", "Headphones", "Smartwatches"}
    products = load_products()
    for p in products:
        assert p.category in valid_categories, f"Product {p.product_id} has invalid category {p.category}"

def test_required_product_fields_exist():
    # Since we use dataclasses, instantiation would fail if required fields are missing
    # But we can verify by checking type and attributes
    products = load_products()
    for p in products:
        assert hasattr(p, "product_id")
        assert hasattr(p, "name")
        assert hasattr(p, "price")
        assert hasattr(p, "specifications")
        assert isinstance(p.specifications, dict)
        assert len(p.specifications) > 0

def test_required_review_fields_exist():
    reviews = load_reviews()
    for r in reviews:
        assert hasattr(r, "review_id")
        assert hasattr(r, "product_id")
        assert hasattr(r, "rating")
        assert hasattr(r, "review_text")
        assert hasattr(r, "sentiment_hint")

def test_get_product_by_id():
    products = load_products()
    test_id = products[0].product_id
    product = get_product_by_id(test_id)
    assert product is not None
    assert product.product_id == test_id

def test_get_reviews_for_product():
    reviews = load_reviews()
    test_id = reviews[0].product_id
    product_reviews = get_reviews_for_product(test_id)
    assert len(product_reviews) > 0
    assert all(r.product_id == test_id for r in product_reviews)
