from enum import Enum


class AgentMode(str, Enum):
    RE_ACT = "ReAct"
    PLAN = "plan-and-exectute"
