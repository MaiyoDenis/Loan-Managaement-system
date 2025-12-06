"""
Payment Management API endpoints
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from decimal import Decimal
from datetime import datetime, date

from app.database import get_db
from app.models.loan import Payment, Loan, MpesaTransaction, Arrear
from app.models.user import User
from app.core.permissions import UserRole
from app.services.mpesa import mpesa_service
from app.services.sms import sms_service, SMSTemplates
from app.schemas.payment import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    ManualPaymentRequest,
    PaymentStatsResponse,
    MpesaTransactionResponse
)
from app.api.deps import (
    get_current_active_user,
    require_permission
)

router = APIRouter()


@router.get("/", response_model=List[PaymentResponse])
def get_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    loan_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """Get payments with filtering"""
    query = db.query(Payment).options(
        joinedload(Payment.loan),
        joinedload(Payment.payer),
        joinedload(Payment.confirmer)
    )
    
    # Apply role-based filtering
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(Payment.payer_id == current_user.id)
    elif current_user.role == UserRole.LOAN_OFFICER:
        # Get payments from officer's group members
        from app.models.branch import Group, GroupMembership
        managed_groups = db.query(Group).filter(Group.loan_officer_id == current_user.id).all()
        group_ids = [g.id for g in managed_groups]
        
        group_members = db.query(GroupMembership).filter(
            GroupMembership.group_id.in_(group_ids),
            GroupMembership.is_active == True
        ).all()
        member_ids = [gm.member_id for gm in group_members]
        
        query = query.filter(Payment.payer_id.in_(member_ids))
    elif current_user.role != UserRole.ADMIN:
        # Branch staff see branch payments
        branch_users = db.query(User).filter(
            User.branch_id == current_user.branch_id,
            User.role == UserRole.CUSTOMER
        ).all()
        user_ids = [u.id for u in branch_users]
        query = query.filter(Payment.payer_id.in_(user_ids))
    
    # Apply additional filters
    if loan_id:
        query = query.filter(Payment.loan_id == loan_id)
    
    if status_filter:
        query = query.filter(Payment.status == status_filter)
    
    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)
    
    if start_date:
        query = query.filter(Payment.payment_date >= start_date)
    
    if end_date:
        query = query.filter(Payment.payment_date <= end_date)
    
    # Apply branch filter for admin
    if branch_id and current_user.role == UserRole.ADMIN:
        branch_users = db.query(User).filter(
            User.branch_id == branch_id,
            User.role == UserRole.CUSTOMER
        ).all()
        user_ids = [u.id for u in branch_users]
        query = query.filter(Payment.payer_id.in_(user_ids))
    
    payments = query.order_by(desc(Payment.created_at)).offset(skip).limit(limit).all()
    
    return payments


@router.post("/manual", response_model=PaymentResponse)
async def create_manual_payment(
    payment_data: ManualPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payments:manual_entry"))
) -> Any:
    """Create manual payment entry (requires approval)"""
    
    # Get loan
    loan = db.query(Loan).filter(Loan.id == payment_data.loan_id).first()
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )
    
    # Check access permissions
    if current_user.role == UserRole.LOAN_OFFICER:
        # Verify loan belongs to officer's group member
        from app.models.branch import GroupMembership
        membership = db.query(GroupMembership).filter(
            GroupMembership.member_id == loan.borrower_id,
            GroupMembership.is_active == True
        ).first()
        
        if not membership or membership.group.loan_officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only record payments for your group members"
            )
    elif current_user.role != UserRole.ADMIN:
        if loan.borrower.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Validate payment amount
    if payment_data.amount > loan.balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount ({payment_data.amount}) exceeds loan balance ({loan.balance})"
        )
    
    # Generate payment number
    payment_number = f"MAN{datetime.now().strftime('%Y%m%d%H%M%S')}{loan.borrower_id}"
    
    # Create manual payment (pending approval)
    payment = Payment(
        payment_number=payment_number,
        loan_id=payment_data.loan_id,
        payer_id=loan.borrower_id,
        amount=payment_data.amount,
        payment_method=payment_data.payment_method,
        mpesa_transaction_code=payment_data.mpesa_code,
        payment_date=payment_data.payment_date,
        status="pending",  # Requires procurement officer approval
        created_by=current_user.id,
        notes=payment_data.notes
    )
    
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    # Notify procurement officer
    procurement_officers = db.query(User).filter(
        User.branch_id == loan.borrower.branch_id,
        User.role == UserRole.PROCUREMENT_OFFICER,
        User.is_active == True
    ).all()
    
    for officer in procurement_officers:
        await notification_service.send_notification(
            recipient_id=officer.id,
            title="Payment Approval Required",
            message=f"Manual payment of KES {payment_data.amount} needs approval for loan {loan.loan_number}",
            notification_type="approval_required",
            sender_id=current_user.id
        )
    
    return payment


@router.put("/{payment_id}/confirm", response_model=PaymentResponse)
async def confirm_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payments:confirm"))
) -> Any:
    """Confirm pending payment (Procurement Officer)"""
    
    payment = db.query(Payment).options(joinedload(Payment.loan)).filter(
        Payment.id == payment_id
    ).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment is not pending approval"
        )
    
    # Check branch access
    if current_user.role != UserRole.ADMIN:
        if payment.loan.borrower.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Confirm payment
    payment.status = "confirmed"
    payment.confirmed_by = current_user.id
    payment.confirmed_at = date.today()
    
    # Update loan
    loan = payment.loan
    loan.amount_paid += payment.amount
    loan.balance -= payment.amount
    
    # Check if loan is fully paid
    if loan.balance <= 0:
        loan.status = "completed"
        loan.balance = Decimal('0.00')
        
        # Remove from arrears if applicable
        arrears = db.query(Arrear).filter(Arrear.loan_id == loan.id).all()
        for arrear in arrears:
            arrear.status = "resolved"
            arrear.resolved_at = date.today()
    else:
        # Update next payment date if partial payments allowed
        if loan.loan_type.allows_partial_payments:
            from dateutil.relativedelta import relativedelta
            loan.next_payment_date = date.today() + relativedelta(months=1)
    
    db.commit()
    
    # Send confirmation SMS
    confirmation_message = SMSTemplates.payment_confirmation(
        loan.borrower.first_name,
        payment.amount,
        loan.loan_number,
        loan.balance,
        loan.next_payment_date.strftime('%Y-%m-%d') if loan.next_payment_date else "N/A"
    )
    
    await sms_service.send_sms(loan.borrower.phone_number, confirmation_message)
    
    # Notify loan officer
    if payment.created_by:
        await notification_service.send_notification(
            recipient_id=payment.created_by,
            title="Payment Confirmed",
            message=f"Payment of KES {payment.amount} for loan {loan.loan_number} has been confirmed",
            notification_type="payment_confirmed",
            sender_id=current_user.id
        )
    
    return payment


@router.put("/{payment_id}/reject")
async def reject_payment(
    payment_id: int,
    rejection_reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payments:confirm"))
) -> Any:
    """Reject pending payment"""
    
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment is not pending approval"
        )
    
    # Check branch access
    if current_user.role != UserRole.ADMIN:
        if payment.loan.borrower.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Reject payment
    payment.status = "rejected"
    payment.confirmed_by = current_user.id
    payment.confirmed_at = date.today()
    payment.rejection_reason = rejection_reason
    
    db.commit()
    
    # Notify loan officer
    if payment.created_by:
        await notification_service.send_notification(
            recipient_id=payment.created_by,
            title="Payment Rejected",
            message=f"Payment of KES {payment.amount} was rejected. Reason: {rejection_reason}",
            notification_type="payment_rejected",
            sender_id=current_user.id
        )
    
    return {"message": "Payment rejected successfully"}


@router.get("/stats", response_model=PaymentStatsResponse)
def get_payment_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    branch_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
) -> Any:
    """Get payment statistics"""
    
    query = db.query(Payment).filter(Payment.status == "confirmed")
    
    # Apply role-based filtering
    if current_user.role != UserRole.ADMIN:
        # Get branch customers
        branch_users = db.query(User).filter(
            User.branch_id == current_user.branch_id,
            User.role == UserRole.CUSTOMER
        ).all()
        user_ids = [u.id for u in branch_users]
        query = query.filter(Payment.payer_id.in_(user_ids))
    elif branch_id:
        branch_users = db.query(User).filter(
            User.branch_id == branch_id,
            User.role == UserRole.CUSTOMER
        ).all()
        user_ids = [u.id for u in branch_users]
        query = query.filter(Payment.payer_id.in_(user_ids))
    
    # Apply date filters
    if start_date:
        query = query.filter(Payment.payment_date >= start_date)
    if end_date:
        query = query.filter(Payment.payment_date <= end_date)
    
    payments = query.all()
    
    # Calculate statistics
    total_payments = len(payments)
    total_amount = sum(float(payment.amount) for payment in payments)
    
    # Group by payment method
    payment_methods = {}
    for payment in payments:
        method = payment.payment_method
        if method not in payment_methods:
            payment_methods[method] = {"count": 0, "amount": 0.0}
        
        payment_methods[method]["count"] += 1
        payment_methods[method]["amount"] += float(payment.amount)
    
    # Daily breakdown (last 7 days)
    daily_stats = []
    for i in range(7):
        target_date = date.today() - timedelta(days=i)
        daily_payments = [p for p in payments if p.payment_date == target_date]
        daily_amount = sum(float(p.amount) for p in daily_payments)
        
        daily_stats.append({
            "date": target_date.isoformat(),
            "count": len(daily_payments),
            "amount": daily_amount
        })
    
    return PaymentStatsResponse(
        total_payments=total_payments,
        total_amount=total_amount,
        payment_methods=payment_methods,
        daily_breakdown=daily_stats[::-1],  # Reverse to show oldest first
        average_payment=total_amount / total_payments if total_payments > 0 else 0
    )


@router.get("/pending", response_model=List[PaymentResponse])
def get_pending_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payments:confirm"))
) -> Any:
    """Get pending payments requiring approval"""
    
    query = db.query(Payment).options(
        joinedload(Payment.loan),
        joinedload(Payment.payer),
        joinedload(Payment.creator)
    ).filter(Payment.status == "pending")
    
    # Apply branch filtering for non-admin users
    if current_user.role != UserRole.ADMIN:
        branch_users = db.query(User).filter(
            User.branch_id == current_user.branch_id,
            User.role == UserRole.CUSTOMER
        ).all()
        user_ids = [u.id for u in branch_users]
        query = query.filter(Payment.payer_id.in_(user_ids))
    
    pending_payments = query.order_by(desc(Payment.created_at)).all()
    
    return pending_payments


@router.get("/mpesa-transactions", response_model=List[MpesaTransactionResponse])
def get_mpesa_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payments:view_history")),
    processed: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """Get M-Pesa transaction history"""
    
    query = db.query(MpesaTransaction)
    
    # Apply branch filtering for non-admin users
    if current_user.role != UserRole.ADMIN:
        branch_customers = db.query(User).filter(
            User.branch_id == current_user.branch_id,
            User.role == UserRole.CUSTOMER
        ).all()
        account_numbers = [c.unique_account_number for c in branch_customers if c.unique_account_number]
        query = query.filter(MpesaTransaction.account_number.in_(account_numbers))
    
    if processed is not None:
        query = query.filter(MpesaTransaction.processed == processed)
    
    transactions = query.order_by(desc(MpesaTransaction.created_at)).offset(skip).limit(limit).all()
    
    return transactions


@router.post("/initiate-mpesa")
async def initiate_mpesa_payment(
    phone_number: str,
    amount: Decimal,
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Initiate M-Pesa STK Push for loan payment"""
    
    # Get loan
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found"
        )
    
    # Check if user can initiate payment for this loan
    if current_user.role == UserRole.CUSTOMER:
        if loan.borrower_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only pay your own loans"
            )
    
    # Validate amount
    if amount > loan.balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount cannot exceed loan balance of KES {loan.balance}"
        )
    
    # Get customer account number
    account_reference = loan.borrower.unique_account_number
    if not account_reference:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer account number not found"
        )
    
    # Initiate M-Pesa payment
    result = mpesa_service.initiate_stk_push(
        phone_number=phone_number,
        amount=amount,
        account_reference=account_reference,
        transaction_desc=f"Loan payment for {loan.loan_number}"
    )
    
    if result["success"]:
        # Store payment initiation record
        payment_initiation = {
            "checkout_request_id": result["checkout_request_id"],
            "loan_id": loan_id,
            "amount": float(amount),
            "initiated_by": current_user.id,
            "initiated_at": datetime.utcnow().isoformat()
        }
        
        # TODO: Store in Redis or database for tracking
        
        return {
            "success": True,
            "message": "Payment request sent to customer's phone",
            "checkout_request_id": result["checkout_request_id"],
            "amount": float(amount),
            "loan_number": loan.loan_number
        }
    else:
        return {
            "success": False,
            "error": result["error"],
            "message": "Failed to initiate M-Pesa payment"
        }


@router.get("/overdue-analysis")
def get_overdue_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    branch_id: Optional[int] = Query(None)
) -> Any:
    """Get analysis of overdue payments and arrears"""
    
    # Build base query for loans
    query = db.query(Loan)
    
    # Apply branch filtering
    if current_user.role != UserRole.ADMIN:
        branch_users = db.query(User).filter(
            User.branch_id == current_user.branch_id,
            User.role == UserRole.CUSTOMER
        ).all()
        user_ids = [u.id for u in branch_users]
        query = query.filter(Loan.borrower_id.in_(user_ids))
    elif branch_id:
        branch_users = db.query(User).filter(
            User.branch_id == branch_id,
            User.role == UserRole.CUSTOMER
        ).all()
        user_ids = [u.id for u in branch_users]
        query = query.filter(Loan.borrower_id.in_(user_ids))
    
    # Get all active loans
    active_loans = query.filter(
        Loan.status.in_(["active", "arrears"]),
        Loan.balance > 0
    ).all()
    
    # Categorize loans
    current_loans = []
    overdue_loans = []
    arrears_loans = []
    
    for loan in active_loans:
        if loan.status == "arrears":
            arrears_loans.append(loan)
        elif loan.due_date < date.today():
            overdue_loans.append(loan)
        else:
            current_loans.append(loan)
    
    # Calculate totals
    current_amount = sum(float(loan.balance) for loan in current_loans)
    overdue_amount = sum(float(loan.balance) for loan in overdue_loans)
    arrears_amount = sum(float(loan.balance) for loan in arrears_loans)
    
    total_amount = current_amount + overdue_amount + arrears_amount
    
    # Calculate collection rate
    all_loans = query.all()
    total_disbursed = sum(float(loan.total_amount) for loan in all_loans)
    total_collected = sum(float(loan.amount_paid) for loan in all_loans)
    collection_rate = (total_collected / total_disbursed * 100) if total_disbursed > 0 else 0
    
    return {
        "summary": {
            "total_active_loans": len(active_loans),
            "current_loans": len(current_loans),
            "overdue_loans": len(overdue_loans),
            "arrears_loans": len(arrears_loans),
            "total_amount_at_risk": total_amount,
            "collection_rate": round(collection_rate, 2)
        },
        "amounts": {
            "current_amount": current_amount,
            "overdue_amount": overdue_amount,
            "arrears_amount": arrears_amount,
            "total_disbursed": total_disbursed,
            "total_collected": total_collected
        },
        "risk_distribution": {
            "low_risk": current_amount,
            "medium_risk": overdue_amount,
            "high_risk": arrears_amount
        }
    }