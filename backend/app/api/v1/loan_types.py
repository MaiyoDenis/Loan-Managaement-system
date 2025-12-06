"""
Loan Types API endpoints
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from decimal import Decimal

from app.database import get_db
from app.models.loan import LoanType
from app.models.user import User
from app.models.branch import Branch
from app.core.permissions import UserRole
from app.schemas.loan import (
    LoanTypeCreate,
    LoanTypeUpdate,
    LoanTypeResponse,
    LoanCalculationRequest,
    LoanCalculationResponse
)
from app.api.deps import (
    get_current_active_user,
    require_permission
)

router = APIRouter()


@router.get("/", response_model=List[LoanTypeResponse])
def get_loan_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    branch_id: Optional[int] = Query(None),
    is_global: Optional[bool] = Query(None)
) -> Any:
    """Get loan types with branch filtering"""
    query = db.query(LoanType).filter(LoanType.is_active == True)
    
    # Apply branch filtering
    if current_user.role == UserRole.ADMIN:
        # Admin can see all loan types
        if branch_id is not None:
            query = query.filter(
                or_(LoanType.branch_id == branch_id, LoanType.branch_id.is_(None))
            )
        elif is_global is not None:
            if is_global:
                query = query.filter(LoanType.branch_id.is_(None))
            else:
                query = query.filter(LoanType.branch_id.isnot(None))
    else:
        # Other users see their branch types + global types
        query = query.filter(
            or_(
                LoanType.branch_id == current_user.branch_id,
                LoanType.branch_id.is_(None)
            )
        )
    
    loan_types = query.all()
    
    # Add branch names
    response_types = []
    for loan_type in loan_types:
        loan_type_data = LoanTypeResponse.from_orm(loan_type)
        if loan_type.branch_id:
            branch = db.query(Branch).filter(Branch.id == loan_type.branch_id).first()
            loan_type_data.branch_name = branch.name if branch else None
        else:
            loan_type_data.branch_name = "Global"
        
        response_types.append(loan_type_data)
    
    return response_types


@router.post("/", response_model=LoanTypeResponse)
def create_loan_type(
    loan_type_data: LoanTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("loans:types_manage"))
) -> Any:
    """Create a new loan type"""
    # Validate branch access
    if loan_type_data.branch_id:
        if current_user.role != UserRole.ADMIN:
            if loan_type_data.branch_id != current_user.branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only create loan types for your branch"
                )
        
        # Verify branch exists
        branch = db.query(Branch).filter(Branch.id == loan_type_data.branch_id).first()
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found"
            )
    
    # Validate amount range
    if loan_type_data.min_amount >= loan_type_data.max_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum amount must be greater than minimum amount"
        )
    
    # Check for overlapping ranges in same branch
    existing_types = db.query(LoanType).filter(
        LoanType.branch_id == loan_type_data.branch_id,
        LoanType.is_active == True
    ).all()
    
    for existing_type in existing_types:
        # Check for range overlap
        if (loan_type_data.min_amount <= existing_type.max_amount and 
            loan_type_data.max_amount >= existing_type.min_amount):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Amount range overlaps with existing loan type '{existing_type.name}'"
            )
    
    loan_type = LoanType(
        name=loan_type_data.name,
        branch_id=loan_type_data.branch_id,
        min_amount=loan_type_data.min_amount,
        max_amount=loan_type_data.max_amount,
        interest_rate=loan_type_data.interest_rate,
        charge_fee_rate=loan_type_data.charge_fee_rate,
        period_months=loan_type_data.period_months,
        allows_partial_payments=loan_type_data.allows_partial_payments,
        created_by=current_user.id
    )
    
    db.add(loan_type)
    db.commit()
    db.refresh(loan_type)
    
    return loan_type


@router.put("/{loan_type_id}", response_model=LoanTypeResponse)
def update_loan_type(
    loan_type_id: int,
    loan_type_data: LoanTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("loans:types_manage"))
) -> Any:
    """Update loan type"""
    loan_type = db.query(LoanType).filter(LoanType.id == loan_type_id).first()
    
    if not loan_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan type not found"
        )
    
    # Check access permissions
    if current_user.role != UserRole.ADMIN:
        if loan_type.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update loan types in your branch"
            )
    
    # Update fields
    update_data = loan_type_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(loan_type, field, value)
    
    # Validate amount range
    if hasattr(loan_type, 'min_amount') and hasattr(loan_type, 'max_amount'):
        if loan_type.min_amount >= loan_type.max_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum amount must be greater than minimum amount"
            )
    
    db.commit()
    db.refresh(loan_type)
    
    return loan_type


@router.post("/calculate", response_model=LoanCalculationResponse)
def calculate_loan(
    calculation_data: LoanCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Calculate loan totals for given products and loan type"""
    # Get loan type
    loan_type = db.query(LoanType).filter(LoanType.id == calculation_data.loan_type_id).first()
    if not loan_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan type not found"
        )
    
    # Calculate total amount for selected products
    from app.models.loan import LoanProduct
    
    total_principal = Decimal('0.00')
    product_details = []
    
    for product_item in calculation_data.products:
        product = db.query(LoanProduct).filter(LoanProduct.id == product_item.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_item.product_id} not found"
            )
        
        item_total = product.selling_price * product_item.quantity
        total_principal += item_total
        
        product_details.append({
            "product_id": product.id,
            "product_name": product.name,
            "unit_price": float(product.selling_price),
            "quantity": product_item.quantity,
            "total_price": float(item_total)
        })
    
    # Validate amount is within loan type range
    if total_principal < loan_type.min_amount or total_principal > loan_type.max_amount:
        return LoanCalculationResponse(
            is_valid=False,
            error_message=f"Total amount ${total_principal} is outside the range ${loan_type.min_amount} - ${loan_type.max_amount} for loan type '{loan_type.name}'",
            principal_amount=float(total_principal),
            suggested_loan_types=[]
        )
    
    # Calculate loan breakdown
    loan_breakdown = loan_type.calculate_total_amount(total_principal)
    
    return LoanCalculationResponse(
        is_valid=True,
        loan_type_id=loan_type.id,
        loan_type_name=loan_type.name,
        principal_amount=float(loan_breakdown["principal"]),
        interest_amount=float(loan_breakdown["interest"]),
        charge_fee_amount=float(loan_breakdown["charge_fee"]),
        total_amount=float(loan_breakdown["total"]),
        period_months=loan_type.period_months,
        allows_partial_payments=loan_type.allows_partial_payments,
        products=product_details
    )


@router.post("/suggest-loan-type")
def suggest_loan_type(
    amount: Decimal,
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Suggest appropriate loan types for given amount"""
    query = db.query(LoanType).filter(
        LoanType.is_active == True,
        LoanType.min_amount <= amount,
        LoanType.max_amount >= amount
    )
    
    # Apply branch filtering
    target_branch_id = branch_id or current_user.branch_id
    if target_branch_id:
        query = query.filter(
            or_(LoanType.branch_id == target_branch_id, LoanType.branch_id.is_(None))
        )
    
    suitable_types = query.all()
    
    suggestions = []
    for loan_type in suitable_types:
        breakdown = loan_type.calculate_total_amount(amount)
        
        suggestions.append({
            "loan_type_id": loan_type.id,
            "loan_type_name": loan_type.name,
            "interest_rate": float(loan_type.interest_rate),
            "charge_fee_rate": float(loan_type.charge_fee_rate),
            "period_months": loan_type.period_months,
            "total_amount": float(breakdown["total"]),
            "monthly_payment": float(breakdown["total"] / loan_type.period_months)
        })
    
    return {
        "requested_amount": float(amount),
        "suitable_loan_types": suggestions,
        "count": len(suggestions)
    }


@router.delete("/{loan_type_id}")
def delete_loan_type(
    loan_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("loans:types_manage"))
) -> Any:
    """Soft delete loan type"""
    loan_type = db.query(LoanType).filter(LoanType.id == loan_type_id).first()
    
    if not loan_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan type not found"
        )
    
    # Check for active loans using this type
    from app.models.loan import Loan
    active_loans = db.query(Loan).filter(
        Loan.loan_type_id == loan_type_id,
        Loan.status.in_(["active", "arrears"])
    ).count()
    
    if active_loans > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete loan type. {active_loans} active loans are using this type."
        )
    
    loan_type.is_active = False
    db.commit()
    
    return {"message": "Loan type deleted successfully"}