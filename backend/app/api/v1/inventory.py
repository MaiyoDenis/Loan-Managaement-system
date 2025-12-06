"""
Branch Inventory Management API endpoints
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
from datetime import date

from app.database import get_db
from app.models.loan import BranchInventory, LoanProduct, StockMovement
from app.models.user import User
from app.models.branch import Branch
from app.core.permissions import UserRole
from app.schemas.loan import (
    BranchInventoryResponse,
    BranchInventoryUpdate,
    StockMovementCreate,
    StockMovementResponse,
    InventoryStatsResponse,
    RestockRequest
)
from app.api.deps import (
    get_current_active_user,
    require_permission,
    validate_branch_access
)

router = APIRouter()


@router.get("/", response_model=List[BranchInventoryResponse])
def get_branch_inventory(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    branch_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, regex="^(ok|low|critical)$"),
    product_name: Optional[str] = Query(None)
) -> Any:
    """Get branch inventory with filtering"""
    # Determine target branch
    target_branch_id = branch_id
    if current_user.role != UserRole.ADMIN:
        target_branch_id = current_user.branch_id
    elif branch_id:
        validate_branch_access(branch_id, current_user)
    
    query = db.query(BranchInventory).options(
        joinedload(BranchInventory.loan_product),
        joinedload(BranchInventory.branch)
    )
    
    if target_branch_id:
        query = query.filter(BranchInventory.branch_id == target_branch_id)
    
    # Apply product name filter
    if product_name:
        query = query.join(LoanProduct).filter(
            LoanProduct.name.ilike(f"%{product_name}%")
        )
    
    inventory_items = query.all()
    
    # Apply status filter after fetching (since it's a computed property)
    if status_filter:
        inventory_items = [item for item in inventory_items if item.status == status_filter]
    
    return inventory_items


@router.get("/branch/{branch_id}", response_model=List[BranchInventoryResponse])
def get_specific_branch_inventory(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get inventory for a specific branch"""
    # Validate access
    if current_user.role != UserRole.ADMIN:
        if current_user.branch_id != branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this branch inventory"
            )
    
    inventory = db.query(BranchInventory).options(
        joinedload(BranchInventory.loan_product),
        joinedload(BranchInventory.branch)
    ).filter(BranchInventory.branch_id == branch_id).all()
    
    return inventory


@router.post("/", response_model=BranchInventoryResponse)
def create_inventory_item(
    product_id: int,
    branch_id: int,
    initial_quantity: int,
    reorder_point: Optional[int] = 5,
    critical_point: Optional[int] = 2,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventory:update"))
) -> Any:
    """Create new inventory item for branch"""
    # Validate branch access
    if current_user.role != UserRole.ADMIN:
        if current_user.branch_id != branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this branch"
            )
    
    # Check if inventory item already exists
    existing_item = db.query(BranchInventory).filter(
        BranchInventory.branch_id == branch_id,
        BranchInventory.loan_product_id == product_id
    ).first()
    
    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventory item already exists for this product in this branch"
        )
    
    # Verify product exists
    product = db.query(LoanProduct).filter(LoanProduct.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Create inventory item
    inventory_item = BranchInventory(
        branch_id=branch_id,
        loan_product_id=product_id,
        current_quantity=initial_quantity,
        reorder_point=reorder_point,
        critical_point=critical_point,
        last_restocked_at=date.today(),
        last_restocked_by=current_user.id
    )
    
    db.add(inventory_item)
    
    # Create initial stock movement
    if initial_quantity > 0:
        stock_movement = StockMovement(
            branch_id=branch_id,
            loan_product_id=product_id,
            movement_type="restock",
            quantity_change=initial_quantity,
            previous_quantity=0,
            new_quantity=initial_quantity,
            reason="Initial stock",
            created_by=current_user.id
        )
        db.add(stock_movement)
    
    db.commit()
    db.refresh(inventory_item)
    
    return inventory_item


@router.put("/{inventory_id}", response_model=BranchInventoryResponse)
def update_inventory_item(
    inventory_id: int,
    inventory_data: BranchInventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventory:update"))
) -> Any:
    """Update inventory item"""
    inventory_item = db.query(BranchInventory).filter(
        BranchInventory.id == inventory_id
    ).first()
    
    if not inventory_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    # Validate branch access
    if current_user.role != UserRole.ADMIN:
        if current_user.branch_id != inventory_item.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this branch inventory"
            )
    
    # Track quantity changes
    old_quantity = inventory_item.current_quantity
    
    # Update fields
    update_data = inventory_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(inventory_item, field, value)
    
    # Create stock movement if quantity changed
    if 'current_quantity' in update_data:
        new_quantity = update_data['current_quantity']
        quantity_change = new_quantity - old_quantity
        
        if quantity_change != 0:
            movement_type = "restock" if quantity_change > 0 else "adjustment"
            
            stock_movement = StockMovement(
                branch_id=inventory_item.branch_id,
                loan_product_id=inventory_item.loan_product_id,
                movement_type=movement_type,
                quantity_change=quantity_change,
                previous_quantity=old_quantity,
                new_quantity=new_quantity,
                reason=inventory_data.reason or "Manual adjustment",
                created_by=current_user.id
            )
            db.add(stock_movement)
            
            # Update restock info if it's a restock
            if movement_type == "restock":
                inventory_item.last_restocked_at = date.today()
                inventory_item.last_restocked_by = current_user.id
    
    db.commit()
    db.refresh(inventory_item)
    
    return inventory_item


@router.post("/restock", response_model=BranchInventoryResponse)
def restock_product(
    restock_data: RestockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventory:restock"))
) -> Any:
    """Restock a product in branch inventory"""
    inventory_item = db.query(BranchInventory).filter(
        BranchInventory.branch_id == restock_data.branch_id,
        BranchInventory.loan_product_id == restock_data.product_id
    ).first()
    
    if not inventory_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    # Validate branch access
    if current_user.role != UserRole.ADMIN:
        if current_user.branch_id != restock_data.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this branch"
            )
    
    # Update quantity
    old_quantity = inventory_item.current_quantity
    new_quantity = old_quantity + restock_data.quantity
    
    inventory_item.current_quantity = new_quantity
    inventory_item.last_restocked_at = date.today()
    inventory_item.last_restocked_by = current_user.id
    
    # Create stock movement record
    stock_movement = StockMovement(
        branch_id=restock_data.branch_id,
        loan_product_id=restock_data.product_id,
        movement_type="restock",
        quantity_change=restock_data.quantity,
        previous_quantity=old_quantity,
        new_quantity=new_quantity,
        reason=restock_data.reason or "Product restocked",
        created_by=current_user.id
    )
    
    db.add(stock_movement)
    db.commit()
    db.refresh(inventory_item)
    
    return inventory_item


@router.get("/movements", response_model=List[StockMovementResponse])
def get_stock_movements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    branch_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    movement_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """Get stock movement history"""
    query = db.query(StockMovement).options(
        joinedload(StockMovement.loan_product),
        joinedload(StockMovement.branch),
        joinedload(StockMovement.created_by_user)
    )
    
    # Apply branch filtering
    if current_user.role != UserRole.ADMIN:
        query = query.filter(StockMovement.branch_id == current_user.branch_id)
    elif branch_id:
        query = query.filter(StockMovement.branch_id == branch_id)
    
    # Apply additional filters
    if product_id:
        query = query.filter(StockMovement.loan_product_id == product_id)
    
    if movement_type:
        query = query.filter(StockMovement.movement_type == movement_type)
    
    # Order by most recent first
    movements = query.order_by(StockMovement.created_at.desc()).offset(skip).limit(limit).all()
    
    return movements


@router.get("/stats", response_model=InventoryStatsResponse)
def get_inventory_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    branch_id: Optional[int] = Query(None)
) -> Any:
    """Get inventory statistics"""
    # Determine target branch
    target_branch_id = branch_id
    if current_user.role != UserRole.ADMIN:
        target_branch_id = current_user.branch_id
    elif branch_id:
        validate_branch_access(branch_id, current_user)
    
    query = db.query(BranchInventory)
    if target_branch_id:
        query = query.filter(BranchInventory.branch_id == target_branch_id)
    
    inventory_items = query.all()
    
    # Calculate stats
    total_products = len(inventory_items)
    total_quantity = sum(item.current_quantity for item in inventory_items)
    
    # Count by status
    status_counts = {"ok": 0, "low": 0, "critical": 0, "out_of_stock": 0}
    for item in inventory_items:
        if item.current_quantity == 0:
            status_counts["out_of_stock"] += 1
        else:
            status_counts[item.status] += 1
    
    # Calculate total value (admin only)
    total_value = 0.0
    if current_user.role == UserRole.ADMIN:
        for item in inventory_items:
            if item.loan_product:
                total_value += float(item.loan_product.buying_price * item.current_quantity)
    
    return InventoryStatsResponse(
        total_products=total_products,
        total_quantity=total_quantity,
        total_value=total_value if current_user.role == UserRole.ADMIN else None,
        low_stock_items=status_counts["low"],
        critical_stock_items=status_counts["critical"],
        out_of_stock_items=status_counts["out_of_stock"],
        status_breakdown=status_counts
    )


@router.get("/alerts")
def get_inventory_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    branch_id: Optional[int] = Query(None)
) -> Any:
    """Get inventory alerts for low/critical stock"""
    # Determine target branch
    target_branch_id = branch_id
    if current_user.role != UserRole.ADMIN:
        target_branch_id = current_user.branch_id
    
    query = db.query(BranchInventory).options(
        joinedload(BranchInventory.loan_product),
        joinedload(BranchInventory.branch)
    )
    
    if target_branch_id:
        query = query.filter(BranchInventory.branch_id == target_branch_id)
    
    inventory_items = query.all()
    
    alerts = []
    for item in inventory_items:
        if item.current_quantity <= item.critical_point:
            alerts.append({
                "type": "critical",
                "priority": "high",
                "branch_id": item.branch_id,
                "branch_name": item.branch.name,
                "product_id": item.loan_product_id,
                "product_name": item.loan_product.name,
                "current_quantity": item.current_quantity,
                "critical_point": item.critical_point,
                "reorder_point": item.reorder_point,
                "message": f"CRITICAL: {item.loan_product.name} has only {item.current_quantity} units left!"
            })
        elif item.current_quantity <= item.reorder_point:
            alerts.append({
                "type": "low_stock",
                "priority": "medium",
                "branch_id": item.branch_id,
                "branch_name": item.branch.name,
                "product_id": item.loan_product_id,
                "product_name": item.loan_product.name,
                "current_quantity": item.current_quantity,
                "critical_point": item.critical_point,
                "reorder_point": item.reorder_point,
                "message": f"LOW STOCK: {item.loan_product.name} needs restocking ({item.current_quantity} units)"
            })
    
    # Sort by priority (critical first)
    alerts.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["priority"]])
    
    return {
        "alerts": alerts,
        "total_alerts": len(alerts),
        "critical_count": len([a for a in alerts if a["type"] == "critical"]),
        "low_stock_count": len([a for a in alerts if a["type"] == "low_stock"])
    }