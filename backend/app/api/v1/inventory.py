"""
Inventory management API endpoints
"""

from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BranchInventory, User
from app.schemas.loan import BranchInventoryCreate, BranchInventoryUpdate, BranchInventoryResponse
from app.api.deps import get_current_active_user, require_permission

router = APIRouter()


@router.get("/{branch_id}", response_model=List[BranchInventoryResponse])
def get_branch_inventory(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventory_view"))
) -> Any:
    """
    Get inventory for a specific branch
    """
    inventory = db.query(BranchInventory).filter(BranchInventory.branch_id == branch_id).all()
    return inventory


@router.put("/{inventory_id}", response_model=BranchInventoryResponse)
def update_branch_inventory(
    inventory_id: int,
    inventory_data: BranchInventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventory_update"))
) -> Any:
    """
    Update inventory for a specific branch
    """
    inventory = db.query(BranchInventory).filter(BranchInventory.id == inventory_id).first()
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )

    update_data = inventory_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(inventory, field, value)
        
    db.commit()
    db.refresh(inventory)
    return inventory
