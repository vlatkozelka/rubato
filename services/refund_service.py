import logging
import uuid
from datetime import datetime
from typing import Optional

from models.approval import Approval, ApprovalPayload, ApprovalStatus, ApprovalType
from models.order import Order
from models.order_status import DeliveredStatus
from services.order_service import get_order_by_id
from services.policy_service import get_refund_policy
from services.product_service import get_product_by_id

logger = logging.getLogger("rubato.services.refund_service")


def check_refund(order_id: str, product_id: str, customer_id: str, reason: str) -> Optional[Approval]:
    logger.log(level=logging.INFO, msg=f"checkRefund called: order_id = {order_id}, customer_id = {customer_id} ")
    now_string = datetime.now().isoformat()
    order: Optional[Order]
    order = get_order_by_id(order_id)
    if order is not None and order.customer_id == customer_id:
        # check order status
        if not isinstance(order.status, DeliveredStatus):
            return Approval(
                id=uuid.uuid4(),
                reason=reason,
                payload=ApprovalPayload(
                    order_id=order_id,
                    reason="Order not yet delivered"
                ),
                status=ApprovalStatus.DENIED,
                created_at=now_string,
                updated_at=now_string,
                type=ApprovalType.REFUND_REQUEST
            )
        for item in order.items:
            if item.product_id == product_id:
                product = get_product_by_id(product_id)
                if product is not None:
                    # check the policy
                    category = product.category
                    delivered_at = datetime.fromisoformat(order.status.delivered_at)
                    elapsed = datetime.now() - delivered_at
                    days_since_delivery = elapsed.days
                    refund_policy = get_refund_policy(category)
                    if refund_policy.allowed_duration > days_since_delivery:
                        return Approval(
                            id=uuid.uuid4(),
                            reason=reason,
                            payload=ApprovalPayload(
                                order_id=order_id,
                                reason=f"Order was delivered since {days_since_delivery} days from this request which is less than {refund_policy.allowed_duration} days as mentioned for the refund policy for items of category: {category} "
                            ),
                            status=ApprovalStatus.PENDING_REVIEW,
                            created_at=now_string,
                            updated_at=now_string,
                            type=ApprovalType.REFUND_REQUEST
                        )
                    else:
                        return Approval(
                            id=uuid.uuid4(),
                            reason=reason,
                            payload=ApprovalPayload(
                                order_id=order_id,
                                reason=f"Order was delivered since {days_since_delivery} days from this request which is more than {refund_policy.allowed_duration} days as mentioned for the refund policy for items of category: {category} "
                            ),
                            status=ApprovalStatus.DENIED,
                            created_at=now_string,
                            updated_at=now_string,
                            type=ApprovalType.REFUND_REQUEST
                        )

                else:
                    return None
    return None


if __name__ == "__main__":
    result = check_refund("ord_1001", "prod_004", "cust_001", "broken")
    print(result)