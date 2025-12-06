"""
Loan Management Models
"""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, Text, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from app.models.base import Base


class LoanProduct(Base):
    """Loan product model"""
    __tablename__ = "loan_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    buying_price = Column(Numeric(10, 2), nullable=False)
    selling_price = Column(Numeric(10, 2), nullable=False)
    profit_margin = Column(Numeric(5, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Loan(Base):
    """Loan model"""
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    loan_number = Column(String(50), unique=True, nullable=False)
    borrower_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    loan_product_id = Column(Integer, ForeignKey("loan_products.id"))
    total_amount = Column(Numeric(15, 2), nullable=False)
    interest_amount = Column(Numeric(15, 2), default=0)
    charge_fee_amount = Column(Numeric(15, 2), default=0)
    balance = Column(Numeric(15, 2), nullable=False)
    status = Column(String(20), default="active")  # active, completed, arrears
    start_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    next_payment_date = Column(Date)
    next_payment_amount = Column(Numeric(15, 2))
    is_overdue = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    borrower = relationship("User", back_populates="loans")
    loan_product = relationship("LoanProduct")
    payments = relationship("Payment", back_populates="loan")


class Payment(Base):
    """Payment model"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_number = Column(String(50), unique=True, nullable=False)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    payment_date = Column(Date, nullable=False)
    payment_method = Column(String(20), default="cash")
    status = Column(String(20), default="confirmed")  # pending, confirmed, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    loan = relationship("Loan", back_populates="payments")


class SavingsAccount(Base):
    """Savings account model"""
    __tablename__ = "savings_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_number = Column(String(20), unique=True, nullable=False)
    balance = Column(Numeric(15, 2), default=0)
    registration_fee_paid = Column(Boolean, default=False)
    loan_limit = Column(Numeric(15, 2), default=0)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="savings_account")


class DrawdownAccount(Base):
    """Drawdown account model"""
    __tablename__ = "drawdown_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_number = Column(String(20), unique=True, nullable=False)
    balance = Column(Numeric(15, 2), default=0)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="drawdown_account")


class BranchInventory(Base):
    """Branch inventory model"""
    __tablename__ = "branch_inventory"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    loan_product_id = Column(Integer, ForeignKey("loan_products.id"), nullable=False)
    current_quantity = Column(Integer, default=0)
    reorder_point = Column(Integer, default=0)
    critical_point = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    branch = relationship("Branch", back_populates="inventory")
    loan_product = relationship("LoanProduct")


class LoanApplication(Base):
    """Loan application model"""
    __tablename__ = "loan_applications"

    id = Column(Integer, primary_key=True, index=True)
    application_number = Column(String(50), unique=True, nullable=False)
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"))
    loan_product_id = Column(Integer, ForeignKey("loan_products.id"))
    requested_amount = Column(Numeric(15, 2), nullable=False)
    status = Column(String(20), default="submitted")  # submitted, pending, under_review, approved, rejected, disbursed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applicant = relationship("User")
    group = relationship("Group")
    loan_product = relationship("LoanProduct")
    products = relationship("LoanApplicationProduct", back_populates="application")


class LoanApplicationProduct(Base):
    """Loan application product model"""
    __tablename__ = "loan_application_products"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("loan_applications.id"), nullable=False)
    loan_product_id = Column(Integer, ForeignKey("loan_products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(15, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("LoanApplication", back_populates="products")
    loan_product = relationship("LoanProduct")


class Transaction(Base):
    """Transaction model"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_number = Column(String(50), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # deposit, withdrawal, payment, transfer
    account_type = Column(String(20), nullable=False)  # savings, drawdown
    amount = Column(Numeric(15, 2), nullable=False)
    balance_after = Column(Numeric(15, 2), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
