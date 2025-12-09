"""
Branch related schemas
"""

from typing import Optional
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


class BranchResponse(BranchBase):
    """Branch response schema"""
    id: int
    is_active: bool
    manager_id: Optional[int] = None
    procurement_officer_id: Optional[int] = None

    class Config:
        orm_mode = True
