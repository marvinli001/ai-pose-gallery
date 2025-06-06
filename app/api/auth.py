"""
认证API - 修复版本
"""
from fastapi import APIRouter, Depends, HTTPException, Response, Request, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from typing import Optional
import re

from app.database import get_db
from app.services.auth_service import AuthService
from app.auth.dependencies import get_current_user, require_user, optional_user
from app.models.user import User

router = APIRouter()


class UserRegister(BaseModel):
    username: str
    email: str  # 改为普通字符串，使用自定义验证
    password: str
    full_name: Optional[str] = None
    
    @validator('email')
    def validate_email(cls, v):
        """简单的邮箱验证"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('邮箱格式不正确')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        """用户名验证"""
        if len(v) < 3:
            raise ValueError('用户名至少3个字符')
        if len(v) > 50:
            raise ValueError('用户名不能超过50个字符')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('用户名只能包含字母、数字、下划线和连字符')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        """密码验证"""
        if len(v) < 6:
            raise ValueError('密码至少6个字符')
        return v


class UserLogin(BaseModel):
    username: str
    password: str


@router.post("/register")
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """用户注册"""
    try:
        auth_service = AuthService(db)
        result = auth_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "注册成功",
                "user": result["user"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")


@router.post("/login")
async def login(
    response: Response,
    request: Request,
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """用户登录"""
    auth_service = AuthService(db)
    result = auth_service.authenticate_user(user_data.username, user_data.password)
    
    if result["success"]:
        # 创建会话Cookie
        ip_address = request.client.host if request.client else "127.0.0.1"
        user_agent = request.headers.get("user-agent", "")
        session_token = auth_service.create_session(
            result["user"]["id"], ip_address, user_agent
        )
        
        # 设置Cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=24 * 60 * 60,  # 24小时
            httponly=True,
            secure=False,  # 在生产环境中设置为True
            samesite="lax"
        )
        
        return {
            "success": True,
            "message": "登录成功",
            "access_token": result["access_token"],
            "user": result["user"]
        }
    else:
        raise HTTPException(status_code=401, detail=result["error"])


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    current_user: Optional[User] = Depends(optional_user),
    db: Session = Depends(get_db)
):
    """用户登出"""
    # 获取会话token并注销
    session_token = request.cookies.get("session_token")
    if session_token:
        auth_service = AuthService(db)
        auth_service.logout_session(session_token)
    
    # 清除Cookie
    response.delete_cookie("session_token")
    
    return {
        "success": True,
        "message": "已退出登录"
    }


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(require_user)
):
    """获取当前用户信息"""
    return {
        "success": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role.value,
            "avatar_url": current_user.avatar_url,
            "upload_count": current_user.upload_count,
            "login_count": current_user.login_count,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
            "created_at": current_user.created_at.isoformat(),
            "bio": current_user.bio,
            "location": current_user.location,
            "website": current_user.website
        }
    }


@router.get("/check")
async def check_auth_status(
    current_user: Optional[User] = Depends(optional_user)
):
    """检查登录状态"""
    if current_user:
        return {
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "role": current_user.role.value,
                "full_name": current_user.full_name,
                "avatar_url": current_user.avatar_url
            }
        }
    else:
        return {
            "authenticated": False,
            "user": None
        }