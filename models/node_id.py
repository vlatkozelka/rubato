from enum import Enum


class NodeId(str, Enum):
    GUARDRAIL_IN = "guardrail_in"
    TRIAGE = "triage"
    CHECK_ORDER_STATUS = "check_order_status"
    ANSWER_POLICY_QUESTION = "answer_policy_question"
    HANDLE_RETURN_REQUEST = "handle_return_request"
    HANDLE_REFUND_REQUEST = "handle_refund_request"
    CHECK_PRICE = "check_price"
    ASSIGN_TO_HUMAN = "assign_to_human"
    GREET = "greet"
    PROCESS_COMPLEX_CASE = "process_complex_case"
    AGENT_GROUNDING = "agent_grounding"
