"""
Branch and group-related models
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Branch(BaseModel):
    """Branch model"""
    __tablename__ = "branches"
    
    # Basic Information
    name = Column(String(100), nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    address = Column(Text, nullable=True)
    phone_number = Column(String(15), nullable=True)
    
    # Management
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    procurement_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    users = relationship("User", back_populates="branch", foreign_keys="User.branch_id")
    manager = relationship("User", back_populates="managed_branch", foreign_keys=[manager_id])
    procurement_officer = relationship("User", back_populates="procurement_branch", foreign_keys=[procurement_officer_id])
    
    # Groups and inventory
    groups = relationship("Group", back_populates="branch")
    inventory_items = relationship("BranchInventory", back_populates="branch")
    loan_types = relationship("LoanType", back_populates="branch")
    
    def __repr__(self):
        return f"<Branch(name='{self.name}', code='{self.code}')>"


class Group(BaseModel):
    """Customer group model"""
    __tablename__ = "groups"
    
    # Basic Information
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    max_members = Column(Integer, default=8)
    
    # Management
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    loan_officer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    branch = relationship("Branch", back_populates="groups")
    loan_officer = relationship("User", back_populates="managed_groups")
    memberships = relationship("GroupMembership", back_populates="group")
    loan_applications = relationship("LoanApplication", back_populates="group")
    
    @property
    def current_members(self):
        return len([m for m in self.memberships if m.is_active])
    
    @property
    def is_full(self):
        return self.current_members >= self.max_members
    
    def __repr__(self):
        return f"<Group(name='{self.name}', members={self.current_members}/{self.max_members})>"


class GroupMembership(BaseModel):
    """Group membership tracking"""
    __tablename__ = "group_memberships"
    
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(String, nullable=False)  # Will be set to created_at
    role = Column(String(20), default="member")  # member, leader, secretary
    
    # Relationships
    group = relationship("Group", back_populates="memberships")
    member = relationship("User", back_populates="group_memberships")
    
    def __repr__(self):
        return f"<GroupMembership(group_id={self.group_id}, member_id={self.member_id})>"