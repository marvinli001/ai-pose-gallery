"""
认证依赖项
"""
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User, UserRole

security = HTTPBearer(auto_error=False)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """获取认证服务"""
    return AuthService(db)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session_token: Optional[str] = Cookie(None),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[User]:
    """获取当前用户（可选）"""
    # 尝试从Bearer Token获取用户
    if credentials:
        user_info = auth_service.verify_access_token(credentials.credentials)
        if user_info:
            return auth_service.get_current_user(credentials.credentials)
    
    # 尝试从Cookie获取用户
    if session_token:
        return auth_service.validate_session(session_token)
    
    return None


def require_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """要求用户登录"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要登录访问",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def require_admin(
    current_user: User = Depends(require_user),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """要求管理员权限"""
    if not auth_service.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


def optional_user(
    current_user: Optional[User] = Depends(get_current_user)
) -> Optional[User]:
    """可选用户（不强制登录）"""
    return current_user