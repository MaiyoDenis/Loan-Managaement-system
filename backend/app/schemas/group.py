"""
Group related schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


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


class GroupResponse(GroupBase):
    """Group response with additional data"""
    id: int
    branch_id: int
    loan_officer_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
