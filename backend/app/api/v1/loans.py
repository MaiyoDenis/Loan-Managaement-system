"""
Active Loans Management API endpoints
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from decimal import Decimal
from datetime import datetime, date

from app.database import get_db
from app.models.loan import Loan, Payment, Arrear
from app.models.user import User
from app.core.permissions import UserRole
from app.schemas.loan import (
    LoanResponse,
    LoanUpdate,
    PaymentCreate,
    PaymentResponse,
    LoanSummaryResponse
)
from app.api.deps import (
    get_current_active_user,
    require_permission
)

router = APIRouter()


@router.get("/", response_model=List[LoanResponse])
def get_loans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    status_filter: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    group_id: Optional[int] = Query(None),
    overdue_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """Get loans with filtering"""
    query = db.query(Loan).options(
        joinedload(Loan.borrower),
        joinedload(Loan.loan_type),
        joinedload(Loan.loan_application)
    )
    
    # Apply role-based filtering
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(Loan.borrower_id == current_user.id)
    elif current_user.role == UserRole.LOAN_OFFICER:
        # Get loans from officer's groups
        from app.models.branch import Group, GroupMembership
        managed_groups = db.query(Group).filter(Group.loan_officer_id == current_user.id).all()
        group_ids = [g.id for g in managed_groups]
        
        # Get members from these groups
        group_members = db.query(GroupMembership).filter(
            GroupMembership.group_id.in_(group_ids),
            GroupMembership.is_active == True
        ).all()
        member_ids = [gm.member_id for gm in group_members]
        
        query = query.filter(Loan.borrower_id.in_(member_ids))
    elif current_user.role != UserRole.ADMIN:
        # Branch staff see branch loans
        branch_users = db.query(User).filter(User.branch_id == current_user.branch_id).all()
        user_ids = [u.id for u in branch_users if u.role == UserRole.CUSTOMER]
        query = query.filter(Loan.borrower_id.in_(user_ids))
    
    # Apply additional filters
    if status_filter:
        query = query.filter(Loan.status == status_filter)
    
    if overdue_only:
        query = query.filter(
            Loan.due_date < date.today(),
            Loan.status == "active"
        )
    
    if branch_id and current_user.role == UserRole.ADMIN:
        branch_users = db.query(User).filter(User.branch_id == branch_id).all()
        user_ids = [u.id for u in branch_users if u.role == UserRole.CUSTOMER]
        query = query.filter(Loan.borrower_id.in_(user_ids))
    
    # Order by most recent first
    loans = query.order_by(Loan.created_at.desc()).offset(skip).limit(limit).all()
    
    return loans


@router.get("/{loan_id}", response_model=LoanResponse)
def get_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get specific loan details"""
    loan = db.query(Loan).options(
        joinedload(Loan.borrower),
        joinedload(Loan.loan_type),
        joinedload(Loan.loan_application),
        joinedload(Loan.payments)
    ).filter(Loan.id == loan_id).first()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )
    
    # Check access permissions
    if current_user.role == UserRole.CUSTOMER:
        if loan.borrower_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role != UserRole.ADMIN:
        if loan.borrower.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return loan


@router.put("/{loan_id}", response_model=LoanResponse)
def update_loan(
    loan_id: int,
    loan_data: LoanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("loans:update"))
) -> Any:
    """Update loan information"""
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )
    
    # Check access permissions
    if current_user.role != UserRole.ADMIN:
        if loan.borrower.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Update fields
    update_data = loan_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(loan, field, value)
    
    db.commit()
    db.refresh(loan)
    
    return loan


@router.get("/{loan_id}/payment-schedule")
def get_payment_schedule(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get payment schedule for a loan"""
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )
    
    # Check access permissions
    if current_user.role == UserRole.CUSTOMER:
        if loan.borrower_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role != UserRole.ADMIN:
        if loan.borrower.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Generate payment schedule
    from dateutil.relativedelta import relativedelta
    
    schedule = []
    current_date = loan.start_date
    remaining_balance = loan.total_amount
    
    if loan.loan_type.allows_partial_payments:
        # Monthly payments
        monthly_payment = loan.total_amount / loan.loan_type.period_months
        
        for month in range(loan.loan_type.period_months):
            payment_date = current_date + relativedelta(months=month)
            payment_amount = min(monthly_payment, remaining_balance)
            
            schedule.append({
                "payment_number": month + 1,
                "due_date": payment_date.isoformat(),
                "amount": float(payment_amount),
                "remaining_balance": float(remaining_balance - payment_amount),
                "status": "pending" if payment_date >= date.today() else "overdue"
            })
            
            remaining_balance -= payment_amount
    else:
        # Single payment
        schedule.append({
            "payment_number": 1,
            "due_date": loan.due_date.isoformat(),
            "amount": float(loan.total_amount),
            "remaining_balance": 0.0,
            "status": "pending" if loan.due_date >= date.today() else "overdue"
        })
    
    return {
        "loan_id": loan.id,
        "loan_number": loan.loan_number,
        "total_amount": float(loan.total_amount),
        "amount_paid": float(loan.amount_paid),
        "balance": float(loan.balance),
        "allows_partial_payments": loan.loan_type.allows_partial_payments,
        "payment_schedule": schedule
    }


@router.get("/analytics/overview")
def get_loans_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    branch_id: Optional[int] = Query(None)
) -> Any:
    """Get loans overview analytics"""
    # Determine scope based on user role
    query = db.query(Loan)
    
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(Loan.borrower_id == current_user.id)
    elif current_user.role != UserRole.ADMIN:
        # Branch-level analytics
        branch_users = db.query(User).filter(User.branch_id == current_user.branch_id).all()
        user_ids = [u.id for u in branch_users if u.role == UserRole.CUSTOMER]
        query = query.filter(Loan.borrower_id.in_(user_ids))
    elif branch_id:
        # Admin viewing specific branch
        branch_users = db.query(User).filter(User.branch_id == branch_id).all()
        user_ids = [u.id for u in branch_users if u.role == UserRole.CUSTOMER]
        query = query.filter(Loan.borrower_id.in_(user_ids))
    
    # Calculate statistics
    all_loans = query.all()
    
    stats = {
        "total_loans": len(all_loans),
        "active_loans": len([l for l in all_loans if l.status == "active"]),
        "completed_loans": len([l for l in all_loans if l.status == "completed"]),
        "arrears_loans": len([l for l in all_loans if l.status == "arrears"]),
        "total_amount_disbursed": float(sum(l.total_amount for l in all_loans)),
        "total_amount_outstanding": float(sum(l.balance for l in all_loans if l.status in ["active", "arrears"])),
        "total_amount_collected": float(sum(l.amount_paid for l in all_loans)),
        "collection_rate": 0.0
    }
    
    # Calculate collection rate
    if stats["total_amount_disbursed"] > 0:
        stats["collection_rate"] = (stats["total_amount_collected"] / stats["total_amount_disbursed"]) * 100
    
    # Overdue loans
    overdue_loans = [l for l in all_loans if l.is_overdue]
    stats["overdue_loans"] = len(overdue_loans)
    stats["overdue_amount"] = float(sum(l.balance for l in overdue_loans))
    
    return stats