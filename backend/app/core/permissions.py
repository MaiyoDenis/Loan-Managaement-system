"""
Role and permission definitions used across the application.
"""
from enum import Enum
from typing import Final


class UserRole(str, Enum):
    ADMIN = "admin"
    BRANCH_MANAGER = "branch_manager"
    LOAN_OFFICER = "loan_officer"
    PROCUREMENT_OFFICER = "procurement_officer"
    CUSTOMER = "customer"
    STAFF = "staff"


# Permission strings (centralized to avoid typos). These align with deps.require_permission usage.
# You can expand these as needed to seed and enforce via Role/Permission tables.
PERM_PAYMENTS_VIEW_HISTORY: Final[str] = "payments:view_history"
PERM_PAYMENTS_MANUAL_ENTRY: Final[str] = "payments:manual_entry"
PERM_PAYMENTS_CONFIRM: Final[str] = "payments:confirm"
PERM_ADMIN_SYSTEM_SETTINGS: Final[str] = "admin:system_settings"
PERM_BRANCH_VIEW: Final[str] = "branches:view"
PERM_USERS_MANAGE: Final[str] = "users:manage"
