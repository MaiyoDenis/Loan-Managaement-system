"""
Loan product and product category management API endpoints
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LoanProduct, ProductCategory, User
from app.schemas.loan import LoanProductCreate, LoanProductUpdate, LoanProductResponse, ProductCategoryCreate, ProductCategoryUpdate, ProductCategoryResponse
from app.api.deps import get_current_active_user, require_permission

router = APIRouter()


@router.get("/categories", response_model=List[ProductCategoryResponse])
def get_product_categories(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(require_permission("product_category_view"))
) -> Any:
    """
    Get product categories with pagination
    """
    categories = db.query(ProductCategory).offset(skip).limit(limit).all()
    return categories


@router.post("/categories", response_model=ProductCategoryResponse, status_code=status.HTTP_201_CREATED)
def create_product_category(
    category_data: ProductCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product_category_create"))
) -> Any:
    """
    Create a new product category
    """
    category = ProductCategory(**category_data.dict(), created_by=current_user.id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/categories/{category_id}", response_model=ProductCategoryResponse)
def get_product_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product_category_view"))
) -> Any:
    """
    Get product category by ID
    """
    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product category not found"
        )
    return category


@router.put("/categories/{category_id}", response_model=ProductCategoryResponse)
def update_product_category(
    category_id: int,
    category_data: ProductCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product_category_update"))
) -> Any:
    """
    Update a product category
    """
    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product category not found"
        )
    
    update_data = category_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("product_category_delete"))
) -> Any:
    """
    Delete a product category
    """
    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product category not found"
        )
    db.delete(category)
    db.commit()


@router.get("/", response_model=List[LoanProductResponse])
def get_loan_products(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(require_permission("loan_product_view"))
) -> Any:
    """
    Get loan products with pagination
    """
    products = db.query(LoanProduct).offset(skip).limit(limit).all()
    return products


@router.post("/", response_model=LoanProductResponse, status_code=status.HTTP_201_CREATED)
def create_loan_product(
    product_data: LoanProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("loan_product_create"))
) -> Any:
    """
    Create a new loan product
    """
    product = LoanProduct(**product_data.dict(), created_by=current_user.id)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=LoanProductResponse)
def get_loan_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("loan_product_view"))
) -> Any:
    """
    Get loan product by ID
    """
    product = db.query(LoanProduct).filter(LoanProduct.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan product not found"
        )
    return product


@router.put("/{product_id}", response_model=LoanProductResponse)
def update_loan_product(
    product_id: int,
    product_data: LoanProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("loan_product_update"))
) -> Any:
    """
    Update a loan product
    """
    product = db.query(LoanProduct).filter(LoanProduct.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan product not found"
        )
    
    update_data = product_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_loan_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("loan_product_delete"))
) -> Any:
    """
    Delete a loan product
    """
    product = db.query(LoanProduct).filter(LoanProduct.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan product not found"
        )
    db.delete(product)
    db.commit()
