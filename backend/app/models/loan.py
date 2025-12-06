"""
Loan and financial-related models
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Text, DECIMAL, Boolean, Date, Enum, JSON
from sqlalchemy.orm import relationship, foreign
from decimal import Decimal
from enum import Enum as PyEnum

from app.models.base import BaseModel


class LoanStatus(str, PyEnum):
    """Loan status enumeration"""
    ACTIVE = "active"
    COMPLETED = "completed"
    DEFAULTED = "defaulted"
    ARREARS = "arrears"


class ApplicationStatus(str, PyEnum):
    """Loan application status enumeration"""
    SUBMITTED = "submitted"
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    ON_HOLD = "on_hold"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"


class PaymentStatus(str, PyEnum):
    """Payment status enumeration"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class TransactionType(str, PyEnum):
    """Transaction type enumeration"""
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    LOAN_REPAYMENT = "loan_repayment"
    LOAN_DISBURSEMENT = "loan_disbursement"
    FEE_DEDUCTION = "fee_deduction"


class SavingsAccount(BaseModel):
    """Customer savings account"""
    __tablename__ = "savings_accounts"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    account_number = Column(String(20), unique=True, nullable=False)
    balance = Column(DECIMAL(15, 2), default=Decimal('0.00'))
    
    # Registration tracking
    registration_fee_paid = Column(Boolean, default=False)
    registration_fee_amount = Column(DECIMAL(10, 2), default=Decimal('800.00'))
    
    # Relationships
    user = relationship("User", back_populates="savings_account")
    transactions = relationship("Transaction", primaryjoin="and_(SavingsAccount.id == foreign(Transaction.account_id), Transaction.account_type == 'savings')")
    
    @property
    def loan_limit(self):
        """Calculate available loan limit (4x savings)"""
        from app.core.config import settings
        return self.balance * settings.DEFAULT_LOAN_LIMIT_MULTIPLIER
    
    @property
    def status(self):
        """Account status based on registration fee"""
        return "active" if self.registration_fee_paid else "pending"
    
    def __repr__(self):
        return f"<SavingsAccount(account_number='{self.account_number}', balance={self.balance})>"


class DrawdownAccount(BaseModel):
    """Customer drawdown/loan repayment account"""
    __tablename__ = "drawdown_accounts"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    account_number = Column(String(20), unique=True, nullable=False)
    balance = Column(DECIMAL(15, 2), default=Decimal('0.00'))
    
    # Relationships
    user = relationship("User", back_populates="drawdown_account")
    transactions = relationship("Transaction", primaryjoin="and_(DrawdownAccount.id == foreign(Transaction.account_id), Transaction.account_type == 'drawdown')", overlaps="transactions")
    
    def __repr__(self):
        return f"<DrawdownAccount(account_number='{self.account_number}', balance={self.balance})>"


class ProductCategory(BaseModel):
    """Product category for loan products"""
    __tablename__ = "product_categories"
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    creator = relationship("User")
    loan_products = relationship("LoanProduct", back_populates="category")
    
    def __repr__(self):
        return f"<ProductCategory(name='{self.name}')>"


class LoanProduct(BaseModel):
    """Physical products available for loans"""
    __tablename__ = "loan_products"
    
    name = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=False)
    description = Column(Text, nullable=True)
    
    # Pricing (buying price is secret - admin only)
    buying_price = Column(DECIMAL(12, 2), nullable=False)
    selling_price = Column(DECIMAL(12, 2), nullable=False)
    
    # Media
    image_url = Column(String(255), nullable=True)
    
    # Tracking
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    category = relationship("ProductCategory", back_populates="loan_products")
    creator = relationship("User")
    inventory_items = relationship("BranchInventory", back_populates="loan_product")
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.buying_price > 0:
            return ((self.selling_price - self.buying_price) / self.buying_price) * 100
        return 0
    
    def __repr__(self):
        return f"<LoanProduct(name='{self.name}', selling_price={self.selling_price})>"


class LoanType(BaseModel):
    """Loan type with terms and conditions"""
    __tablename__ = "loan_types"
    
    name = Column(String(100), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)  # Branch-specific or global
    
    # Loan parameters
    min_amount = Column(DECIMAL(12, 2), nullable=False)
    max_amount = Column(DECIMAL(12, 2), nullable=False)
    interest_rate = Column(DECIMAL(5, 2), nullable=False)  # Percentage
    charge_fee_rate = Column(DECIMAL(5, 2), default=Decimal('0.00'))  # Optional charge fee
    period_months = Column(Integer, nullable=False)
    
    # Payment options
    allows_partial_payments = Column(Boolean, default=False)
    
    # Tracking
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    branch = relationship("Branch", back_populates="loan_types")
    creator = relationship("User")
    loan_applications = relationship("LoanApplication", back_populates="loan_type")
    loans = relationship("Loan", back_populates="loan_type")
    
    def calculate_total_amount(self, principal: Decimal) -> dict:
        """Calculate total loan amount including interest and fees"""
        interest_amount = principal * (self.interest_rate / 100)
        charge_fee_amount = principal * (self.charge_fee_rate / 100)
        total_amount = principal + interest_amount + charge_fee_amount
        
        return {
            "principal": principal,
            "interest": interest_amount,
            "charge_fee": charge_fee_amount,
            "total": total_amount
        }
    
    def __repr__(self):
        return f"<LoanType(name='{self.name}', rate={self.interest_rate}%)>"


class BranchInventory(BaseModel):
    """Branch-specific inventory tracking"""
    __tablename__ = "branch_inventory"
    
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    loan_product_id = Column(Integer, ForeignKey("loan_products.id"), nullable=False)
    
    # Inventory levels
    current_quantity = Column(Integer, default=0)
    reorder_point = Column(Integer, default=5)
    critical_point = Column(Integer, default=2)
    
    # Tracking
    last_restocked_at = Column(Date, nullable=True)
    last_restocked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    branch = relationship("Branch", back_populates="inventory_items")
    loan_product = relationship("LoanProduct", back_populates="inventory_items")
    restocked_by = relationship("User")
    
    @property
    def status(self):
        """Inventory status based on quantity levels"""
        if self.current_quantity <= self.critical_point:
            return "critical"
        elif self.current_quantity <= self.reorder_point:
            return "low"
        else:
            return "ok"
    
    def __repr__(self):
        return f"<BranchInventory(product='{self.loan_product.name}', qty={self.current_quantity}, status='{self.status}')>"


class LoanApplication(BaseModel):
    """Loan application model"""
    __tablename__ = "loan_applications"
    
    application_number = Column(String(20), unique=True, nullable=False)
    
    # Applicant information
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    loan_officer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Loan details
    loan_type_id = Column(Integer, ForeignKey("loan_types.id"), nullable=False)
    total_amount = Column(DECIMAL(15, 2), nullable=False)
    
    # Status tracking
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.SUBMITTED)
    
    # Review process
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(Date, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Disbursement
    disbursed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    disbursed_at = Column(Date, nullable=True)
    
    # Relationships
    applicant = relationship("User", back_populates="loan_applications", foreign_keys=[applicant_id])
    group = relationship("Group", back_populates="loan_applications")
    loan_officer = relationship("User", foreign_keys=[loan_officer_id])
    loan_type = relationship("LoanType", back_populates="loan_applications")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    disburser = relationship("User", foreign_keys=[disbursed_by])
    
    # Products in application
    application_products = relationship("LoanApplicationProduct", back_populates="loan_application")
    
    # Generated loan
    loan = relationship("Loan", back_populates="loan_application", uselist=False)
    
    def __repr__(self):
        return f"<LoanApplication(number='{self.application_number}', status='{self.status}')>"


class LoanApplicationProduct(BaseModel):
    """Products included in a loan application"""
    __tablename__ = "loan_application_products"
    
    loan_application_id = Column(Integer, ForeignKey("loan_applications.id", ondelete="CASCADE"), nullable=False)
    loan_product_id = Column(Integer, ForeignKey("loan_products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(DECIMAL(12, 2), nullable=False)
    total_price = Column(DECIMAL(12, 2), nullable=False)
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="application_products")
    loan_product = relationship("LoanProduct")
    
    def __repr__(self):
        return f"<LoanApplicationProduct(product='{self.loan_product.name}', qty={self.quantity})>"


class Loan(BaseModel):
    """Active loan model"""
    __tablename__ = "loans"
    
    loan_number = Column(String(20), unique=True, nullable=False)
    loan_application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=False)
    
    # Borrower
    borrower_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    loan_type_id = Column(Integer, ForeignKey("loan_types.id"), nullable=False)
    
    # Loan amounts
    principal_amount = Column(DECIMAL(15, 2), nullable=False)
    interest_amount = Column(DECIMAL(15, 2), nullable=False)
    charge_fee_amount = Column(DECIMAL(15, 2), default=Decimal('0.00'))
    total_amount = Column(DECIMAL(15, 2), nullable=False)
    
    # Payment tracking
    amount_paid = Column(DECIMAL(15, 2), default=Decimal('0.00'))
    balance = Column(DECIMAL(15, 2), nullable=False)
    
    # Schedule
    start_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    next_payment_date = Column(Date, nullable=True)
    next_payment_amount = Column(DECIMAL(12, 2), nullable=True)
    
    # Status
    status = Column(Enum(LoanStatus), default=LoanStatus.ACTIVE)
    
    # Relationships
    loan_application = relationship("LoanApplication", back_populates="loan")
    borrower = relationship("User", back_populates="loans")
    loan_type = relationship("LoanType", back_populates="loans")
    payments = relationship("Payment", back_populates="loan")
    arrears = relationship("Arrear", back_populates="loan")
    
    @property
    def payment_progress(self):
        """Calculate payment progress percentage"""
        if self.total_amount > 0:
            return (self.amount_paid / self.total_amount) * 100
        return 0
    
    @property
    def is_overdue(self):
        """Check if loan is overdue"""
        from datetime import date
        return self.due_date < date.today() and self.status == LoanStatus.ACTIVE
    
    def __repr__(self):
        return f"<Loan(number='{self.loan_number}', balance={self.balance}, status='{self.status}')>"


class Transaction(BaseModel):
    """Financial transaction model"""
    __tablename__ = "transactions"
    
    transaction_number = Column(String(30), unique=True, nullable=False)
    
    # Account information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, nullable=False)  # savings_account.id or drawdown_account.id
    account_type = Column(String(20), nullable=False)  # 'savings' or 'drawdown'
    
    # Transaction details
    transaction_type = Column(Enum(TransactionType), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    balance_before = Column(DECIMAL(15, 2), nullable=False)
    balance_after = Column(DECIMAL(15, 2), nullable=False)
    
    # Additional information
    description = Column(Text, nullable=True)
    reference_number = Column(String(50), nullable=True)  # M-Pesa code, etc.
    
    # Processing
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    processor = relationship("User", foreign_keys=[processed_by])
    
    def __repr__(self):
        return f"<Transaction(number='{self.transaction_number}', type='{self.transaction_type}', amount={self.amount})>"


class Payment(BaseModel):
    """Loan payment model"""
    __tablename__ = "payments"
    
    payment_number = Column(String(20), unique=True, nullable=False)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    payer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Payment details
    amount = Column(DECIMAL(12, 2), nullable=False)
    payment_method = Column(String(20), nullable=False)  # 'mpesa', 'cash', 'bank_transfer', 'drawdown_auto'
    mpesa_transaction_code = Column(String(20), nullable=True)
    
    # Status and confirmation
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_at = Column(Date, nullable=True)
    payment_date = Column(Date, nullable=False)
    
    # Manual entry tracking
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    loan = relationship("Loan", back_populates="payments")
    payer = relationship("User", foreign_keys=[payer_id])
    confirmer = relationship("User", foreign_keys=[confirmed_by])
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<Payment(number='{self.payment_number}', amount={self.amount}, status='{self.status}')>"


class Arrear(BaseModel):
    """Arrears/overdue loan tracking"""
    __tablename__ = "arrears"
    
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    amount_overdue = Column(DECIMAL(12, 2), nullable=False)
    days_overdue = Column(Integer, nullable=False)
    
    # Grace period tracking
    grace_period_end = Column(Date, nullable=True)
    
    # Collection assignment
    assigned_collector_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Status
    status = Column(String(20), default="new")  # new, in_progress, resolved, written_off
    resolved_at = Column(Date, nullable=True)
    
    # Relationships
    loan = relationship("Loan", back_populates="arrears")
    assigned_collector = relationship("User")
    
    def __repr__(self):
        return f"<Arrear(loan_id={self.loan_id}, amount={self.amount_overdue}, days={self.days_overdue})>"


class ActivityLog(BaseModel):
    """System activity audit log"""
    __tablename__ = "activity_logs"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)  # 'user', 'loan', 'payment', etc.
    resource_id = Column(Integer, nullable=True)
    
    # Change tracking
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    
    # Request information
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="activity_logs")
    
    def __repr__(self):
        return f"<ActivityLog(user_id={self.user_id}, action='{self.action}', resource='{self.resource_type}')>"


class Notification(BaseModel):
    """System notification model"""
    __tablename__ = "notifications"
    
    # Recipients
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for broadcast
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Message content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(20), nullable=False)  # 'system', 'payment', 'reminder', 'alert', 'custom'
    
    # Targeting
    target_type = Column(String(20), default="individual")  # 'individual', 'group', 'branch', 'all'
    target_id = Column(Integer, nullable=True)  # group_id or branch_id if applicable
    
    # Status
    is_read = Column(Boolean, default=False)
    sent_via_sms = Column(Boolean, default=False)
    sent_via_email = Column(Boolean, default=False)
    
    # Relationships
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_notifications")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_notifications")
    
    def __repr__(self):
        return f"<Notification(type='{self.notification_type}', target='{self.target_type}')>"