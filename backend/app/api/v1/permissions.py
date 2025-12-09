"""
Permissions and roles management API endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Role, Permission, RolePermission, User
from app.schemas.permission import RoleCreate, RoleResponse, PermissionCreate, PermissionResponse, RolePermissionRequest
from app.api.deps import get_current_active_user, require_role

router = APIRouter()


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
@require_role("admin")
def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new role (Admin only)
    """
    if db.query(Role).filter(Role.name == role_data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists"
        )

    new_role = Role(**role_data.dict())
    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    return new_role


@router.get("/roles", response_model=List[RoleResponse])
@require_role("admin")
def get_all_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all roles (Admin only)
    """
    return db.query(Role).all()


@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
@require_role("admin")
def create_permission(
    permission_data: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new permission (Admin only)
    """
    if db.query(Permission).filter(Permission.name == permission_data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission with this name already exists"
        )

    new_permission = Permission(**permission_data.dict())
    db.add(new_permission)
    db.commit()
    db.refresh(new_permission)

    return new_permission


@router.get("/permissions", response_model=List[PermissionResponse])
@require_role("admin")
def get_all_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all permissions (Admin only)
    """
    return db.query(Permission).all()


@router.post("/roles/assign-permission", status_code=status.HTTP_201_CREATED)
@require_role("admin")
def assign_permission_to_role(
    role_permission_data: RolePermissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Assign a permission to a role (Admin only)
    """
    role = db.query(Role).filter(Role.id == role_permission_data.role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    permission = db.query(Permission).filter(Permission.id == role_permission_data.permission_id).first()
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    existing_assignment = db.query(RolePermission).filter(
        RolePermission.role_id == role.id,
        RolePermission.permission_id == permission.id
    ).first()

    if existing_assignment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Permission already assigned to this role")

    new_assignment = RolePermission(role_id=role.id, permission_id=permission.id)
    db.add(new_assignment)
    db.commit()

    return {"message": "Permission assigned to role successfully"}
