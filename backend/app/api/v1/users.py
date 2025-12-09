"""
User management API endpoints
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import User, Role, Group, GroupMembership, SavingsAccount, DrawdownAccount
from app.schemas.user import UserCreate, UserUpdate, UserResponse, CustomerCreate
from app.core.security import get_password_hash, generate_unique_account_number
from app.core.config import settings
from app.api.deps import get_current_active_user, require_permission

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    role: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("user_view"))
) -> Any:
    """
    Get users with filtering and pagination
    """
    query = db.query(User)
    
    if branch_id:
        query = query.filter(User.branch_id == branch_id)
    
    if role:
        query = query.join(Role).filter(Role.name == role)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.phone_number.ilike(search_term)
            )
        )
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user_create"))
) -> Any:
    """
    Create a new user
    """
    existing_user = db.query(User).filter(
        or_(
            User.username == user_data.username,
            User.phone_number == user_data.phone_number,
            User.email == user_data.email if user_data.email else False
        )
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this username, phone, or email already exists"
        )
    
    role = db.query(Role).filter(Role.id == user_data.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role ID"
        )

    user = User(**user_data.dict(), password_hash=get_password_hash(user_data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/customers", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("customer_create"))
) -> Any:
    """
    Create a new customer and add them to a group
    """
    group = db.query(Group).filter(Group.id == customer_data.group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    customer_role = db.query(Role).filter(Role.name == "customer").first()
    if not customer_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Customer role not found"
        )

    username = f"user_{customer_data.phone_number}"
    password = "password123" #  A more secure password should be generated

    user = User(
        username=username,
        phone_number=customer_data.phone_number,
        first_name=customer_data.first_name,
        last_name=customer_data.last_name,
        national_id=customer_data.national_id,
        password_hash=get_password_hash(password),
        role_id=customer_role.id,
        branch_id=group.branch_id,
    )
    db.add(user)
    db.flush()

    savings_account = SavingsAccount(
        user_id=user.id,
        balance=-settings.DEFAULT_REGISTRATION_FEE,
    )
    drawdown_account = DrawdownAccount(user_id=user.id)
    group_membership = GroupMembership(
        group_id=group.id,
        member_id=user.id,
    )
    db.add_all([savings_account, drawdown_account, group_membership])

    db.commit()
    db.refresh(user)
    return user


@router.get("/staff-for-assignment", response_model=List[UserResponse])
def get_staff_for_assignment(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("branch_update"))
) -> Any:
    """
    Get users with 'branch_manager' or 'procurement_officer' roles
    for assignment to a branch.
    """
    roles = db.query(Role).filter(
        or_(
            Role.name == "branch_manager",
            Role.name == "procurement_officer"
        )
    ).all()
    
    if not roles:
        return []

    role_ids = [role.id for role in roles]
    users = db.query(User).filter(User.role_id.in_(role_ids)).all()
    return users


@router.get("/groups/{group_id}/members", response_model=List[UserResponse])
def get_group_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("group_view"))
) -> Any:
    """
    Get members of a specific group
    """
    members = db.query(User).join(GroupMembership).filter(GroupMembership.group_id == group_id).all()
    return members


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user_view"))
) -> Any:
    """
    Get user by ID
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("user_update"))
) -> Any:
    """
    Update user information
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user
