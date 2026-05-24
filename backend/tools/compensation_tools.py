"""Compensation, guardrail and escalation tools for the Compensation Agent."""
import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from backend.config import settings
from backend.database.database import get_db
from backend.database.models import Coupon, Flag
from backend.logger import setup_logger
from backend.tools.base_tool import BaseTool

logger = setup_logger(__name__)


class CheckGuardrail(BaseTool):
    """Check whether a proposed compensation amount fits brand guardrails."""

    name = "check_guardrail"
    description = (
        "Check if compensation amount is within allowed guardrail limits"
    )

    async def execute(self, amount_inr: float) -> Dict[str, Any]:
        """Evaluate a compensation amount against the configured maximum.

        Args:
            amount_inr: The proposed compensation amount in INR.

        Returns:
            A dict describing whether the amount is within the limit and
            whether human approval or auto-approval is appropriate.
        """
        self.logger.info("check_guardrail: amount_inr=%s", amount_inr)
        return {
            "success": True,
            "amount_inr": amount_inr,
            "max_allowed_inr": settings.max_compensation,
            "within_limit": amount_inr <= settings.max_compensation,
            "requires_human_approval": amount_inr > settings.max_compensation,
            "auto_approve": amount_inr <= 200,
        }


class EvaluateCompensation(BaseTool):
    """Recommend a compensation action given the customer situation."""

    name = "evaluate_compensation"
    description = (
        "Evaluate appropriate compensation given the customer situation"
    )

    async def execute(
        self,
        intent: str,
        is_safety_alert: bool = False,
        days_delayed: int = 0,
        order_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Decide the recommended compensation given case context.

        Args:
            intent: The classified customer intent.
            is_safety_alert: True if the case is a safety concern.
            days_delayed: Number of days the order is delayed, if any.
            order_data: Optional snapshot of order context, unused in the
                default policy but kept for downstream extension.

        Returns:
            A dict with recommended_action, reason, urgency and
            suggested_discount.
        """
        self.logger.info(
            "evaluate_compensation: intent=%s safety=%s days_delayed=%s",
            intent,
            is_safety_alert,
            days_delayed,
        )
        if is_safety_alert:
            return {
                "success": True,
                "recommended_action": "escalate",
                "reason": "Safety concern requires immediate human review",
                "urgency": "critical",
                "suggested_discount": 0,
            }
        if intent in ("complaint", "return_request") and days_delayed > 5:
            return {
                "success": True,
                "recommended_action": "coupon",
                "reason": "Significant delay warrants compensation",
                "urgency": "high",
                "suggested_discount": 10,
            }
        if intent in ("complaint", "return_request") and days_delayed > 2:
            return {
                "success": True,
                "recommended_action": "coupon",
                "reason": "Delay warrants compensation",
                "urgency": "medium",
                "suggested_discount": 5,
            }
        if intent in ("complaint", "return_request") and days_delayed == 0:
            return {
                "success": True,
                "recommended_action": "coupon",
                "reason": "Product issue warrants compensation",
                "urgency": "medium",
                "suggested_discount": 5,
            }
        if intent == "cancellation":
            return {
                "success": True,
                "recommended_action": "apology",
                "reason": "Order cancellation acknowledged",
                "urgency": "low",
                "suggested_discount": 0,
            }
        return {
            "success": True,
            "recommended_action": "apology",
            "reason": "Standard resolution",
            "urgency": "low",
            "suggested_discount": 0,
        }
        


class GenerateCoupon(BaseTool):
    """Generate and persist a unique discount coupon for a customer."""

    name = "generate_coupon"
    description = "Generate a unique coupon code for customer compensation"

    async def execute(
        self,
        order_id: str,
        discount_percent: int,
        brand_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Kreactive-prefixed coupon valid for 30 days.

        Args:
            order_id: The order identifier the coupon is tied to.
            discount_percent: The discount percentage to grant.
            brand_id: Optional brand override; defaults to settings.brand_id.

        Returns:
            A dict containing the generated coupon code, discount, expiry
            and the originating order ID.
        """
        use_brand_id = brand_id or settings.brand_id
        chars = string.ascii_uppercase + string.digits
        suffix = "".join(random.choices(chars, k=6))
        code = f"KREACT{suffix}"
        expires_at = datetime.utcnow() + timedelta(days=30)

        self.logger.info(
            "generate_coupon: order_id=%s discount=%s code=%s",
            order_id,
            discount_percent,
            code,
        )

        db = next(get_db())
        try:
            coupon = Coupon(
                coupon_id=str(uuid.uuid4()),
                brand_id=use_brand_id,
                order_id=order_id,
                code=code,
                discount_percent=discount_percent,
                created_by_agent="agent_compensation",
                used=False,
                expires_at=expires_at,
            )
            db.add(coupon)
            db.commit()
            return {
                "success": True,
                "coupon_code": code,
                "discount_percent": discount_percent,
                "expires_at": expires_at.isoformat(),
                "order_id": order_id,
            }
        finally:
            db.close()


class RaiseFlag(BaseTool):
    """Raise a dashboard-visible flag for human review."""

    name = "raise_flag"
    description = "Raise a flag for human review visible in the dashboard"

    async def execute(
        self,
        reason: str,
        urgency: str,
        raised_by_agent: str,
        order_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        brand_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist a new open Flag record tied to the optional order/conv.

        Args:
            reason: Human-readable reason for the flag.
            urgency: Severity level (low/medium/high/critical).
            raised_by_agent: Identifier of the agent raising the flag.
            order_id: Optional related order ID.
            conversation_id: Optional related conversation ID.
            brand_id: Optional brand override; defaults to settings.brand_id.

        Returns:
            A dict containing the created flag_id and its key fields.
        """
        use_brand_id = brand_id or settings.brand_id
        self.logger.info(
            "raise_flag: urgency=%s reason=%s by=%s",
            urgency,
            reason,
            raised_by_agent,
        )
        db = next(get_db())
        try:
            flag = Flag(
                flag_id=str(uuid.uuid4()),
                brand_id=use_brand_id,
                order_id=order_id,
                conversation_id=conversation_id,
                reason=reason,
                urgency=urgency,
                raised_by_agent=raised_by_agent,
                status="open",
            )
            db.add(flag)
            db.commit()
            return {
                "success": True,
                "flag_id": flag.flag_id,
                "urgency": urgency,
                "reason": reason,
                "raised_by_agent": raised_by_agent,
            }
        finally:
            db.close()
