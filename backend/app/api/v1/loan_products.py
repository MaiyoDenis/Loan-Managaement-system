"""
Loan Products and Categories API endpoints
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from decimal import Decimal
import uuid
import os

from app.database import get_db
from app.models.loan import LoanProduct, ProductCategory, BranchInventory
from app.models.user import User
from app.core.permissions import UserRole
from app.schemas.loan import (
    LoanProductCreate,
    LoanProductUpdate, 
    LoanProductResponse,
    ProductCategoryCreate,
    ProductCategoryResponse,
    BranchInventoryResponse
)
from app.api.deps import (
    get_current_active_user,
    require_permission,
    require_admin
)

router = APIRouter()


@router.get("/categories", response_model=List[ProductCategoryResponse])
def get_product_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """Get all product categories"""
    categories = db.query(ProductCategory).filter(
        ProductCategory.is_active == True
    ).offset(skip).limit(limit).all()
    
    return categories


@router.post("/categories", response_model=ProductCategoryResponse)
def create_product_category(
    category_data: ProductCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("loans:products_manage"))
) -> Any:
    """Create a new product category"""
    # Check if category name exists
    existing_category = db.query(ProductCategory).filter(
        ProductCategory.name == category_data.name,
        ProductCategory.is_active == True
    ).first()
    
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    category = ProductCategory(
        name=category_data.name,
        description=category_data.description,
        created_by=current_user.id
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return category


@router.get("/", response_model=List[LoanProductResponse])
def get_loan_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None)
) -> Any:
    """
    Get loan products with filtering
    """
    query = db.query(LoanProduct).options(
        joinedload(LoanProduct.category)
    ).filter(LoanProduct.is_active == True)
    
    # Apply category filter
    if category_id:
        query = query.filter(LoanProduct.category_id == category_id)
    
    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                LoanProduct.name.ilike(search_term),
                LoanProduct.description.ilike(search_term)
            )
        )
    
    products = query.offset(skip).limit(limit).all()
    
    # For non-admin users, hide buying prices
    response_products = []
    for product in products:
        product_data = LoanProductResponse.from_orm(product)
        
        # Hide buying price from non-admin users
        if not current_user or current_user.role != UserRole.ADMIN:
            product_data.buying_price = None  # Secret information
        
        # Add inventory information if branch_id provided
        if branch_id:
            inventory = db.query(BranchInventory).filter(
                BranchInventory.branch_id == branch_id,
                BranchInventory.loan_product_id == product.id
            ).first()
            
            if inventory:
                product_data.current_quantity = inventory.current_quantity
                product_data.inventory_status = inventory.status
        
        response_products.append(product_data)
    
    return response_products


@router.post("/", response_model=LoanProductResponse)
async def create_loan_product(
    name: str,
    category_id: int,
    buying_price: Decimal,
    selling_price: Decimal,
    description: Optional[str] = None,
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("loans:products_manage"))
) -> Any:
    """Create a new loan product"""
    # Validate category exists
    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Validate prices
    if buying_price >= selling_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selling price must be higher than buying price"
        )
    
    # Handle image upload
    image_url = None
    if image:
        # Create uploads directory if not exists
        upload_dir = "uploads/products"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        file_extension = image.filename.split('.')[-1] if image.filename else 'jpg'
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(upload_dir, filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await image.read()
            buffer.write(content)
        
        image_url = f"/uploads/products/{filename}"
    
    # Create product
    product = LoanProduct(
        name=name,
        category_id=category_id,
        description=description,
        buying_price=buying_price,
        selling_price=selling_price,
        image_url=image_url,
        created_by=current_user.id
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return product


@router.put("/{product_id}", response_model=LoanProductResponse)
def update_loan_product(
    product_id: int,
    product_data: LoanProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("loans:products_manage"))
) -> Any:
    """Update loan product"""
    product = db.query(LoanProduct).filter(LoanProduct.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Update fields
    update_data = product_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    # Validate prices if both are provided
    if hasattr(product, 'buying_price') and hasattr(product, 'selling_price'):
        if product.buying_price >= product.selling_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selling price must be higher than buying price"
            )
    
    db.commit()
    db.refresh(product)
    
    return product


@router.delete("/{product_id}")
def delete_loan_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("loans:products_manage"))
) -> Any:
    """Soft delete loan product"""
    product = db.query(LoanProduct).filter(LoanProduct.id == product_id).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    product.is_active = False
    db.commit()
    
    return {"message": "Product deleted successfully"}


@router.get("/{product_id}/inventory", response_model=List[BranchInventoryResponse])
def get_product_inventory(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("inventory:read"))
) -> Any:
    """Get inventory levels for a product across all branches"""
    # Admin can see all branches, others only their branch
    query = db.query(BranchInventory).options(
        joinedload(BranchInventory.branch)
    ).filter(BranchInventory.loan_product_id == product_id)
    
    if current_user.role != UserRole.ADMIN:
        query = query.filter(BranchInventory.branch_id == current_user.branch_id)
    
    inventory_items = query.all()
    
    return inventory_items


@router.get("/analytics/profit-margins")
def get_profit_margins(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin())
) -> Any:
    """Get profit margin analysis (Admin only)"""
    products = db.query(LoanProduct).filter(LoanProduct.is_active == True).all()
    
    analytics = []
    total_profit_potential = 0
    
    for product in products:
        profit_amount = product.selling_price - product.buying_price
        profit_margin = product.profit_margin
        
        # Get total inventory across all branches
        total_inventory = db.query(BranchInventory).filter(
            BranchInventory.loan_product_id == product.id
        ).with_entities(
            db.func.sum(BranchInventory.current_quantity).label('total_qty')
        ).scalar() or 0
        
        potential_profit = profit_amount * total_inventory
        total_profit_potential += potential_profit
        
        analytics.append({
            "product_id": product.id,
            "product_name": product.name,
            "buying_price": float(product.buying_price),
            "selling_price": float(product.selling_price),
            "profit_amount": float(profit_amount),
            "profit_margin": float(profit_margin),
            "total_inventory": int(total_inventory),
            "potential_profit": float(potential_profit)
        })
    
    return {
        "products": analytics,
        "total_profit_potential": float(total_profit_potential),
        "total_products": len(products),
        "average_margin": sum(p["profit_margin"] for p in analytics) / len(analytics) if analytics else 0
    }