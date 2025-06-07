from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User, UserRole
from app.config import get_settings

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """获取当前用户（必须登录）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证身份",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 从cookie获取token
        token = request.cookies.get("access_token")
        
        if token is None:
            print("❌ 未找到access_token cookie")
            raise credentials_exception
        
        # 验证token
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            username: str = payload.get("sub")
            if username is None:
                print("❌ Token中没有用户名")
                raise credentials_exception
        except JWTError as e:
            print(f"❌ JWT验证失败: {str(e)}")
            raise credentials_exception
        
        # 查找用户
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            print(f"❌ 用户 {username} 不存在")
            raise credentials_exception
        
        if not user.is_active:
            print(f"❌ 用户 {username} 已被禁用")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账户已被禁用"
            )
        
        print(f"✅ 用户 {username} 验证成功")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 用户验证异常: {str(e)}")
        raise credentials_exception

async def optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """可选的用户依赖，不强制要求登录"""
    try:
        token = request.cookies.get("access_token")
        if not token:
            return None
        
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            return None
        
        user = db.query(User).filter(User.username == username).first()
        if user is None or not user.is_active:
            return None
        
        return user
    except JWTError:
        return None
    except Exception:
        return None

# 添加缺失的 require_user 函数
async def require_user(current_user: User = Depends(get_current_user)) -> User:
    """要求用户登录（任何角色）"""
    return current_user

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求管理员权限"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

async def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求超级管理员权限"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限"
        )
    return current_user

# 为了向后兼容，添加其他可能需要的函数
async def get_user_or_none(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """获取用户或None（向后兼容）"""
    return await optional_user(request, db)