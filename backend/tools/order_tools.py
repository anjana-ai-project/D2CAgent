"""Order and inventory lookup tools for the Shipping Agent."""
from datetime import datetime
from typing import Any, Dict, Optional  # noqa: F401  (Optional kept for downstream type use)

from backend.config import settings
from backend.database.database import get_db
from backend.database.models import Order, Product
from backend.logger import setup_logger
from backend.tools.base_tool import BaseTool

logger = setup_logger(__name__)


def _compute_delay(order: Order) -> Dict[str, Any]:
    """Compute delay status for an order against the current UTC time.

    Args:
        order: The Order ORM instance to inspect.

    Returns:
        A dict containing is_delayed (bool) and days_delayed (int).
    """
    is_delayed = False
    days_delayed = 0
    if (
        order.status not in ("delivered", "cancelled")
        and order.expected_delivery is not None
        and order.expected_delivery < datetime.utcnow()
    ):
        is_delayed = True
        days_delayed = int((datetime.utcnow() - order.expected_delivery).days)
    return {"is_delayed": is_delayed, "days_delayed": days_delayed}


class GetOrderByCustomer(BaseTool):
    """Return recent orders for a customer keyed by Telegram ID."""

    name = "get_order_by_customer"
    description = "Find all orders for a customer by their Telegram ID"

    async def execute(self, telegram_id: str) -> Dict[str, Any]:
        """Fetch up to 5 most recent orders for the given Telegram ID.

        Args:
            telegram_id: The customer's Telegram user identifier.

        Returns:
            A dict with success status, orders list and count.
        """
        self.logger.info(
            "get_order_by_customer: telegram_id=%s brand_id=%s",
            telegram_id,
            settings.brand_id,
        )
        db = next(get_db())
        try:
            rows = (
                db.query(Order)
                .filter(
                    Order.customer_telegram_id == telegram_id,
                    Order.brand_id == settings.brand_id,
                )
                .order_by(Order.created_at.desc())
                .limit(5)
                .all()
            )
            orders_list = []
            for order in rows:
                delay = _compute_delay(order)
                orders_list.append(
                    {
                        "order_id": order.order_id,
                        "customer_name": order.customer_name,
                        "product_name": order.product_name,
                        "quantity": order.quantity,
                        "status": order.status,
                        "tracking_number": order.tracking_number,
                        "expected_delivery": (
                            order.expected_delivery.isoformat()
                            if order.expected_delivery
                            else None
                        ),
                        "order_value": order.order_value,
                        "shipping_address": order.shipping_address,
                        "notes": order.notes,
                        "created_at": order.created_at.isoformat(),
                        "is_delayed": delay["is_delayed"],
                        "days_delayed": delay["days_delayed"],
                    }
                )
            return {
                "success": True,
                "orders": orders_list,
                "count": len(orders_list),
            }
        finally:
            db.close()


class GetOrderStatus(BaseTool):
    """Return detailed status for a single order ID."""

    name = "get_order_status"
    description = "Get detailed status for a specific order by order ID"

    async def execute(self, order_id: str) -> Dict[str, Any]:
        """Fetch the order matching the given ID for the configured brand.

        Args:
            order_id: The order identifier to look up.

        Returns:
            A dict describing the order, or {found: False} if absent.
        """
        self.logger.info("get_order_status: order_id=%s", order_id)
        db = next(get_db())
        try:
            order = (
                db.query(Order)
                .filter(
                    Order.order_id == order_id,
                    Order.brand_id == settings.brand_id,
                )
                .first()
            )
            if order is None:
                return {
                    "success": True,
                    "found": False,
                    "order_id": order_id,
                }
            delay = _compute_delay(order)
            return {
                "success": True,
                "found": True,
                "order_id": order.order_id,
                "customer_name": order.customer_name,
                "product_name": order.product_name,
                "quantity": order.quantity,
                "status": order.status,
                "tracking_number": order.tracking_number,
                "expected_delivery": (
                    order.expected_delivery.isoformat()
                    if order.expected_delivery
                    else None
                ),
                "order_value": order.order_value,
                "shipping_address": order.shipping_address,
                "notes": order.notes,
                "created_at": order.created_at.isoformat(),
                "is_delayed": delay["is_delayed"],
                "days_delayed": delay["days_delayed"],
            }
        finally:
            db.close()


class GetDeliveryEstimate(BaseTool):
    """Return a human-readable delivery estimate for a given order."""

    name = "get_delivery_estimate"
    description = (
        "Get delivery estimate and human readable message for an order"
    )

    async def execute(self, order_id: str) -> Dict[str, Any]:
        """Build a customer-facing delivery message for the given order.

        Args:
            order_id: The order identifier to look up.

        Returns:
            A dict with delivery metadata and a human-readable message.
        """
        self.logger.info("get_delivery_estimate: order_id=%s", order_id)
        db = next(get_db())
        try:
            order = (
                db.query(Order)
                .filter(
                    Order.order_id == order_id,
                    Order.brand_id == settings.brand_id,
                )
                .first()
            )
            if order is None:
                return {"success": True, "found": False}
            delay = _compute_delay(order)
            is_delayed = delay["is_delayed"]
            days_delayed = delay["days_delayed"]

            if order.status == "delivered":
                message = "Your order has been delivered"
            elif order.status == "cancelled":
                message = "Your order was cancelled"
            elif order.status == "out_for_delivery":
                message = "Your order is out for delivery today"
            elif is_delayed:
                message = (
                    f"Your order is delayed by {days_delayed} days — "
                    "we sincerely apologize"
                )
            elif order.expected_delivery:
                message = (
                    "Your order is expected by "
                    f"{order.expected_delivery.strftime('%d %b %Y')}"
                )
            else:
                message = "Delivery date will be updated soon"

            return {
                "success": True,
                "found": True,
                "order_id": order_id,
                "status": order.status,
                "tracking_number": order.tracking_number,
                "expected_delivery": (
                    order.expected_delivery.isoformat()
                    if order.expected_delivery
                    else None
                ),
                "is_delayed": is_delayed,
                "days_delayed": days_delayed,
                "message": message,
            }
        finally:
            db.close()


class GetProductStock(BaseTool):
    """Return stock availability for a product matched by name."""

    name = "get_product_stock"
    description = "Check stock availability for a product by name"

    async def execute(self, product_name: str) -> Dict[str, Any]:
        """Find the first matching active product and report its stock.

        Args:
            product_name: A partial or full product name to search for.

        Returns:
            A dict with stock and catalog details, or {found: False}.
        """
        self.logger.info("get_product_stock: product_name=%s", product_name)
        db = next(get_db())
        try:
            product = (
                db.query(Product)
                .filter(
                    Product.brand_id == settings.brand_id,
                    Product.is_active.is_(True),
                    Product.name.ilike(f"%{product_name}%"),
                )
                .first()
            )
            if product is None:
                return {
                    "success": True,
                    "found": False,
                    "product_name": product_name,
                }
            return {
                "success": True,
                "found": True,
                "product_id": product.product_id,
                "name": product.name,
                "price": product.price,
                "stock_quantity": product.stock_quantity,
                "in_stock": product.stock_quantity > 0,
                "category": product.category,
                "age_group": product.age_group,
                "description": product.description,
            }
        finally:
            db.close()
