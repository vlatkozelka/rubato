from enum import Enum


class UserRole(str, Enum):
    STAFF = "staff"
    CUSTOMER = "customer"
