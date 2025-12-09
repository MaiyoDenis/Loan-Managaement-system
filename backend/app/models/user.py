"""
User-related database models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import BaseModel
class User(BaseModel):
    """User model for all system users"""
    __tablename__ = "users"
    
    # Basic Information
    username = Column(String(50), unique=True, nullable=False, index=True)
    phone_number = Column(String(15), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    
    # Personal Information
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    national_id = Column(String(20), unique=True, nullable=True)
    
    # System Information
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    unique_account_number = Column(String(20), unique=True, nullable=True, index=True)
    
    # Status Information
    last_login = Column(DateTime, nullable=True)
    is_online = Column(Boolean, default=False)
    password_changed_at = Column(DateTime, default=datetime.utcnow)
    must_change_password = Column(Boolean, default=True)
    
    # Relationships
    role_obj = relationship("Role", back_populates="users")
    branch = relationship("Branch", back_populates="users", foreign_keys=[branch_id])
    managed_branch = relationship("Branch", back_populates="manager", foreign_keys="Branch.manager_id")
    procurement_branch = relationship("Branch", back_populates="procurement_officer", foreign_keys="Branch.procurement_officer_id")
    
    # Group relationships
    managed_groups = relationship("Group", back_populates="loan_officer")
    group_memberships = relationship("GroupMembership", back_populates="member")
    
    # Account relationships
    savings_account = relationship("SavingsAccount", back_populates="user", uselist=False)
    drawdown_account = relationship("DrawdownAccount", back_populates="user", uselist=False)
    
    # Loan relationships
    loan_applications = relationship("LoanApplication", back_populates="applicant", foreign_keys="LoanApplication.applicant_id")
    loans = relationship("Loan", back_populates="borrower")
    
    # Activity tracking
    activity_logs = relationship("ActivityLog", back_populates="user")
    user_sessions = relationship("UserSession", back_populates="user")
    
    # Notifications
    sent_notifications = relationship("Notification", foreign_keys="Notification.sender_id", back_populates="sender")
    received_notifications = relationship("Notification", foreign_keys="Notification.recipient_id", back_populates="recipient")
    
    def __repr__(self):
        return f"<User(username='{self.username}')>"


class UserSession(BaseModel):
    """Track user login sessions"""
    __tablename__ = "user_sessions"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    login_time = Column(DateTime, default=datetime.utcnow)
    logout_time = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)  # Support IPv6
    user_agent = Column(Text, nullable=True)
    session_token = Column(String(255), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="user_sessions")
    
    @property
    def is_active(self):
        return self.logout_time is None
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, active={self.is_active})>"