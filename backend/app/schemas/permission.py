"""
Pydantic schemas for permissions and roles
"""

from pydantic import BaseModel
from typing import Optional


class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    pass


class PermissionResponse(PermissionBase):
    id: int

    class Config:
        orm_mode = True


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    pass


class RoleResponse(RoleBase):
    id: int

    class Config:
        orm_mode = True


class RolePermissionRequest(BaseModel):
    role_id: int
    permission_id: int
