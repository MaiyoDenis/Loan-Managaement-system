"""
User-related Pydantic schemas
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50)
    phone_number: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    email: Optional[EmailStr] = None
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    national_id: Optional[str] = Field(None, max_length=20)


class UserCreate(UserBase):
    """User creation schema"""
    password: str = Field(..., min_length=8)
    role_id: int
    branch_id: Optional[int] = None


class UserUpdate(BaseModel):
    """User update schema"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    phone_number: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    national_id: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    branch_id: Optional[int] = None
    role_id: Optional[int] = None


class UserResponse(UserBase):
    """User response schema (excludes sensitive data)"""
    id: int
    role_id: int
    branch_id: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True

class CustomerCreate(BaseModel):
    """Customer creation by loan officer"""
    phone_number: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    national_id: Optional[str] = Field(None, max_length=20)
    group_id: int
