"""
Account-related Pydantic schemas
"""

from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class AccountResponse(BaseModel):
    """Account response schema"""
    id: int
    user_id: int
    account_number: str
    account_type: str  # 'savings' or 'drawdown'
    balance: float
    status: str
    created_at: datetime
    
    # User information
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    
    # Savings account specific
    registration_fee_paid: Optional[bool] = None
    loan_limit: Optional[float] = None
    
    class Config:
        from_attributes = True


class TransactionCreate(BaseModel):
    """Transaction creation"""
    user_id: int
    account_type: str = Field(..., pattern="^(savings|drawdown)$")
    transaction_type: str
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    description: Optional[str] = None
    reference_number: Optional[str] = None


class TransactionResponse(BaseModel):
    """Transaction response"""
    id: int
    transaction_number: str
    user_id: int
    account_type: str
    transaction_type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    description: Optional[str] = None
    reference_number: Optional[str] = None
    processed_by: Optional[int] = None
    created_at: datetime
    
    # Additional information
    processed_by_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class AccountTransferRequest(BaseModel):
    """Account transfer request"""
    user_id: int
    from_account: str = Field(..., regex="^(savings|drawdown)$")
    to_account: str = Field(..., regex="^(savings|drawdown)$")
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    description: Optional[str] = None
    
    @validator('to_account')
    def accounts_must_be_different(cls, v, values):
        if 'from_account' in values and v == values['from_account']:
            raise ValueError('Source and destination accounts must be different')
        return v


class AccountSummaryResponse(BaseModel):
    """Account summary for a user"""
    user_id: int
    user_name: str
    savings_balance: float
    drawdown_balance: float
    loan_limit: float
    registration_status: str
    active_loans_count: int
    total_loan_balance: float
    recent_transactions: List[TransactionResponse] = []


class DepositRequest(BaseModel):
    """Deposit request"""
    user_id: int
    account_type: str = Field(..., regex="^(savings|drawdown)$")
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_method: str = Field(default="cash", regex="^(cash|mpesa|bank_transfer)$")
    reference_number: Optional[str] = None
    description: Optional[str] = None