"""
Branch management API endpoints
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Branch, User
from app.schemas.branch import BranchCreate, BranchUpdate, BranchResponse
from app.api.deps import get_current_active_user, require_permission

router = APIRouter()


@router.get("/", response_model=List[BranchResponse])
def get_branches(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_permission("branch_view"))
) -> Any:
    """
    Get branches with filtering and pagination
    """
    query = db.query(Branch)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Branch.name.ilike(search_term)) |
            (Branch.code.ilike(search_term))
        )

    branches = query.offset(skip).limit(limit).all()
    return branches


@router.post("/", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
def create_branch(
    branch_data: BranchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("branch_create"))
) -> Any:
    """
    Create a new branch
    """
    existing_branch = db.query(Branch).filter(
        (Branch.code == branch_data.code) |
        (Branch.name == branch_data.name)
    ).first()

    if existing_branch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Branch with this code or name already exists"
        )

    branch = Branch(**branch_data.dict())
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


@router.get("/{branch_id}", response_model=BranchResponse)
def get_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("branch_view"))
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
    return branch


@router.put("/{branch_id}", response_model=BranchResponse)
def update_branch(
    branch_id: int,
    branch_data: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("branch_update"))
) -> Any:
    """
    Update branch information
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()

    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )

    update_data = branch_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(branch, field, value)

    db.commit()
    db.refresh(branch)
    return branch


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("branch_delete"))
) -> Any:
    """
    Delete branch
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()

    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )

    if db.query(User).filter(User.branch_id == branch_id).count() > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete branch with assigned users"
        )

    db.delete(branch)
    db.commit()
