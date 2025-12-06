"""
API dependencies for authentication and authorization
"""

from typing import Generator, Optional, Set
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import verify_token
from app.core.permissions import UserRole, get_role_permissions, has_permission
from app.models.user import User, UserPermission
from app.schemas.auth import TokenData

# Security scheme
security = HTTPBearer()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify token and get user ID
        user_id = verify_token(credentials.credentials)
        if user_id is None:
            raise credentials_exception
        
        # Get user from database
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise credentials_exception
            
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        return user
        
    except (JWTError, ValueError):
        raise credentials_exception


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def get_current_user_permissions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Set[str]:
    """Get current user's permissions"""
    # Start with role-based permissions
    role_permissions = get_role_permissions(current_user.role)
    
    # Add user-specific permissions
    user_permissions = db.query(UserPermission).filter(
        UserPermission.user_id == current_user.id,
        UserPermission.is_active == True
    ).all()
    
    specific_permissions = {perm.permission_name for perm in user_permissions}
    
    return role_permissions.union(specific_permissions)


def require_permission(required_permission: str):
    """Dependency factory for permission-based access control"""
    def permission_checker(
        current_user: User = Depends(get_current_active_user),
        user_permissions: Set[str] = Depends(get_current_user_permissions)
    ) -> User:
        if not has_permission(user_permissions, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permission}"
            )
        return current_user
    
    return permission_checker


def require_role(required_role: UserRole):
    """Dependency factory for role-based access control"""
    def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role.value}"
            )
        return current_user
    
    return role_checker


def require_admin():
    """Require admin role"""
    return require_role(UserRole.ADMIN)


def require_branch_manager():
    """Require branch manager role or admin"""
    def checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in [UserRole.ADMIN, UserRole.BRANCH_MANAGER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Branch manager role required"
            )
        return current_user
    
    return checker


def get_branch_users_only(
    current_user: User = Depends(get_current_active_user)
):
    """Dependency to ensure user can only access their branch data"""
    def branch_filter(resource_branch_id: Optional[int] = None):
        # Admin can access all branches
        if current_user.role == UserRole.ADMIN:
            return True
        
        # Other roles can only access their own branch
        if resource_branch_id is None:
            return current_user.branch_id
        
        if current_user.branch_id != resource_branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access data from your branch"
            )
        
        return True
    
    return branch_filter


def validate_branch_access(
    branch_id: int,
    current_user: User = Depends(get_current_active_user)
) -> bool:
    """Validate user has access to specified branch"""
    if current_user.role == UserRole.ADMIN:
        return True
    
    if current_user.branch_id != branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this branch"
        )
    
    return True


def get_loan_officer_groups_only(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Ensure loan officer can only access their own groups"""
    if current_user.role == UserRole.ADMIN:
        return None  # Admin can access all
    
    if current_user.role != UserRole.LOAN_OFFICER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only loan officers can access group data"
        )
    
    # Return user's managed groups
    from app.models.branch import Group
    managed_groups = db.query(Group).filter(
        Group.loan_officer_id == current_user.id
    ).all()
    
    return [group.id for group in managed_groups]