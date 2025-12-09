"""
Role and Permission related database models
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Role(BaseModel):
    """Role model for user roles"""
    __tablename__ = "roles"

    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)

    users = relationship("User", back_populates="role_obj")
    permissions = relationship("RolePermission", back_populates="role")


class Permission(BaseModel):
    """Permission model for granular permissions"""
    __tablename__ = "permissions"

    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)

    roles = relationship("RolePermission", back_populates="permission")


class RolePermission(BaseModel):
    """Association table for roles and permissions"""
    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")
