"""
Loan-related Pydantic schemas
"""

from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, validator

from app.core.permissions import UserRole


# Product Category Schemas
class ProductCategoryCreate(BaseModel):
    """Product category creation"""
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None


class ProductCategoryResponse(BaseModel):
    """Product category response"""
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Loan Product Schemas
class LoanProductCreate(BaseModel):
    """Loan product creation"""
    name: str = Field(..., min_length=2, max_length=100)
    category_id: int
    description: Optional[str] = None
    buying_price: Decimal = Field(..., gt=0, decimal_places=2)
    selling_price: Decimal = Field(..., gt=0, decimal_places=2)
    
    @validator('selling_price')
    def selling_price_must_be_higher(cls, v, values):
        if 'buying_price' in values and v <= values['buying_price']:
            raise ValueError('Selling price must be higher than buying price')
        return v


class LoanProductUpdate(BaseModel):
    """Loan product update"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    category_id: Optional[int] = None
    description: Optional[str] = None
    buying_price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    selling_price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    is_active: Optional[bool] = None


class LoanProductResponse(BaseModel):
    """Loan product response"""
    id: int
    name: str
    category_id: int
    description: Optional[str] = None
    buying_price: Optional[Decimal] = None  # Hidden from non-admin users
    selling_price: Decimal
    image_url: Optional[str] = None
    profit_margin: Optional[float] = None  # Calculated property
    is_active: bool
    created_at: datetime
    
    # Category information
    category_name: Optional[str] = None
    
    # Inventory information (when requested)
    current_quantity: Optional[int] = None
    inventory_status: Optional[str] = None
    
    class Config:
        from_attributes = True


# Loan Type Schemas
class LoanTypeCreate(BaseModel):
    """Loan type creation"""
    name: str = Field(..., min_length=2, max_length=100)
    branch_id: Optional[int] = None  # None for global loan types
    min_amount: Decimal = Field(..., gt=0, decimal_places=2)
    max_amount: Decimal = Field(..., gt=0, decimal_places=2)
    interest_rate: Decimal = Field(..., ge=0, le=100, decimal_places=2)
    charge_fee_rate: Decimal = Field(default=Decimal('0.00'), ge=0, le=100, decimal_places=2)
    period_months: int = Field(..., gt=0, le=60)
    allows_partial_payments: bool = False
    
    @validator('max_amount')
    def max_amount_must_be_higher(cls, v, values):
        if 'min_amount' in values and v <= values['min_amount']:
            raise ValueError('Maximum amount must be greater than minimum amount')
        return v


class LoanTypeUpdate(BaseModel):
    """Loan type update"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    min_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    max_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    charge_fee_rate: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    period_months: Optional[int] = Field(None, gt=0, le=60)
    allows_partial_payments: Optional[bool] = None
    is_active: Optional[bool] = None


class LoanTypeResponse(BaseModel):
    """Loan type response"""
    id: int
    name: str
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    min_amount: Decimal
    max_amount: Decimal
    interest_rate: Decimal
    charge_fee_rate: Decimal
    period_months: int
    allows_partial_payments: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Loan Calculation Schemas
class ProductSelectionItem(BaseModel):
    """Product selection for loan calculation"""
    product_id: int
    quantity: int = Field(..., gt=0, le=10)


class LoanCalculationRequest(BaseModel):
    """Loan calculation request"""
    loan_type_id: int
    products: List[ProductSelectionItem]
    
    @validator('products')
    def validate_max_products(cls, v):
        if len(v) > 3:
            raise ValueError('Maximum 3 products allowed per loan')
        return v


class LoanCalculationResponse(BaseModel):
    """Loan calculation response"""
    is_valid: bool
    error_message: Optional[str] = None
    
    # Loan details (if valid)
    loan_type_id: Optional[int] = None
    loan_type_name: Optional[str] = None
    principal_amount: Optional[float] = None
    interest_amount: Optional[float] = None
    charge_fee_amount: Optional[float] = None
    total_amount: Optional[float] = None
    period_months: Optional[int] = None
    monthly_payment: Optional[float] = None
    allows_partial_payments: Optional[bool] = None
    
    # Product breakdown
    products: List[dict] = []
    
    # Suggestions (if invalid)
    suggested_loan_types: List[dict] = []


# Branch Inventory Schemas
class BranchInventoryResponse(BaseModel):
    """Branch inventory response"""
    id: int
    branch_id: int
    branch_name: Optional[str] = None
    loan_product_id: int
    product_name: Optional[str] = None
    current_quantity: int
    reorder_point: int
    critical_point: int
    status: str  # Computed property: ok, low, critical
    last_restocked_at: Optional[date] = None
    last_restocked_by: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class BranchInventoryUpdate(BaseModel):
    """Branch inventory update"""
    current_quantity: Optional[int] = Field(None, ge=0)
    reorder_point: Optional[int] = Field(None, gt=0)
    critical_point: Optional[int] = Field(None, gt=0)
    reason: Optional[str] = None


class StockMovementCreate(BaseModel):
    """Stock movement creation"""
    branch_id: int
    loan_product_id: int
    movement_type: str = Field(..., regex="^(restock|loan_disbursement|adjustment|transfer)$")
    quantity_change: int
    reason: Optional[str] = None


class StockMovementResponse(BaseModel):
    """Stock movement response"""
    id: int
    branch_id: int
    branch_name: Optional[str] = None
    loan_product_id: int
    product_name: Optional[str] = None
    movement_type: str
    quantity_change: int
    previous_quantity: int
    new_quantity: int
    reason: Optional[str] = None
    created_by: int
    created_by_name: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class RestockRequest(BaseModel):
    """Product restock request"""
    branch_id: int
    product_id: int
    quantity: int = Field(..., gt=0)
    reason: Optional[str] = None


class InventoryStatsResponse(BaseModel):
    """Inventory statistics response"""
    total_products: int
    total_quantity: int
    total_value: Optional[float] = None  # Only for admin
    low_stock_items: int
    critical_stock_items: int
    out_of_stock_items: int
    status_breakdown: dict


# Loan Application Schemas
class LoanApplicationCreate(BaseModel):
    """Loan application creation"""
    applicant_id: int
    loan_type_id: int
    products: List[ProductSelectionItem]
    
    @validator('products')
    def validate_products(cls, v):
        if len(v) == 0:
            raise ValueError('At least one product must be selected')
        if len(v) > 3:
            raise ValueError('Maximum 3 products allowed per loan')
        return v


class LoanApplicationUpdate(BaseModel):
    """Loan application update"""
    status: Optional[str] = Field(None, pattern="^(submitted|pending|under_review|on_hold|approved|rejected|disbursed)$")
    rejection_reason: Optional[str] = None


class LoanApplicationResponse(BaseModel):
    """Loan application response"""
    id: int
    application_number: str
    applicant_id: int
    applicant_name: str
    group_id: int
    group_name: str
    loan_officer_id: int
    loan_officer_name: str
    loan_type_id: int
    loan_type_name: str
    total_amount: Decimal
    status: str
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[date] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    
    # Product details
    products: List[dict] = []
    
    class Config:
        from_attributes = True