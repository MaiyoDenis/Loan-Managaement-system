"""
Branch and group-related schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class BranchBase(BaseModel):
    """Base branch schema"""
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=10)
    address: Optional[str] = None
    phone_number: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')


class BranchCreate(BranchBase):
    """Branch creation schema"""
    manager_id: Optional[int] = None
    procurement_officer_id: Optional[int] = None


class BranchUpdate(BaseModel):
    """Branch update schema"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    address: Optional[str] = None
    phone_number: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    manager_id: Optional[int] = None
    procurement_officer_id: Optional[int] = None
    is_active: Optional[bool] = None


class BranchInDB(BranchBase):
    """Branch as stored in database"""
    id: int
    manager_id: Optional[int] = None
    procurement_officer_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BranchResponse(BranchInDB):
    """Branch response with related data"""
    manager_name: Optional[str] = None
    procurement_officer_name: Optional[str] = None
    total_users: int = 0
    total_groups: int = 0
    active_loans: int = 0


class BranchStats(BaseModel):
    """Branch statistics"""
    total_customers: int = 0
    total_groups: int = 0
    active_loans: int = 0
    total_loan_amount: float = 0.0
    collection_rate: float = 0.0
    arrears_amount: float = 0.0


# Group Schemas
class GroupBase(BaseModel):
    """Base group schema"""
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    max_members: int = Field(default=8, ge=1, le=20)


class GroupCreate(GroupBase):
    """Group creation schema"""
    branch_id: int
    loan_officer_id: int


class GroupUpdate(BaseModel):
    """Group update schema"""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = None
    max_members: Optional[int] = Field(None, ge=1, le=20)
    is_active: Optional[bool] = None


class GroupInDB(GroupBase):
    """Group as stored in database"""
    id: int
    branch_id: int
    loan_officer_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GroupResponse(GroupInDB):
    """Group response with additional data"""
    branch_name: str
    loan_officer_name: str
    current_members: int = 0
    total_savings: float = 0.0
    active_loans: int = 0


class GroupMembershipCreate(BaseModel):
    """Group membership creation"""
    member_id: int
    role: str = Field(default="member", pattern=r'^(member|leader|secretary)$')


class GroupMemberResponse(BaseModel):
    """Group member information"""
    id: int
    username: str
    first_name: str
    last_name: str
    phone_number: str
    role: str
    joined_at: datetime
    savings_balance: float = 0.0
    active_loans: int = 0
    
    class Config:
        from_attributes = True


class GroupTransfer(BaseModel):
    """Group transfer between branches"""
    group_id: int
    new_branch_id: int
    new_loan_officer_id: int
    transfer_reason: str