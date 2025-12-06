"""
Granular permission system for role-based access control
"""

from enum import Enum
from typing import List, Dict, Set, Optional
from pydantic import BaseModel


class UserRole(str, Enum):
    """User roles in the system"""
    ADMIN = "admin"
    BRANCH_MANAGER = "branch_manager"
    PROCUREMENT_OFFICER = "procurement_officer"
    LOAN_OFFICER = "loan_officer"
    CUSTOMER = "customer"


class PermissionModule(str, Enum):
    """Permission modules"""
    USERS = "users"
    BRANCHES = "branches"
    LOANS = "loans"
    PAYMENTS = "payments"
    INVENTORY = "inventory"
    REPORTS = "reports"
    ADMIN = "admin"
    NOTIFICATIONS = "notifications"


class Permission(BaseModel):
    """Individual permission"""
    name: str
    module: PermissionModule
    description: str


# Define all system permissions
SYSTEM_PERMISSIONS = [
    # User Management
    Permission(name="users:create", module=PermissionModule.USERS, description="Create new users"),
    Permission(name="users:read", module=PermissionModule.USERS, description="View user information"),
    Permission(name="users:update", module=PermissionModule.USERS, description="Update user information"),
    Permission(name="users:delete", module=PermissionModule.USERS, description="Delete users"),
    Permission(name="users:transfer", module=PermissionModule.USERS, description="Transfer users between groups/branches"),
    Permission(name="users:manage_permissions", module=PermissionModule.USERS, description="Manage user permissions"),
    
    # Branch Management
    Permission(name="branches:create", module=PermissionModule.BRANCHES, description="Create new branches"),
    Permission(name="branches:read", module=PermissionModule.BRANCHES, description="View branch information"),
    Permission(name="branches:update", module=PermissionModule.BRANCHES, description="Update branch information"),
    Permission(name="branches:delete", module=PermissionModule.BRANCHES, description="Delete branches"),
    Permission(name="branches:manage_staff", module=PermissionModule.BRANCHES, description="Manage branch staff"),
    
    # Loan Management
    Permission(name="loans:create", module=PermissionModule.LOANS, description="Create loan applications"),
    Permission(name="loans:read", module=PermissionModule.LOANS, description="View loan information"),
    Permission(name="loans:update", module=PermissionModule.LOANS, description="Update loan information"),
    Permission(name="loans:approve", module=PermissionModule.LOANS, description="Approve/reject loans"),
    Permission(name="loans:disburse", module=PermissionModule.LOANS, description="Disburse approved loans"),
    Permission(name="loans:products_manage", module=PermissionModule.LOANS, description="Manage loan products"),
    Permission(name="loans:types_manage", module=PermissionModule.LOANS, description="Manage loan types"),
    
    # Payment Management
    Permission(name="payments:create", module=PermissionModule.PAYMENTS, description="Record payments"),
    Permission(name="payments:confirm", module=PermissionModule.PAYMENTS, description="Confirm payments"),
    Permission(name="payments:view_history", module=PermissionModule.PAYMENTS, description="View payment history"),
    Permission(name="payments:manual_entry", module=PermissionModule.PAYMENTS, description="Manual payment entry"),
    
    # Inventory Management
    Permission(name="inventory:read", module=PermissionModule.INVENTORY, description="View inventory"),
    Permission(name="inventory:update", module=PermissionModule.INVENTORY, description="Update inventory quantities"),
    Permission(name="inventory:restock", module=PermissionModule.INVENTORY, description="Restock products"),
    Permission(name="inventory:transfer", module=PermissionModule.INVENTORY, description="Transfer inventory between branches"),
    
    # Reporting
    Permission(name="reports:view_own", module=PermissionModule.REPORTS, description="View own reports"),
    Permission(name="reports:view_branch", module=PermissionModule.REPORTS, description="View branch reports"),
    Permission(name="reports:view_all", module=PermissionModule.REPORTS, description="View all reports"),
    Permission(name="reports:export", module=PermissionModule.REPORTS, description="Export reports"),
    Permission(name="reports:analytics", module=PermissionModule.REPORTS, description="View analytics dashboards"),
    
    # Admin Functions
    Permission(name="admin:system_settings", module=PermissionModule.ADMIN, description="Manage system settings"),
    Permission(name="admin:view_buying_prices", module=PermissionModule.ADMIN, description="View product buying prices"),
    Permission(name="admin:audit_logs", module=PermissionModule.ADMIN, description="View audit logs"),
    Permission(name="admin:user_sessions", module=PermissionModule.ADMIN, description="View user sessions"),
    Permission(name="admin:backup_restore", module=PermissionModule.ADMIN, description="Backup and restore data"),
    
    # Notifications
    Permission(name="notifications:send_individual", module=PermissionModule.NOTIFICATIONS, description="Send individual notifications"),
    Permission(name="notifications:send_group", module=PermissionModule.NOTIFICATIONS, description="Send group notifications"),
    Permission(name="notifications:send_branch", module=PermissionModule.NOTIFICATIONS, description="Send branch notifications"),
    Permission(name="notifications:send_all", module=PermissionModule.NOTIFICATIONS, description="Send system-wide notifications"),
]


# Default role permissions
DEFAULT_ROLE_PERMISSIONS: Dict[UserRole, Set[str]] = {
    UserRole.ADMIN: {
        # Admin has ALL permissions
        perm.name for perm in SYSTEM_PERMISSIONS
    },
    
    UserRole.BRANCH_MANAGER: {
        "users:read", "users:update", "users:create",
        "branches:read", "branches:update", "branches:manage_staff",
        "loans:read", "loans:update", "loans:products_manage",
        "payments:view_history", "payments:confirm",
        "inventory:read", "inventory:update", "inventory:restock",
        "reports:view_branch", "reports:export", "reports:analytics",
        "notifications:send_individual", "notifications:send_group"
    },
    
    UserRole.PROCUREMENT_OFFICER: {
        "users:read",
        "loans:read", "loans:approve", "loans:disburse",
        "payments:confirm", "payments:view_history",
        "inventory:read", "inventory:update", "inventory:restock",
        "reports:view_own", "reports:analytics",
        "notifications:send_individual"
    },
    
    UserRole.LOAN_OFFICER: {
        "users:read", "users:create", "users:update",  # For their group members only
        "loans:create", "loans:read", "loans:update",  # For their groups only
        "payments:manual_entry", "payments:view_history",
        "reports:view_own",
        "notifications:send_individual"
    },
    
    UserRole.CUSTOMER: {
        "loans:read",  # Own loans only
        "payments:view_history",  # Own payments only
        "reports:view_own"
    }
}


def get_role_permissions(role: UserRole) -> Set[str]:
    """Get default permissions for a role"""
    return DEFAULT_ROLE_PERMISSIONS.get(role, set())


def has_permission(user_permissions: Set[str], required_permission: str) -> bool:
    """Check if user has required permission"""
    return required_permission in user_permissions


def get_permission_by_name(permission_name: str) -> Optional[Permission]:
    """Get permission object by name"""
    for perm in SYSTEM_PERMISSIONS:
        if perm.name == permission_name:
            return perm
    return None


class PermissionChecker:
    """Helper class for checking permissions"""
    
    def __init__(self, user_permissions: Set[str]):
        self.user_permissions = user_permissions
    
    def can_create_users(self) -> bool:
        return has_permission(self.user_permissions, "users:create")
    
    def can_manage_branches(self) -> bool:
        return has_permission(self.user_permissions, "branches:create")
    
    def can_approve_loans(self) -> bool:
        return has_permission(self.user_permissions, "loans:approve")
    
    def can_view_buying_prices(self) -> bool:
        return has_permission(self.user_permissions, "admin:view_buying_prices")
    
    def can_view_all_reports(self) -> bool:
        return has_permission(self.user_permissions, "reports:view_all")
    
    def can_send_system_notifications(self) -> bool:
        return has_permission(self.user_permissions, "notifications:send_all")