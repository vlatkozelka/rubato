import logging

logger = logging.getLogger("rubato.services.refund_execution")


def execute_refund(order_id: str, amount: float) -> None:
    # Stub — a real payment gateway integration (Stripe, etc.) would go here.
    logger.info(
        "refund_executed",
        extra={"event": "refund_executed", "order_id": order_id, "amount": amount},
    )
    print(f"REFUND EXECUTED: order {order_id}, amount ${amount:.2f}")
