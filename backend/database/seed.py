"""Seed the D2CAgent database with Kreactive Toys demo data."""
import json  # noqa: F401  (available for downstream JSON work)
import uuid  # noqa: F401  (available for downstream UUID work)
from datetime import datetime, timedelta

from backend.config import settings
from backend.database.database import get_db, init_db
from backend.database.models import Agent, Brand, Order, Product, Workflow
from backend.logger import setup_logger

logger = setup_logger(__name__)


def seed_brand() -> Brand:
    """Build the Kreactive Toys brand record.

    Returns:
        An unsaved Brand ORM instance populated from settings.
    """
    return Brand(
        brand_id=settings.brand_id,
        name=settings.brand_name,
        telegram_bot_token=settings.telegram_bot_token,
        webhook_secret="kreactive_webhook_secret_2024",
    )


def seed_products() -> list:
    """Build the 10 Kreactive Toys product catalog records.

    Returns:
        A list of unsaved Product ORM instances for the brand.
    """
    return [
        Product(
            product_id="PROD001",
            brand_id=settings.brand_id,
            name="Rainbow Stacking Rings",
            category="Stacking Toys",
            price=599.0,
            stock_quantity=45,
            description=(
                "Handcrafted wooden stacking rings in 7 rainbow colors. "
                "Develops motor skills and color recognition. "
                "Safe, non-toxic paint."
            ),
            age_group="1-3 years",
            is_active=True,
        ),
        Product(
            product_id="PROD002",
            brand_id=settings.brand_id,
            name="Animal Puzzle Set",
            category="Puzzles",
            price=799.0,
            stock_quantity=30,
            description=(
                "12-piece wooden animal puzzle featuring farm animals. "
                "Each piece has a knob for easy handling. "
                "Develops problem-solving skills."
            ),
            age_group="2-4 years",
            is_active=True,
        ),
        Product(
            product_id="PROD003",
            brand_id=settings.brand_id,
            name="Wooden Alphabet Blocks",
            category="Educational",
            price=999.0,
            stock_quantity=25,
            description=(
                "Set of 26 handcrafted wooden alphabet blocks with letters, "
                "numbers and pictures. Promotes early literacy and numeracy."
            ),
            age_group="2-5 years",
            is_active=True,
        ),
        Product(
            product_id="PROD004",
            brand_id=settings.brand_id,
            name="Dinosaur Shape Sorter",
            category="Shape Sorters",
            price=849.0,
            stock_quantity=20,
            description=(
                "Wooden dinosaur-themed shape sorter with 6 unique shapes. "
                "Teaches shape recognition and hand-eye coordination."
            ),
            age_group="2-4 years",
            is_active=True,
        ),
        Product(
            product_id="PROD005",
            brand_id=settings.brand_id,
            name="Magnetic Drawing Board",
            category="Creative Play",
            price=699.0,
            stock_quantity=35,
            description=(
                "Wooden frame magnetic drawing board with stylus. "
                "Endless drawing and erasing. Screen-free creative play."
            ),
            age_group="3-6 years",
            is_active=True,
        ),
        Product(
            product_id="PROD006",
            brand_id=settings.brand_id,
            name="Wooden Train Set",
            category="Vehicle Toys",
            price=1499.0,
            stock_quantity=15,
            description=(
                "20-piece handcrafted wooden train set with engine, "
                "carriages and track pieces. Develops spatial thinking."
            ),
            age_group="3-6 years",
            is_active=True,
        ),
        Product(
            product_id="PROD007",
            brand_id=settings.brand_id,
            name="Forest Animal Figurines",
            category="Figurines",
            price=649.0,
            stock_quantity=40,
            description=(
                "Set of 8 handpainted wooden forest animal figurines. "
                "Fox, deer, owl, bear, rabbit, hedgehog, squirrel and wolf."
            ),
            age_group="3+ years",
            is_active=True,
        ),
        Product(
            product_id="PROD008",
            brand_id=settings.brand_id,
            name="Activity Cube",
            category="Activity Toys",
            price=1299.0,
            stock_quantity=12,
            description=(
                "5-sided wooden activity cube with abacus, shape sorter, "
                "maze, clock and gear. All-in-one developmental toy."
            ),
            age_group="1-4 years",
            is_active=True,
        ),
        Product(
            product_id="PROD009",
            brand_id=settings.brand_id,
            name="Wooden Kitchen Set",
            category="Pretend Play",
            price=1899.0,
            stock_quantity=8,
            description=(
                "18-piece wooden kitchen playset with pots, pans, "
                "utensils and food items. Encourages imaginative play."
            ),
            age_group="3-6 years",
            is_active=True,
        ),
        Product(
            product_id="PROD010",
            brand_id=settings.brand_id,
            name="Balancing Cactus Game",
            category="Games",
            price=549.0,
            stock_quantity=50,
            description=(
                "Wooden stacking balancing game with cactus pieces. "
                "Develops concentration, patience and fine motor skills."
            ),
            age_group="4+ years",
            is_active=True,
        ),
    ]


def seed_agents() -> list:
    """Build the 4 Kreactive Toys agent definitions.

    Returns:
        A list of unsaved Agent ORM instances configured for the brand.
    """
    support = Agent(
        agent_id="agent_support",
        brand_id=settings.brand_id,
        name="Support Agent",
        role="support",
        system_prompt=(
            "You are a friendly and professional customer support agent "
            "for Kreactive Toys, a D2C brand selling handcrafted wooden "
            "toys for kids in India. Your job is to understand customer "
            "queries, check their conversation history, classify their "
            "intent, and route them to the right specialist agent. Always "
            "be warm, empathetic and professional. Never make promises "
            "you cannot keep."
        ),
        model=settings.llm_model,
        channel="telegram",
        memory_enabled=True,
    )
    support.tools = ["read_history"]
    support.skills = ["conversation_management", "intent_classification"]
    support.guardrails = {
        "max_response_time_seconds": 30,
        "escalate_on_keywords": [
            "injury",
            "safety",
            "swallowed",
            "hurt",
            "emergency",
        ],
    }
    support.interaction_rules = [
        "Always greet the customer by their first name if known",
        "If customer mentions injury or safety escalate immediately as critical",
        "Escalate to human after 2 failed resolution attempts",
        "Always acknowledge the customers concern before routing",
    ]

    shipping = Agent(
        agent_id="agent_shipping",
        brand_id=settings.brand_id,
        name="Shipping Agent",
        role="shipping",
        system_prompt=(
            "You are the order and shipping specialist for Kreactive Toys. "
            "You have access to real order and inventory data. Your job is "
            "to look up order status, delivery estimates and stock "
            "availability. Return structured, accurate information. If an "
            "order is delayed or has issues flag it for compensation review."
        ),
        model=settings.llm_model,
        channel="telegram",
        memory_enabled=False,
    )
    shipping.tools = [
        "get_order_by_customer",
        "get_order_status",
        "get_delivery_estimate",
        "get_product_stock",
    ]
    shipping.skills = ["order_lookup", "inventory_check"]
    shipping.guardrails = {"max_orders_to_return": 5}
    shipping.interaction_rules = [
        "Always return exact order status from the database",
        "Never guess delivery dates — use only database values",
        "If order is delayed by more than 2 days flag for compensation",
    ]

    compensation = Agent(
        agent_id="agent_compensation",
        brand_id=settings.brand_id,
        name="Compensation Agent",
        role="compensation",
        system_prompt=(
            "You are the compensation and resolution specialist for "
            "Kreactive Toys. You evaluate customer situations and decide "
            "the appropriate resolution — apology, coupon, replacement or "
            "escalation to human. You must stay within the compensation "
            "guardrails configured for this brand. Always be fair, "
            "empathetic and solution-focused."
        ),
        model=settings.llm_model,
        channel="telegram",
        memory_enabled=False,
    )
    compensation.tools = [
        "evaluate_compensation",
        "generate_coupon",
        "raise_flag",
        "check_guardrail",
    ]
    compensation.skills = ["refund_processing", "escalation"]
    compensation.guardrails = {
        "max_compensation_inr": 500,
        "auto_approve_below_inr": 200,
        "require_human_above_inr": 500,
    }
    compensation.interaction_rules = [
        "Never promise compensation above the configured limit without human approval",
        "Always acknowledge customer frustration before offering solution",
        "Never admit product defect — say we are looking into this",
        "Offer coupon first before escalating to human",
    ]

    response = Agent(
        agent_id="agent_response",
        brand_id=settings.brand_id,
        name="Response Agent",
        role="response",
        system_prompt=(
            "You are the final response composer for Kreactive Toys. You "
            "receive the full context from all specialist agents and craft "
            "a single, clear, warm and professional response to send to "
            "the customer on Telegram. Your response must be concise "
            "(under 200 words), actionable and end with an offer to help "
            "further. Evaluate if the response fully resolves the customer "
            "query. If not, signal for another compensation review."
        ),
        model=settings.llm_model,
        channel="telegram",
        memory_enabled=True,
    )
    response.tools = ["send_telegram_message", "save_conversation"]
    response.skills = ["response_crafting"]
    response.guardrails = {"max_response_words": 200, "max_loop_iterations": 2}
    response.interaction_rules = [
        "Always respond in the same language the customer used",
        "Never mention competitor brands",
        "Always end with: Is there anything else I can help you with?",
        "Never admit liability on safety complaints",
        "Keep response under 200 words",
    ]

    return [support, shipping, compensation, response]


def seed_orders() -> list:
    """Build 15 demo orders with varied statuses and Indian customer names.

    Returns:
        A list of unsaved Order ORM instances for the brand.
    """
    now = datetime.utcnow()
    return [
        Order(
            order_id="ORD001",
            brand_id=settings.brand_id,
            customer_name="Priya Sharma",
            customer_telegram_id="111001",
            product_name="Rainbow Stacking Rings",
            quantity=1,
            status="delivered",
            tracking_number="TRK001234",
            expected_delivery=now - timedelta(days=2),
            order_value=599.0,
            shipping_address="14 MG Road, Bengaluru 560001",
            created_at=now - timedelta(days=8),
        ),
        Order(
            order_id="ORD002",
            brand_id=settings.brand_id,
            customer_name="Rahul Mehta",
            customer_telegram_id="111002",
            product_name="Wooden Train Set",
            quantity=1,
            status="out_for_delivery",
            tracking_number="TRK001235",
            expected_delivery=now + timedelta(days=1),
            order_value=1499.0,
            shipping_address="7 Juhu Beach Road, Mumbai 400049",
            created_at=now - timedelta(days=5),
        ),
        Order(
            order_id="ORD003",
            brand_id=settings.brand_id,
            customer_name="Ananya Krishnan",
            customer_telegram_id="111003",
            product_name="Animal Puzzle Set",
            quantity=2,
            status="shipped",
            tracking_number="TRK001236",
            expected_delivery=now + timedelta(days=3),
            order_value=1598.0,
            shipping_address="22 Anna Nagar, Chennai 600040",
            created_at=now - timedelta(days=4),
        ),
        Order(
            order_id="ORD004",
            brand_id=settings.brand_id,
            customer_name="Vikram Singh",
            customer_telegram_id="111004",
            product_name="Activity Cube",
            quantity=1,
            status="processing",
            tracking_number=None,
            expected_delivery=now + timedelta(days=6),
            order_value=1299.0,
            shipping_address="33 Connaught Place, New Delhi 110001",
            created_at=now - timedelta(days=1),
        ),
        Order(
            order_id="ORD005",
            brand_id=settings.brand_id,
            customer_name="Deepa Nair",
            customer_telegram_id="111005",
            product_name="Wooden Kitchen Set",
            quantity=1,
            status="shipped",
            tracking_number="TRK001238",
            expected_delivery=now + timedelta(days=2),
            order_value=1899.0,
            shipping_address="5 Marine Drive, Kochi 682031",
            created_at=now - timedelta(days=3),
        ),
        Order(
            order_id="ORD006",
            brand_id=settings.brand_id,
            customer_name="Arjun Patel",
            customer_telegram_id="111006",
            product_name="Dinosaur Shape Sorter",
            quantity=1,
            status="delivered",
            tracking_number="TRK001239",
            expected_delivery=now - timedelta(days=1),
            order_value=849.0,
            shipping_address="9 CG Road, Ahmedabad 380009",
            created_at=now - timedelta(days=7),
        ),
        Order(
            order_id="ORD007",
            brand_id=settings.brand_id,
            customer_name="Kavitha Reddy",
            customer_telegram_id="111007",
            product_name="Wooden Alphabet Blocks",
            quantity=1,
            status="out_for_delivery",
            tracking_number="TRK001240",
            expected_delivery=now + timedelta(hours=4),
            order_value=999.0,
            shipping_address="18 Banjara Hills, Hyderabad 500034",
            created_at=now - timedelta(days=5),
        ),
        Order(
            order_id="ORD008",
            brand_id=settings.brand_id,
            customer_name="Suresh Kumar",
            customer_telegram_id="111008",
            product_name="Forest Animal Figurines",
            quantity=2,
            status="processing",
            tracking_number=None,
            expected_delivery=now + timedelta(days=5),
            order_value=1298.0,
            shipping_address="27 Park Street, Kolkata 700016",
            created_at=now - timedelta(days=2),
        ),
        Order(
            order_id="ORD009",
            brand_id=settings.brand_id,
            customer_name="Meera Iyer",
            customer_telegram_id="111009",
            product_name="Balancing Cactus Game",
            quantity=1,
            status="delivered",
            tracking_number="TRK001242",
            expected_delivery=now - timedelta(days=3),
            order_value=549.0,
            shipping_address="3 Residency Road, Bengaluru 560025",
            created_at=now - timedelta(days=10),
        ),
        Order(
            order_id="ORD010",
            brand_id=settings.brand_id,
            customer_name="Rohan Gupta",
            customer_telegram_id="111010",
            product_name="Magnetic Drawing Board",
            quantity=1,
            status="shipped",
            tracking_number="TRK001243",
            expected_delivery=now + timedelta(days=4),
            order_value=699.0,
            shipping_address="11 Sector 17, Chandigarh 160017",
            created_at=now - timedelta(days=3),
        ),
        Order(
            order_id="ORD011",
            brand_id=settings.brand_id,
            customer_name="Sneha Joshi",
            customer_telegram_id="111011",
            product_name="Activity Cube",
            quantity=1,
            status="cancelled",
            tracking_number=None,
            expected_delivery=None,
            order_value=1299.0,
            shipping_address="6 FC Road, Pune 411004",
            created_at=now - timedelta(days=6),
        ),
        Order(
            order_id="ORD012",
            brand_id=settings.brand_id,
            customer_name="Karthik Raj",
            customer_telegram_id="111012",
            product_name="Wooden Train Set",
            quantity=1,
            status="shipped",
            tracking_number="TRK001245",
            expected_delivery=now + timedelta(days=2),
            order_value=1499.0,
            shipping_address="42 Nungambakkam, Chennai 600034",
            created_at=now - timedelta(days=4),
        ),
        Order(
            order_id="ORD013",
            brand_id=settings.brand_id,
            customer_name="Pooja Verma",
            customer_telegram_id="111013",
            product_name="Rainbow Stacking Rings",
            quantity=2,
            status="out_for_delivery",
            tracking_number="TRK001246",
            expected_delivery=now + timedelta(hours=6),
            order_value=1198.0,
            shipping_address="15 Hazratganj, Lucknow 226001",
            created_at=now - timedelta(days=5),
        ),
        Order(
            order_id="ORD014",
            brand_id=settings.brand_id,
            customer_name="Amit Bose",
            customer_telegram_id="111014",
            product_name="Animal Puzzle Set",
            quantity=1,
            status="processing",
            tracking_number=None,
            expected_delivery=now + timedelta(days=7),
            order_value=799.0,
            shipping_address="8 Salt Lake, Kolkata 700091",
            created_at=now - timedelta(hours=12),
        ),
        Order(
            order_id="ORD015",
            brand_id=settings.brand_id,
            customer_name="Divya Menon",
            customer_telegram_id="111015",
            product_name="Wooden Kitchen Set",
            quantity=1,
            status="delivered",
            tracking_number="TRK001248",
            expected_delivery=now - timedelta(days=4),
            order_value=1899.0,
            shipping_address="19 Koramangala, Bengaluru 560034",
            created_at=now - timedelta(days=9),
        ),
    ]


def seed_workflows() -> list:
    """Build the 2 workflow templates for Kreactive Toys.

    Returns:
        A list of unsaved Workflow ORM instances marked as templates.
    """
    order_support = Workflow(
        workflow_id="wf_order_support",
        brand_id=settings.brand_id,
        name="Order Support Flow",
        description=(
            "Handle order status, complaints, returns and cancellations "
            "with full agent collaboration"
        ),
        is_template=True,
        status="active",
    )
    order_support.agent_sequence = [
        "support",
        "shipping",
        "compensation",
        "response",
    ]
    order_support.conditional_edges = {
        "support": {
            "order_status": "shipping",
            "order_modification": "shipping",
            "complaint": "compensation",
            "return_request": "compensation",
            "cancellation": "compensation",
            "simple_faq": "response",
            "product_query": "response",
            "safety_alert": "response",
            "positive_feedback": "response",
        },
        "shipping": {
            "issue_found": "compensation",
            "resolved": "response",
        },
        "compensation": {
            "resolution_ready": "response",
        },
        "response": {
            "sufficient": "END",
            "insufficient": "compensation",
        },
    }
    order_support.loop_config = {
        "max_iterations": 2,
        "loop_agents": ["compensation", "response"],
    }

    product_discovery = Workflow(
        workflow_id="wf_product_discovery",
        brand_id=settings.brand_id,
        name="Product Discovery Flow",
        description=(
            "Help customers find the perfect wooden toy from our catalog "
            "using AI-powered recommendations"
        ),
        is_template=True,
        status="active",
    )
    product_discovery.agent_sequence = ["support", "response"]
    product_discovery.conditional_edges = {
        "support": {
            "product_query": "response",
            "simple_faq": "response",
        },
        "response": {
            "sufficient": "END",
        },
    }
    product_discovery.loop_config = {"max_iterations": 1, "loop_agents": []}

    return [order_support, product_discovery]


def seed_all() -> None:
    """Seed the database with the full Kreactive Toys demo dataset.

    Initializes schema, then inserts brand, products, agents, workflows
    and orders in a single transaction. Skips seeding if the brand record
    already exists. Rolls back on any exception.
    """
    init_db()

    session_gen = get_db()
    session = next(session_gen)
    try:
        existing = (
            session.query(Brand)
            .filter_by(brand_id=settings.brand_id)
            .first()
        )
        if existing is not None:
            logger.info("Database already seeded — skipping")
            return

        logger.info("Seeding brand: %s", settings.brand_name)
        brand = seed_brand()
        session.add(brand)

        logger.info("Seeding products")
        products = seed_products()
        session.add_all(products)

        logger.info("Seeding agents")
        agents = seed_agents()
        session.add_all(agents)

        logger.info("Seeding workflows")
        workflows = seed_workflows()
        session.add_all(workflows)

        logger.info("Seeding orders")
        orders = seed_orders()
        session.add_all(orders)

        session.commit()

        logger.info(
            "Seed complete: %d products, %d orders, %d agents, %d workflows seeded",
            len(products),
            len(orders),
            len(agents),
            len(workflows),
        )
        # ChromaDB product catalog seeded separately via seed_chroma.py
    except Exception as exc:
        session.rollback()
        logger.error("Seeding failed: %s", exc, exc_info=True)
    finally:
        session.close()


if __name__ == "__main__":
    seed_all()
