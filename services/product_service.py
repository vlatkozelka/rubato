import json
from typing import Optional, List

from app.config import DATA_DIR
from models.product import Product


def _load_products() -> list[dict]:
    path = DATA_DIR / "products.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_product_by_id(product_id: str) -> Optional[Product]:
    for raw in _load_products():
        if raw["id"] == product_id:
            return Product(**raw)
    return None


def get_products_by_name(name: str) -> List[Product]:
    # Naive word-overlap matching over flat JSON — no real search index here.
    # A production system would use Elasticsearch/Algolia, or Postgres full-text
    # search / trigram matching if staying in SQL. Acceptable for a 20-item
    # sandbox catalog; would not scale to a real product count.
    query_words = {w.rstrip("s") for w in name.lower().split()}

    products: List[Product] = []
    for raw in _load_products():
        product_words = {w.rstrip("s") for w in raw["name"].lower().split()}
        if query_words & product_words:  # any overlap at all
            products.append(Product(**raw))
    return products
