"""
Account Management API endpoints (Savings & Drawdown)
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime

from app.database import get_db
from app.models.loan import SavingsAccount, DrawdownAccount, Transaction
from app.models.user import User
from app.core.permissions import UserRole
from app.core.config import settings
from app.schemas.account import (
    AccountResponse,
    TransactionCreate,
    TransactionResponse,
    AccountTransferRequest,
    AccountSummaryResponse
)
from app.api.deps import (
    get_current_active_user,
    require_permission
)

router = APIRouter()


@router.get("/savings", response_model=List[AccountResponse])
def get_savings_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    branch_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None)
) -> Any:
    """Get savings accounts"""
    query = db.query(SavingsAccount).join(User)
    
    # Apply branch filtering
    if current_user.role != UserRole.ADMIN:
        query = query.filter(User.branch_id == current_user.branch_id)
    elif branch_id:
        query = query.filter(User.branch_id == branch_id)
    
    # Apply status filtering
    if status:
        if status == "active":
            query = query.filter(SavingsAccount.registration_fee_paid == True)
        elif status == "pending":
            query = query.filter(SavingsAccount.registration_fee_paid == False)
    
    accounts = query.all()
    
    # Convert to response format
    response_accounts = []
    for account in accounts:
        response_accounts.append(AccountResponse(
            id=account.id,
            user_id=account.user_id,
            account_number=account.account_number,
            account_type="savings",
            balance=float(account.balance),
            status=account.status,
            registration_fee_paid=account.registration_fee_paid,
            loan_limit=float(account.loan_limit),
            created_at=account.created_at,
            user_name=f"{account.user.first_name} {account.user.last_name}",
            user_phone=account.user.phone_number
        ))
    
    return response_accounts


@router.get("/drawdown", response_model=List[AccountResponse])
def get_drawdown_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    branch_id: Optional[int] = Query(None)
) -> Any:
    """Get drawdown accounts"""
    query = db.query(DrawdownAccount).join(User)
    
    # Apply branch filtering
    if current_user.role != UserRole.ADMIN:
        query = query.filter(User.branch_id == current_user.branch_id)
    elif branch_id:
        query = query.filter(User.branch_id == branch_id)
    
    accounts = query.all()
    
    # Convert to response format
    response_accounts = []
    for account in accounts:
        response_accounts.append(AccountResponse(
            id=account.id,
            user_id=account.user_id,
            account_number=account.account_number,
            account_type="drawdown",
            balance=float(account.balance),
            status="active",
            created_at=account.created_at,
            user_name=f"{account.user.first_name} {account.user.last_name}",
            user_phone=account.user.phone_number
        ))
    
    return response_accounts


@router.get("/user/{user_id}/summary", response_model=AccountSummaryResponse)
def get_user_account_summary(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get account summary for a specific user"""
    # Get target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check access permissions
    if current_user.role == UserRole.CUSTOMER:
        if current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own account information"
            )
    elif current_user.role != UserRole.ADMIN:
        if target_user.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this user's account"
            )
    
    # Get accounts
    savings_account = db.query(SavingsAccount).filter(SavingsAccount.user_id == user_id).first()
    drawdown_account = db.query(DrawdownAccount).filter(DrawdownAccount.user_id == user_id).first()
    
    if not savings_account or not drawdown_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User accounts not found"
        )
    
    # Get active loans count and total
    from app.models.loan import Loan
    active_loans = db.query(Loan).filter(
        Loan.borrower_id == user_id,
        Loan.status.in_(["active", "arrears"])
    ).all()
    
    total_loan_balance = sum(float(loan.balance) for loan in active_loans)
    
    # Get recent transactions
    recent_transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(Transaction.created_at.desc()).limit(5).all()
    
    return AccountSummaryResponse(
        user_id=user_id,
        user_name=f"{target_user.first_name} {target_user.last_name}",
        savings_balance=float(savings_account.balance),
        drawdown_balance=float(drawdown_account.balance),
        loan_limit=float(savings_account.loan_limit),
        registration_status=savings_account.status,
        active_loans_count=len(active_loans),
        total_loan_balance=total_loan_balance,
        recent_transactions=[
            TransactionResponse.from_orm(tx) for tx in recent_transactions
        ]
    )


@router.post("/transfer", response_model=TransactionResponse)
def transfer_funds(
    transfer_data: AccountTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Transfer funds between savings and drawdown accounts"""
    # Validate access - customers can only transfer their own funds
    if current_user.role == UserRole.CUSTOMER:
        if current_user.id != transfer_data.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only transfer your own funds"
            )
    elif current_user.role != UserRole.ADMIN:
        # Loan officers can transfer for their group members
        target_user = db.query(User).filter(User.id == transfer_data.user_id).first()
        if not target_user or target_user.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Get accounts
    savings_account = db.query(SavingsAccount).filter(
        SavingsAccount.user_id == transfer_data.user_id
    ).first()
    drawdown_account = db.query(DrawdownAccount).filter(
        DrawdownAccount.user_id == transfer_data.user_id
    ).first()
    
    if not savings_account or not drawdown_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User accounts not found"
        )
    
    amount = transfer_data.amount
    
    # Determine source and destination accounts
    if transfer_data.from_account == "savings":
        source_account = savings_account
        dest_account = drawdown_account
        source_type = "savings"
        dest_type = "drawdown"
    else:
        source_account = drawdown_account
        dest_account = savings_account
        source_type = "drawdown"
        dest_type = "savings"
    
    # Check sufficient balance
    if source_account.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance for transfer"
        )
    
    # Perform transfer
    source_balance_before = source_account.balance
    dest_balance_before = dest_account.balance
    
    source_account.balance -= amount
    dest_account.balance += amount
    
    # Generate transaction number
    transaction_number = f"TRF{datetime.now().strftime('%Y%m%d%H%M%S')}{transfer_data.user_id}"
    
    # Create withdrawal transaction
    withdrawal_transaction = Transaction(
        transaction_number=f"{transaction_number}W",
        user_id=transfer_data.user_id,
        account_id=source_account.id,
        account_type=source_type,
        transaction_type="transfer",
        amount=amount,
        balance_before=source_balance_before,
        balance_after=source_account.balance,
        description=f"Transfer to {dest_type} account",
        processed_by=current_user.id
    )
    
    # Create deposit transaction
    deposit_transaction = Transaction(
        transaction_number=f"{transaction_number}D",
        user_id=transfer_data.user_id,
        account_id=dest_account.id,
        account_type=dest_type,
        transaction_type="transfer",
        amount=amount,
        balance_before=dest_balance_before,
        balance_after=dest_account.balance,
        description=f"Transfer from {source_type} account",
        reference_number=f"{transaction_number}W",  # Link transactions
        processed_by=current_user.id
    )
    
    db.add(withdrawal_transaction)
    db.add(deposit_transaction)
    db.commit()
    
    # Return the deposit transaction as confirmation
    db.refresh(deposit_transaction)
    return deposit_transaction


@router.post("/deposit", response_model=TransactionResponse)
def deposit_funds(
    user_id: int,
    amount: Decimal,
    account_type: str,
    description: Optional[str] = None,
    reference_number: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payments:manual_entry"))
) -> Any:
    """Deposit funds to user account"""
    # Get target account
    if account_type == "savings":
        account = db.query(SavingsAccount).filter(SavingsAccount.user_id == user_id).first()
    else:
        account = db.query(DrawdownAccount).filter(DrawdownAccount.user_id == user_id).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{account_type.title()} account not found"
        )
    
    # Check access permissions
    if current_user.role != UserRole.ADMIN:
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user or target_user.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Process deposit
    balance_before = account.balance
    account.balance += amount
    
    # Handle registration fee deduction for savings account
    if account_type == "savings" and not account.registration_fee_paid:
        if account.balance >= 0:  # Now positive balance
            account.registration_fee_paid = True
    
    # Create transaction record
    transaction_number = f"DEP{datetime.now().strftime('%Y%m%d%H%M%S')}{user_id}"
    
    transaction = Transaction(
        transaction_number=transaction_number,
        user_id=user_id,
        account_id=account.id,
        account_type=account_type,
        transaction_type="deposit",
        amount=amount,
        balance_before=balance_before,
        balance_after=account.balance,
        description=description or f"Deposit to {account_type} account",
        reference_number=reference_number,
        processed_by=current_user.id
    )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    return transaction


@router.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    user_id: Optional[int] = Query(None),
    account_type: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """Get transaction history"""
    query = db.query(Transaction)
    
    # Apply user filter
    if user_id:
        # Check access permissions
        if current_user.role == UserRole.CUSTOMER:
            if current_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own transactions"
                )
        elif current_user.role != UserRole.ADMIN:
            target_user = db.query(User).filter(User.id == user_id).first()
            if not target_user or target_user.branch_id != current_user.branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        query = query.filter(Transaction.user_id == user_id)
    elif current_user.role == UserRole.CUSTOMER:
        # Customers only see their own transactions
        query = query.filter(Transaction.user_id == current_user.id)
    elif current_user.role != UserRole.ADMIN:
        # Other roles see branch transactions
        branch_users = db.query(User).filter(User.branch_id == current_user.branch_id).all()
        user_ids = [u.id for u in branch_users]
        query = query.filter(Transaction.user_id.in_(user_ids))
    
    # Apply additional filters
    if account_type:
        query = query.filter(Transaction.account_type == account_type)
    
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    # Order by most recent first
    transactions = query.order_by(Transaction.created_at.desc()).offset(skip).limit(limit).all()
    
    return transactions