"""
Group management API endpoints
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.branch import Group
from app.models.user import User
from app.schemas.group import GroupCreate, GroupUpdate, GroupResponse
from app.api.deps import get_current_active_user, require_permission

router = APIRouter()


@router.get("/", response_model=List[GroupResponse])
def get_groups(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("group_view"))
) -> Any:
    """
    Get groups with filtering and pagination
    """
    query = db.query(Group)

    if search:
        search_term = f"%{search}%"
        query = query.filter(Group.name.ilike(search_term))

    groups = query.offset(skip).limit(limit).all()
    return groups


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    group_data: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("group_create"))
) -> Any:
    """
    Create a new group
    """
    existing_group = db.query(Group).filter(Group.name == group_data.name).first()

    if existing_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group with this name already exists"
        )

    group = Group(**group_data.dict())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("group_view"))
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
    return group


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    group_data: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("group_update"))
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

    update_data = group_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)

    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("group_delete"))
) -> None:
    """
    Delete group
    """
    group = db.query(Group).filter(Group.id == group_id).first()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found"
        )

    db.delete(group)
    db.commit()
