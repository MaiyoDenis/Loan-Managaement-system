"""
Branch management API endpoints
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.branch import Branch, Group
from app.models.user import User
from app.core.permissions import UserRole
from app.schemas.branch import (
    BranchCreate,
    BranchUpdate,
    BranchResponse,
    GroupCreate,
    GroupUpdate,
    GroupResponse
)
from app.api.deps import (
    get_current_active_user,
    require_permission,
    require_admin
)

router = APIRouter()


@router.get("/", response_model=List[BranchResponse])
def get_branches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None)
) -> Any:
    """
    Get branches with filtering and pagination
    """
    query = db.query(Branch)

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Branch.name.ilike(search_term)) |
            (Branch.location.ilike(search_term)) |
            (Branch.code.ilike(search_term))
        )

    # Apply pagination
    branches = query.offset(skip).limit(limit).all()

    return branches


@router.post("/", response_model=BranchResponse)
def create_branch(
    branch_data: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
) -> Any:
    """
    Create a new branch (Admin only)
    """
    # Check if branch code already exists
    existing_branch = db.query(Branch).filter(
        (Branch.code == branch_data.code) |
        (Branch.name == branch_data.name)
    ).first()

    if existing_branch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Branch with this code or name already exists"
        )

    # Create branch
    branch = Branch(
        name=branch_data.name,
        code=branch_data.code,
        location=branch_data.location,
        phone_number=branch_data.phone_number,
        email=branch_data.email,
        manager_id=branch_data.manager_id
    )

    db.add(branch)
    db.commit()
    db.refresh(branch)

    return branch


@router.get("/{branch_id}", response_model=BranchResponse)
def get_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get branch by ID
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()

    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )

    # Check access permissions
    if current_user.role != UserRole.ADMIN:
        if current_user.branch_id != branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    return branch


@router.put("/{branch_id}", response_model=BranchResponse)
def update_branch(
    branch_id: int,
    branch_data: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
) -> Any:
    """
    Update branch information (Admin only)
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()

    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )

    # Update fields
    update_data = branch_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(branch, field, value)

    db.commit()
    db.refresh(branch)

    return branch


@router.delete("/{branch_id}")
def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
) -> Any:
    """
    Delete branch (Admin only)
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()

    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )

    # Check if branch has users
    users_count = db.query(User).filter(User.branch_id == branch_id).count()
    if users_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete branch with active users"
        )

    # Delete branch
    db.delete(branch)
    db.commit()

    return {"message": "Branch deleted successfully"}


# Group management endpoints

@router.get("/{branch_id}/groups", response_model=List[GroupResponse])
def get_branch_groups(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """
    Get groups in a branch
    """
    # Check branch access
    if current_user.role != UserRole.ADMIN:
        if current_user.branch_id != branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    groups = db.query(Group).filter(Group.branch_id == branch_id).offset(skip).limit(limit).all()

    return groups


@router.post("/{branch_id}/groups", response_model=GroupResponse)
def create_group(
    branch_id: int,
    group_data: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create a new group in a branch
    """
    # Check branch access
    if current_user.role != UserRole.ADMIN:
        if current_user.branch_id != branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    # Verify loan officer belongs to the branch
    if group_data.loan_officer_id:
        loan_officer = db.query(User).filter(
            User.id == group_data.loan_officer_id,
            User.branch_id == branch_id,
            User.role == UserRole.LOAN_OFFICER
        ).first()

        if not loan_officer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid loan officer for this branch"
            )

    # Create group
    group = Group(
        name=group_data.name,
        branch_id=branch_id,
        loan_officer_id=group_data.loan_officer_id,
        max_members=group_data.max_members,
        meeting_day=group_data.meeting_day,
        meeting_time=group_data.meeting_time,
        meeting_location=group_data.meeting_location
    )

    db.add(group)
    db.commit()
    db.refresh(group)

    return group


@router.get("/groups/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get group by ID
    """
    group = db.query(Group).filter(Group.id == group_id).first()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Check access permissions
    if current_user.role == UserRole.LOAN_OFFICER:
        if group.loan_officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role != UserRole.ADMIN:
        if group.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    return group


@router.put("/groups/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    group_data: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update group information
    """
    group = db.query(Group).filter(Group.id == group_id).first()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Check access permissions
    if current_user.role == UserRole.LOAN_OFFICER:
        if group.loan_officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role != UserRole.ADMIN:
        if group.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    # Update fields
    update_data = group_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)

    db.commit()
    db.refresh(group)

    return group


@router.delete("/groups/{group_id}")
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Delete group
    """
    group = db.query(Group).filter(Group.id == group_id).first()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    # Check access permissions
    if current_user.role == UserRole.LOAN_OFFICER:
        if group.loan_officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role != UserRole.ADMIN:
        if group.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    # Check if group has active members
    if group.current_members > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete group with active members"
        )

    # Delete group
    db.delete(group)
    db.commit()

    return {"message": "Group deleted successfully"}
