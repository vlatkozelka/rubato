from enum import Enum


class Intent(str, Enum):
    ORDER_STATUS = "order_status"
    POLICY_QUESTION = "policy_question"
    RETURN_REQUEST = "return_request"
    REFUND_REQUEST = "refund_request"
    PRICE_CHECK = "price_check"
    ESCALATE = "escalate"
    CHITCHAT = "chitchat"
    COMPOSITE = "composite"
    COMPLEX_CASE = "complex_case"
