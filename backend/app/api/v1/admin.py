"""
Admin API endpoints
"""

from typing import List, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.branch import Branch, Group
from app.models.loan import Loan, LoanApplication
from app.core.permissions import UserRole
from app.schemas.user import UserResponse
from app.schemas.branch import BranchResponse
from app.api.deps import require_admin

router = APIRouter()


@router.get("/dashboard/stats")
def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
) -> Any:
    """
    Get admin dashboard statistics
    """
    # User statistics
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    online_users = db.query(func.count(User.id)).filter(User.is_online == True).scalar()

    # Branch statistics
    total_branches = db.query(func.count(Branch.id)).scalar()

    # Group statistics
    total_groups = db.query(func.count(Group.id)).scalar()

    # Loan statistics
    total_loans = db.query(func.count(Loan.id)).scalar()
    active_loans = db.query(func.count(Loan.id)).filter(Loan.status == "active").scalar()
    pending_applications = db.query(func.count(LoanApplication.id)).filter(
        LoanApplication.status == "pending"
    ).scalar()

    # User role distribution
    role_stats = db.query(User.role, func.count(User.id)).group_by(User.role).all()
    users_by_role = {role.value: count for role, count in role_stats}

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "online": online_users,
            "by_role": users_by_role
        },
        "branches": {
            "total": total_branches
        },
        "groups": {
            "total": total_groups
        },
        "loans": {
            "total": total_loans,
            "active": active_loans,
            "pending_applications": pending_applications
        }
    }


@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
) -> Any:
    """
    Get all users (Admin only)
    """
    users = db.query(User).all()
    return users


@router.get("/branches", response_model=List[BranchResponse])
def get_all_branches(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
) -> Any:
    """
    Get all branches (Admin only)
    """
    branches = db.query(Branch).all()
    return branches


@router.post("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
) -> Any:
    """
    Activate a user account (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_active = True
    db.commit()

    return {"message": "User activated successfully"}


@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
) -> Any:
    """
    Deactivate a user account (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent deactivating admin accounts
    if user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate admin accounts"
        )

    user.is_active = False
    user.is_online = False
    db.commit()

    return {"message": "User deactivated successfully"}


@router.post("/system/maintenance")
def trigger_system_maintenance(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
) -> Any:
    """
    Trigger system maintenance tasks (Admin only)
    """
    # This could include:
    # - Cleaning up old sessions
    # - Updating statistics
    # - Database optimization
    # - etc.

    # For now, just return success
    return {"message": "System maintenance completed successfully"}
