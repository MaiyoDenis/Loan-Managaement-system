"""
User management API endpoints
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from datetime import datetime

from app.database import get_db
from app.models.user import User, UserPermission
from app.models.branch import Group, GroupMembership, Branch
from app.models.loan import SavingsAccount, DrawdownAccount
from app.core.security import get_password_hash, generate_unique_account_number
from app.core.permissions import UserRole
from app.core.config import settings
from app.schemas.user import (
    UserCreate, 
    UserUpdate, 
    UserResponse, 
    CustomerCreate,
    UserTransfer,
    OnlineUsersResponse
)
from app.schemas.branch import GroupMemberResponse
from app.api.deps import (
    get_current_active_user,
    require_permission,
    require_admin,
    get_loan_officer_groups_only
)

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    role: Optional[UserRole] = Query(None),
    branch_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None)
) -> Any:
    """
    Get users with filtering and pagination
    """
    query = db.query(User)
    
    # Apply branch filtering based on user role
    if current_user.role != UserRole.ADMIN:
        if current_user.branch_id:
            query = query.filter(User.branch_id == current_user.branch_id)
    elif branch_id:
        query = query.filter(User.branch_id == branch_id)
    
    # Apply role filter
    if role:
        query = query.filter(User.role == role)
    
    # Apply search filter
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
    
    # Apply pagination
    users = query.offset(skip).limit(limit).all()
    
    return users


@router.post("/", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:create"))
) -> Any:
    """
    Create a new user
    """
    # Check if username already exists
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
    
    # Validate branch assignment for non-admin users
    if current_user.role != UserRole.ADMIN:
        if user_data.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create users in your branch"
            )
    
    # Create user
    user = User(
        username=user_data.username,
        phone_number=user_data.phone_number,
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        national_id=user_data.national_id,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
        branch_id=user_data.branch_id,
        must_change_password=user_data.must_change_password
    )
    
    db.add(user)
    db.flush()  # Get user ID
    
    # Generate unique account number for customers
    if user_data.role == UserRole.CUSTOMER:
        user.unique_account_number = generate_unique_account_number(user.id)
        
        # Create savings and drawdown accounts
        savings_account = SavingsAccount(
            user_id=user.id,
            account_number=f"SAV{user.id:06d}",
            registration_fee_amount=settings.DEFAULT_REGISTRATION_FEE
        )
        
        drawdown_account = DrawdownAccount(
            user_id=user.id,
            account_number=f"DRW{user.id:06d}"
        )
        
        db.add(savings_account)
        db.add(drawdown_account)
    
    db.commit()
    db.refresh(user)
    
    # TODO: Send welcome SMS with login credentials
    
    return user


@router.post("/customers", response_model=UserResponse)
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create a customer (by loan officer)
    """
    # Verify loan officer can access this group
    if current_user.role == UserRole.LOAN_OFFICER:
        group = db.query(Group).filter(
            Group.id == customer_data.group_id,
            Group.loan_officer_id == current_user.id
        ).first()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only add customers to your groups"
            )
    
    # Check if group exists and has space
    group = db.query(Group).filter(Group.id == customer_data.group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    if group.current_members >= group.max_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group is full"
        )
    
    # Check if phone number already exists
    existing_user = db.query(User).filter(
        User.phone_number == customer_data.phone_number
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this phone number already exists"
        )
    
    # Generate username from phone number
    username = f"user{customer_data.phone_number[-8:]}"
    
    # Create customer
    customer = User(
        username=username,
        phone_number=customer_data.phone_number,
        first_name=customer_data.first_name,
        last_name=customer_data.last_name,
        national_id=customer_data.national_id,
        password_hash=get_password_hash("123456789"),  # Default password
        role=UserRole.CUSTOMER,
        branch_id=group.branch_id,
        must_change_password=True
    )
    
    db.add(customer)
    db.flush()  # Get customer ID
    
    # Generate unique account number
    customer.unique_account_number = generate_unique_account_number(customer.id)
    
    # Create accounts with registration fee debt
    savings_account = SavingsAccount(
        user_id=customer.id,
        account_number=f"SAV{customer.id:06d}",
        balance=-settings.DEFAULT_REGISTRATION_FEE,  # Start with negative balance
        registration_fee_amount=settings.DEFAULT_REGISTRATION_FEE
    )
    
    drawdown_account = DrawdownAccount(
        user_id=customer.id,
        account_number=f"DRW{customer.id:06d}"
    )
    
    db.add(savings_account)
    db.add(drawdown_account)
    
    # Add to group
    membership = GroupMembership(
        group_id=customer_data.group_id,
        member_id=customer.id,
        joined_at=str(datetime.utcnow())
    )
    db.add(membership)
    
    db.commit()
    db.refresh(customer)
    
    # TODO: Send welcome SMS with login credentials
    
    return customer


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
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
    
    # Check access permissions
    if current_user.role != UserRole.ADMIN:
        if user.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:update"))
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
    
    # Check access permissions
    if current_user.role != UserRole.ADMIN:
        if user.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Update fields
    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/transfer", response_model=UserResponse)
def transfer_user(
    transfer_data: UserTransfer,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users:transfer"))
) -> Any:
    """
    Transfer user between branches/groups (Admin only)
    """
    user = db.query(User).filter(User.id == transfer_data.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update branch if specified
    if transfer_data.new_branch_id:
        branch = db.query(Branch).filter(Branch.id == transfer_data.new_branch_id).first()
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found"
            )
        user.branch_id = transfer_data.new_branch_id
    
    # Update group membership if specified
    if transfer_data.new_group_id:
        group = db.query(Group).filter(Group.id == transfer_data.new_group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )
        
        # Remove from current group
        current_membership = db.query(GroupMembership).filter(
            GroupMembership.member_id == user.id,
            GroupMembership.is_active == True
        ).first()
        
        if current_membership:
            current_membership.is_active = False
        
        # Add to new group
        new_membership = GroupMembership(
            group_id=transfer_data.new_group_id,
            member_id=user.id,
            joined_at=str(datetime.utcnow())
        )
        db.add(new_membership)
    
    db.commit()
    db.refresh(user)
    
    # TODO: Log transfer activity
    
    return user


@router.get("/online/summary", response_model=OnlineUsersResponse)
def get_online_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
) -> Any:
    """
    Get online users summary (Admin only)
    """
    online_users = db.query(User).filter(User.is_online == True).all()
    
    # Group by role
    by_role = {}
    for user in online_users:
        role = user.role.value
        if role not in by_role:
            by_role[role] = 0
        by_role[role] += 1
    
    return {
        "total_online": len(online_users),
        "by_role": by_role,
        "users": online_users
    }


@router.get("/groups/{group_id}/members", response_model=List[GroupMemberResponse])
def get_group_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get members of a specific group
    """
    # Check if user can access this group
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )
    
    # Access control
    if current_user.role == UserRole.LOAN_OFFICER:
        if group.loan_officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your groups"
            )
    elif current_user.role not in [UserRole.ADMIN, UserRole.BRANCH_MANAGER, UserRole.PROCUREMENT_OFFICER]:
        if group.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Get group members with additional data
    memberships = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.is_active == True
    ).options(joinedload(GroupMembership.member)).all()
    
    members_data = []
    for membership in memberships:
        member = membership.member
        
        # Get savings balance
        savings_balance = 0.0
        if member.savings_account:
            savings_balance = float(member.savings_account.balance)
        
        # Get active loans count
        active_loans = len([loan for loan in member.loans if loan.status == "active"])
        
        member_data = GroupMemberResponse(
            id=member.id,
            username=member.username,
            first_name=member.first_name,
            last_name=member.last_name,
            phone_number=member.phone_number,
            role=membership.role,
            joined_at=membership.created_at,
            savings_balance=savings_balance,
            active_loans=active_loans
        )
        members_data.append(member_data)
    
    return members_data