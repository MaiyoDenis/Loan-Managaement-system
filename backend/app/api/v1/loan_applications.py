"""
Loan Application API endpoints
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from decimal import Decimal
from datetime import datetime, date

from app.database import get_db
from app.models.loan import (
    LoanApplication, 
    LoanApplicationProduct, 
    LoanType, 
    LoanProduct,
    Loan,
    BranchInventory
)
from app.models.user import User
from app.models.branch import Group, GroupMembership
from app.core.permissions import UserRole
from app.schemas.loan import (
    LoanApplicationCreate,
    LoanApplicationUpdate,
    LoanApplicationResponse,
    LoanCalculationRequest,
    LoanCalculationResponse
)
from app.api.deps import (
    get_current_active_user,
    require_permission
)

router = APIRouter()


@router.get("/", response_model=List[LoanApplicationResponse])
def get_loan_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    status_filter: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    group_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """Get loan applications with filtering"""
    query = db.query(LoanApplication).options(
        joinedload(LoanApplication.applicant),
        joinedload(LoanApplication.group),
        joinedload(LoanApplication.loan_officer),
        joinedload(LoanApplication.loan_type),
        joinedload(LoanApplication.application_products)
    )
    
    # Apply role-based filtering
    if current_user.role == UserRole.CUSTOMER:
        # Customers see only their own applications
        query = query.filter(LoanApplication.applicant_id == current_user.id)
    elif current_user.role == UserRole.LOAN_OFFICER:
        # Loan officers see applications from their groups
        managed_groups = db.query(Group).filter(Group.loan_officer_id == current_user.id).all()
        group_ids = [g.id for g in managed_groups]
        query = query.filter(LoanApplication.group_id.in_(group_ids))
    elif current_user.role in [UserRole.BRANCH_MANAGER, UserRole.PROCUREMENT_OFFICER]:
        # Branch staff see their branch applications
        branch_groups = db.query(Group).filter(Group.branch_id == current_user.branch_id).all()
        group_ids = [g.id for g in branch_groups]
        query = query.filter(LoanApplication.group_id.in_(group_ids))
    # Admin sees all applications
    
    # Apply additional filters
    if status_filter:
        query = query.filter(LoanApplication.status == status_filter)
    
    if branch_id and current_user.role == UserRole.ADMIN:
        branch_groups = db.query(Group).filter(Group.branch_id == branch_id).all()
        group_ids = [g.id for g in branch_groups]
        query = query.filter(LoanApplication.group_id.in_(group_ids))
    
    if group_id:
        query = query.filter(LoanApplication.group_id == group_id)
    
    # Order by most recent first
    applications = query.order_by(LoanApplication.created_at.desc()).offset(skip).limit(limit).all()
    
    # Convert to response format
    response_applications = []
    for app in applications:
        app_data = LoanApplicationResponse(
            id=app.id,
            application_number=app.application_number,
            applicant_id=app.applicant_id,
            applicant_name=f"{app.applicant.first_name} {app.applicant.last_name}",
            group_id=app.group_id,
            group_name=app.group.name,
            loan_officer_id=app.loan_officer_id,
            loan_officer_name=f"{app.loan_officer.first_name} {app.loan_officer.last_name}",
            loan_type_id=app.loan_type_id,
            loan_type_name=app.loan_type.name,
            total_amount=app.total_amount,
            status=app.status.value,
            reviewed_by=app.reviewed_by,
            reviewed_at=app.reviewed_at,
            rejection_reason=app.rejection_reason,
            created_at=app.created_at,
            products=[
                {
                    "product_id": ap.loan_product_id,
                    "product_name": ap.loan_product.name,
                    "quantity": ap.quantity,
                    "unit_price": float(ap.unit_price),
                    "total_price": float(ap.total_price)
                }
                for ap in app.application_products
            ]
        )
        response_applications.append(app_data)
    
    return response_applications


@router.post("/", response_model=LoanApplicationResponse)
def create_loan_application(
    application_data: LoanApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Create a new loan application"""
    # Get applicant
    applicant = db.query(User).filter(User.id == application_data.applicant_id).first()
    if not applicant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Applicant not found"
        )
    
    # Check if applicant has active loans (max 3 rule)
    active_loans_count = db.query(Loan).filter(
        Loan.borrower_id == application_data.applicant_id,
        Loan.status.in_(["active", "arrears"])
    ).count()
    
    if active_loans_count >= 3:
        active_loans = db.query(Loan).filter(
            Loan.borrower_id == application_data.applicant_id,
            Loan.status.in_(["active", "arrears"])
        ).all()
        
        # Suggest which loans to clear
        clearable_loans = [
            {
                "loan_id": loan.id,
                "loan_number": loan.loan_number,
                "balance": float(loan.balance),
                "can_clear_from_drawdown": float(applicant.drawdown_account.balance) >= float(loan.balance)
            }
            for loan in active_loans
        ]
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Maximum 3 active loans allowed",
                "current_loans": active_loans_count,
                "clearable_loans": clearable_loans
            }
        )
    
    # Get applicant's group membership
    membership = db.query(GroupMembership).filter(
        GroupMembership.member_id == application_data.applicant_id,
        GroupMembership.is_active == True
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Applicant is not a member of any active group"
        )
    
    # Check access permissions for loan officer
    if current_user.role == UserRole.LOAN_OFFICER:
        if membership.group.loan_officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create applications for your group members"
            )
    elif current_user.role == UserRole.CUSTOMER:
        if current_user.id != application_data.applicant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create your own loan applications"
            )
    
    # Get loan type
    loan_type = db.query(LoanType).filter(LoanType.id == application_data.loan_type_id).first()
    if not loan_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan type not found"
        )
    
    # Calculate total amount and validate
    total_principal = Decimal('0.00')
    product_details = []
    
    for product_item in application_data.products:
        product = db.query(LoanProduct).filter(LoanProduct.id == product_item.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_item.product_id} not found"
            )
        
        # Check inventory availability
        inventory = db.query(BranchInventory).filter(
            BranchInventory.branch_id == membership.group.branch_id,
            BranchInventory.loan_product_id == product_item.product_id
        ).first()
        
        if not inventory or inventory.current_quantity < product_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {product.name}. Available: {inventory.current_quantity if inventory else 0}"
            )
        
        item_total = product.selling_price * product_item.quantity
        total_principal += item_total
        
        product_details.append({
            "product_id": product.id,
            "quantity": product_item.quantity,
            "unit_price": product.selling_price,
            "total_price": item_total
        })
    
    # Validate amount is within loan type range
    if total_principal < loan_type.min_amount or total_principal > loan_type.max_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Total amount ${total_principal} is outside the range ${loan_type.min_amount} - ${loan_type.max_amount} for loan type '{loan_type.name}'"
        )
    
    # Check loan limit
    if not applicant.savings_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Applicant does not have a savings account"
        )
    
    loan_breakdown = loan_type.calculate_total_amount(total_principal)
    if loan_breakdown["total"] > applicant.savings_account.loan_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Loan amount exceeds available limit",
                "requested_amount": float(loan_breakdown["total"]),
                "available_limit": float(applicant.savings_account.loan_limit),
                "current_savings": float(applicant.savings_account.balance),
                "suggestion": "Increase savings to raise loan limit"
            }
        )
    
    # Generate application number
    app_number = f"APP{datetime.now().strftime('%Y%m%d%H%M%S')}{applicant.id}"
    
    # Create loan application
    loan_application = LoanApplication(
        application_number=app_number,
        applicant_id=application_data.applicant_id,
        group_id=membership.group_id,
        loan_officer_id=membership.group.loan_officer_id,
        loan_type_id=application_data.loan_type_id,
        total_amount=loan_breakdown["total"]
    )
    
    db.add(loan_application)
    db.flush()  # Get application ID
    
    # Add application products
    for product_detail in product_details:
        app_product = LoanApplicationProduct(
            loan_application_id=loan_application.id,
            loan_product_id=product_detail["product_id"],
            quantity=product_detail["quantity"],
            unit_price=product_detail["unit_price"],
            total_price=product_detail["total_price"]
        )
        db.add(app_product)
    
    db.commit()
    db.refresh(loan_application)
    
    # TODO: Send notification to procurement officer
    
    return loan_application


@router.put("/{application_id}/status", response_model=LoanApplicationResponse)
def update_application_status(
    application_id: int,
    status_update: LoanApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("loans:approve"))
) -> Any:
    """Update loan application status (Procurement Officer)"""
    application = db.query(LoanApplication).options(
        joinedload(LoanApplication.applicant),
        joinedload(LoanApplication.group),
        joinedload(LoanApplication.application_products)
    ).filter(LoanApplication.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan application not found"
        )
    
    # Check branch access for non-admin users
    if current_user.role != UserRole.ADMIN:
        if application.group.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this application"
            )
    
    # Update status
    old_status = application.status
    application.status = status_update.status
    application.reviewed_by = current_user.id
    application.reviewed_at = date.today()
    
    if status_update.rejection_reason:
        application.rejection_reason = status_update.rejection_reason
    
    # Handle disbursement
    if status_update.status == "disbursed" and old_status == "approved":
        # Create actual loan record
        loan = await self._disburse_loan(application, current_user, db)
        
        # Update inventory quantities
        for app_product in application.application_products:
            inventory = db.query(BranchInventory).filter(
                BranchInventory.branch_id == application.group.branch_id,
                BranchInventory.loan_product_id == app_product.loan_product_id
            ).first()
            
            if inventory:
                inventory.current_quantity -= app_product.quantity
                
                # Create stock movement
                from app.models.loan import StockMovement
                stock_movement = StockMovement(
                    branch_id=application.group.branch_id,
                    loan_product_id=app_product.loan_product_id,
                    movement_type="loan_disbursement",
                    quantity_change=-app_product.quantity,
                    previous_quantity=inventory.current_quantity + app_product.quantity,
                    new_quantity=inventory.current_quantity,
                    reason=f"Loan disbursement - {application.application_number}",
                    created_by=current_user.id
                )
                db.add(stock_movement)
        
        application.disbursed_by = current_user.id
        application.disbursed_at = date.today()
    
    db.commit()
    db.refresh(application)
    
    # TODO: Send notification to applicant and loan officer
    
    return application


async def _disburse_loan(self, application: LoanApplication, current_user: User, db: Session) -> Loan:
    """Create actual loan from approved application"""
    # Calculate loan details
    loan_breakdown = application.loan_type.calculate_total_amount(application.total_amount)
    
    # Generate loan number
    loan_number = f"LN{datetime.now().strftime('%Y%m%d%H%M%S')}{application.applicant_id}"
    
    # Calculate due date
    from dateutil.relativedelta import relativedelta
    start_date = date.today()
    due_date = start_date + relativedelta(months=application.loan_type.period_months)
    
    # Calculate next payment details
    if application.loan_type.allows_partial_payments:
        next_payment_amount = loan_breakdown["total"] / application.loan_type.period_months
        next_payment_date = start_date + relativedelta(months=1)
    else:
        next_payment_amount = loan_breakdown["total"]
        next_payment_date = due_date
    
    # Create loan
    loan = Loan(
        loan_number=loan_number,
        loan_application_id=application.id,
        borrower_id=application.applicant_id,
        loan_type_id=application.loan_type_id,
        principal_amount=loan_breakdown["principal"],
        interest_amount=loan_breakdown["interest"],
        charge_fee_amount=loan_breakdown["charge_fee"],
        total_amount=loan_breakdown["total"],
        balance=loan_breakdown["total"],
        start_date=start_date,
        due_date=due_date,
        next_payment_date=next_payment_date,
        next_payment_amount=next_payment_amount
    )
    
    db.add(loan)
    
    # Create disbursement transaction (credit to drawdown account)
    from app.models.loan import Transaction, DrawdownAccount
    
    drawdown_account = db.query(DrawdownAccount).filter(
        DrawdownAccount.user_id == application.applicant_id
    ).first()
    
    if drawdown_account:
        balance_before = drawdown_account.balance
        drawdown_account.balance += loan_breakdown["principal"]  # Only principal, not fees
        
        transaction = Transaction(
            transaction_number=f"DISB{datetime.now().strftime('%Y%m%d%H%M%S')}{application.applicant_id}",
            user_id=application.applicant_id,
            account_id=drawdown_account.id,
            account_type="drawdown",
            transaction_type="loan_disbursement",
            amount=loan_breakdown["principal"],
            balance_before=balance_before,
            balance_after=drawdown_account.balance,
            description=f"Loan disbursement - {loan_number}",
            reference_number=application.application_number,
            processed_by=current_user.id
        )
        db.add(transaction)
    
    return loan


@router.get("/{application_id}", response_model=LoanApplicationResponse)
def get_loan_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get specific loan application"""
    application = db.query(LoanApplication).options(
        joinedload(LoanApplication.applicant),
        joinedload(LoanApplication.group),
        joinedload(LoanApplication.loan_officer),
        joinedload(LoanApplication.loan_type),
        joinedload(LoanApplication.application_products)
    ).filter(LoanApplication.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan application not found"
        )
    
    # Check access permissions
    if current_user.role == UserRole.CUSTOMER:
        if application.applicant_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role == UserRole.LOAN_OFFICER:
        if application.loan_officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role != UserRole.ADMIN:
        if application.group.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return application


@router.delete("/{application_id}")
def cancel_loan_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Cancel/delete loan application (only if not approved/disbursed)"""
    application = db.query(LoanApplication).filter(LoanApplication.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan application not found"
        )
    
    # Check if can be cancelled
    if application.status.value in ["approved", "disbursed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel approved or disbursed loan applications"
        )
    
    # Check access permissions
    if current_user.role == UserRole.CUSTOMER:
        if application.applicant_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel your own applications"
            )
    elif current_user.role == UserRole.LOAN_OFFICER:
        if application.loan_officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only cancel applications from your groups"
            )
    
    # Soft delete
    application.is_active = False
    db.commit()
    
    return {"message": "Loan application cancelled successfully"}


@router.get("/eligibility/{user_id}")
def check_loan_eligibility(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Check loan eligibility for a user"""
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check access permissions
    if current_user.role == UserRole.CUSTOMER:
        if current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role != UserRole.ADMIN:
        if user.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Get savings account
    savings_account = user.savings_account
    if not savings_account:
        return {
            "eligible": False,
            "reason": "No savings account found",
            "requirements": ["Create savings account"]
        }
    
    # Check registration status
    if not savings_account.registration_fee_paid:
        return {
            "eligible": False,
            "reason": "Registration fee not paid",
            "current_balance": float(savings_account.balance),
            "required_deposit": float(800 + abs(savings_account.balance)),
            "requirements": [
                f"Deposit at least ${800 + abs(savings_account.balance)} to complete registration"
            ]
        }
    
    # Check active loans count
    active_loans = db.query(Loan).filter(
        Loan.borrower_id == user_id,
        Loan.status.in_(["active", "arrears"])
    ).all()
    
    if len(active_loans) >= 3:
        return {
            "eligible": False,
            "reason": "Maximum loan limit reached",
            "active_loans": len(active_loans),
            "requirements": [
                "Clear at least one active loan before applying for new loan"
            ],
            "active_loans_details": [
                {
                    "loan_number": loan.loan_number,
                    "balance": float(loan.balance),
                    "can_clear": float(user.drawdown_account.balance) >= float(loan.balance)
                }
                for loan in active_loans
            ]
        }
    
    # All checks passed
    return {
        "eligible": True,
        "loan_limit": float(savings_account.loan_limit),
        "current_savings": float(savings_account.balance),
        "active_loans": len(active_loans),
        "remaining_loan_slots": 3 - len(active_loans)
    }