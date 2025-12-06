from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.models.user import User
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dummy implementations for demonstration purposes

def get_current_active_user(token: Optional[str] = Depends(oauth2_scheme)) -> User:
    # This should validate token and return user object
    # Here return a dummy user or raise exception as placeholder
    user = User()
    user.id = 1
    user.role = "ADMIN"
    user.branch_id = 1
    return user

def require_permission(permission_name: str):
    def permission_dependency(user: User = Depends(get_current_active_user)):
        # Implement permission check logic here
        # For now, allow all for demo
        if user.role != "ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return permission_dependency
