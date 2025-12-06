"""
User-related Pydantic schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from app.core.permissions import UserRole


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
    role: UserRole
    branch_id: Optional[int] = None
    must_change_password: bool = True
    
    @validator('password')
    def validate_password_strength(cls, v):
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')  
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        return v


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


class UserInDB(UserBase):
    """User as stored in database"""
    id: int
    role: UserRole
    branch_id: Optional[int] = None
    unique_account_number: Optional[str] = None
    is_active: bool
    last_login: Optional[datetime] = None
    is_online: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserResponse(UserInDB):
    """User response schema (excludes sensitive data)"""
    pass


class UserWithPermissions(UserResponse):
    """User with permissions"""
    permissions: List[str] = []


class UserTransfer(BaseModel):
    """User transfer schema"""
    user_id: int
    new_branch_id: Optional[int] = None
    new_group_id: Optional[int] = None
    transfer_reason: str


class CustomerCreate(BaseModel):
    """Customer creation by loan officer"""
    phone_number: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    national_id: Optional[str] = Field(None, max_length=20)
    group_id: int


class UserSessionResponse(BaseModel):
    """User session information"""
    id: int
    login_time: datetime
    logout_time: Optional[datetime] = None
    ip_address: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True


class OnlineUsersResponse(BaseModel):
    """Online users summary"""
    total_online: int
    by_role: dict = {}
    users: List[UserResponse] = []