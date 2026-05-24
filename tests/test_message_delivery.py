"""Tests for message delivery — critical path."""

import asyncio
import pytest


def test_order_lookup_real_data():
    """Test order tool returns real seeded data."""
    import sys
    sys.path.insert(0, '.')
    from backend.tools.order_tools import GetOrderStatus
    tool = GetOrderStatus()
    result = asyncio.run(tool.safe_execute(order_id="ORD001"))
    assert result["success"] is True
    assert result["found"] is True
    assert result["product_name"] == "Rainbow Stacking Rings"
    assert result["status"] == "delivered"


def test_order_not_found():
    """Test order tool handles missing order gracefully."""
    from backend.tools.order_tools import GetOrderStatus
    tool = GetOrderStatus()
    result = asyncio.run(tool.safe_execute(order_id="INVALID"))
    assert result["success"] is True
    assert result["found"] is False


def test_product_stock_check():
    """Test product stock tool returns correct data."""
    from backend.tools.order_tools import GetProductStock
    tool = GetProductStock()
    result = asyncio.run(tool.safe_execute(
        product_name="Rainbow Stacking Rings"))
    assert result["success"] is True
    assert result["found"] is True
    assert result["in_stock"] is True
    assert result["price"] == 599.0


def test_generate_coupon_creates_db_entry():
    """Test coupon generation creates entry in database."""
    import asyncio
    from backend.tools.compensation_tools import GenerateCoupon
    tool = GenerateCoupon()
    result = asyncio.run(tool.safe_execute(
        order_id="ORD001",
        discount_percent=10
    ))
    assert result["success"] is True
    assert "KREACT" in result["coupon_code"]
    assert result["discount_percent"] == 10


def test_flag_creation():
    """Test flag creation saves to database."""
    from backend.tools.compensation_tools import RaiseFlag
    tool = RaiseFlag()
    result = asyncio.run(tool.safe_execute(
        reason="Test flag",
        urgency="medium",
        raised_by_agent="Support Agent"
    ))
    assert result["success"] is True
    assert "flag_id" in result
    assert result["urgency"] == "medium"


def test_health_endpoint(client):
    """Test health endpoint returns correct brand."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["brand"] == "Kreactive Toys"


def test_get_workflows(client):
    """Test workflows endpoint returns seeded templates."""
    response = client.get("/workflows")
    assert response.status_code == 200
    workflows = response.json()
    assert len(workflows) >= 1


def test_get_products(client):
    """Test products endpoint returns seeded catalog."""
    response = client.get("/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) == 10