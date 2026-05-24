"""Seed ChromaDB with Kreactive Toys product catalog.

This file embeds all product descriptions into ChromaDB
so the Response Agent can do semantic product search.
Run after seed.py and after ChromaDB is initialized.
"""

from pathlib import Path
from backend.config import settings
from backend.logger import setup_logger
from backend.database.database import get_db
from backend.database.models import Product
import chromadb

logger = setup_logger(__name__)


def seed_chroma() -> None:
    """Load all active products into ChromaDB as embeddings.
    
    Creates a 'products' collection in ChromaDB.
    Each product is stored with its full description
    and metadata for filtering.
    """
    # Initialize ChromaDB
    chroma_path = Path(settings.chroma_path)
    chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))

    # Get or create products collection
    collection = client.get_or_create_collection(
        name="products",
        metadata={"hnsw:space": "cosine"}
    )

    # Check if already seeded
    if collection.count() > 0:
        logger.info(
            f"Products collection already has "
            f"{collection.count()} items — skipping")
        return

    # Load products from SQLite
    db = next(get_db())
    try:
        products = db.query(Product).filter_by(
            brand_id=settings.brand_id,
            is_active=True
        ).all()

        if not products:
            logger.warning("No products found in SQLite to seed")
            return

        # Prepare documents for ChromaDB
        documents = []
        ids = []
        metadatas = []

        for product in products:
            # Build rich text document for embedding
            doc = (
                f"Product: {product.name}. "
                f"Category: {product.category}. "
                f"Age Group: {product.age_group}. "
                f"Price: Rs {product.price}. "
                f"Description: {product.description}. "
                f"In Stock: {product.stock_quantity > 0}."
            )
            documents.append(doc)
            ids.append(product.product_id)
            metadatas.append({
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "age_group": str(product.age_group or "all ages"),
                "price": str(product.price),
                "in_stock": str(product.stock_quantity > 0),
                "brand_id": settings.brand_id
            })

        # Add to ChromaDB
        collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )

        logger.info(
            f"ChromaDB seeded with {len(documents)} products")

    except Exception as e:
        logger.error(f"ChromaDB seed failed: {e}")
        raise
    finally:
        db.close()


def search_products(
    query: str,
    n_results: int = 3,
    age_group: str = None
) -> list:
    """Search products by semantic query.
    
    Used by Response Agent for product recommendations.
    Returns list of matching product dicts.
    """
    chroma_path = Path(settings.chroma_path)
    client = chromadb.PersistentClient(path=str(chroma_path))

    try:
        collection = client.get_collection("products")
    except Exception:
        logger.warning("Products collection not found in ChromaDB")
        return []

    try:
        # Build where filter if age_group provided
        where = None
        if age_group:
            where = {"age_group": age_group}

        count = collection.count()
        if count == 0:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, count),
            where=where if where else None
        )

        if not results["documents"] or \
                not results["documents"][0]:
            return []

        # Return list of product dicts
        return [
            {
                "document": doc,
                "metadata": meta
            }
            for doc, meta in zip(
                results["documents"][0],
                results["metadatas"][0]
            )
        ]

    except Exception as e:
        logger.warning(f"Product search failed: {e}")
        return []


if __name__ == "__main__":
    seed_chroma()
    print("ChromaDB product catalog seeded successfully")