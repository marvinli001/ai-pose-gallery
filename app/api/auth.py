from fastapi import APIRouter, Depends, HTTPException, Form, Response, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.auth.password import verify_password
from app.config import get_settings

router = APIRouter()
settings = get_settings()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# 登录请求模型
class LoginRequest(BaseModel):
    username: str
    password: str

def create_access_token(data: dict, expires_delta: timedelta = None):
    """创建访问token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """用户登录 - 支持Form数据和JSON数据"""
    try:
        # 获取请求数据
        content_type = request.headers.get("content-type", "")
        
        if "application/x-www-form-urlencoded" in content_type:
            # 处理表单数据
            form_data = await request.form()
            username = form_data.get("username")
            password = form_data.get("password")
        elif "application/json" in content_type:
            # 处理JSON数据
            json_data = await request.json()
            username = json_data.get("username")
            password = json_data.get("password")
        else:
            # 尝试从表单获取
            form_data = await request.form()
            username = form_data.get("username")
            password = form_data.get("password")
        
        # 验证参数
        if not username or not password:
            print(f"❌ 登录参数缺失: username={username}, password={'*' * len(password) if password else None}")
            raise HTTPException(
                status_code=400,
                detail="用户名和密码不能为空"
            )
        
        username = str(username).strip()
        password = str(password)
        
        print(f"🔄 尝试登录用户: {username}")
        
        # 查找用户
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"❌ 用户 {username} 不存在")
            raise HTTPException(
                status_code=401,
                detail="用户名或密码错误"
            )
        
        # 打印用户模型的属性，用于调试
        print(f"🔍 用户模型属性: {[attr for attr in dir(user) if not attr.startswith('_')]}")
        
        # 修复：根据实际的密码字段名称进行验证
        password_field = None
        if hasattr(user, 'password_hash'):  # 你的模型使用这个字段
            password_field = user.password_hash
        elif hasattr(user, 'hashed_password'):
            password_field = user.hashed_password
        elif hasattr(user, 'password'):
            password_field = user.password
        else:
            print(f"❌ 用户模型中未找到密码字段")
            raise HTTPException(
                status_code=500,
                detail="用户密码配置错误"
            )
        
        print(f"🔍 使用密码字段: password_hash, 哈希值前20字符: {password_field[:20] if password_field else 'None'}")
        
        # 验证密码
        try:
            password_valid = verify_password(password, password_field)
            print(f"🔍 密码验证结果: {password_valid}")
    
            if not password_valid:
                print(f"❌ 用户 {username} 密码错误")
                raise HTTPException(
                    status_code=401,
                    detail="用户名或密码错误"
                )
        except Exception as e:
            print(f"❌ 密码验证异常: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail="用户名或密码错误"
            )
        
        # 检查用户状态
        if hasattr(user, 'is_active') and not user.is_active:
            print(f"❌ 用户 {username} 账号被禁用")
            raise HTTPException(
                status_code=401,
                detail="账号已被禁用"
            )
        
        # 更新最后登录时间
        if hasattr(user, 'last_login'):
            user.last_login = datetime.now()
            db.commit()
        
        # 创建access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )
        
        # 设置cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=settings.access_token_expire_minutes * 60,
            expires=settings.access_token_expire_minutes * 60,
            path="/",
            domain=None,
            secure=False,
            httponly=True,
            samesite="lax"
        )
        
        print(f"✅ 用户 {username} 登录成功")
        print(f"🔑 Token前50字符: {access_token[:50]}...")
        
        # 构建用户信息响应
        user_info = {
            "id": user.id,
            "username": user.username,
        }

        # 添加可选字段
        if hasattr(user, 'email'):
            user_info["email"] = user.email
        if hasattr(user, 'role'):
            user_info["role"] = user.role.value if hasattr(user.role, 'value') else str(user.role)
        else:
            user_info["role"] = "user"  # 默认角色
        if hasattr(user, 'is_active'):
            user_info["is_active"] = user.is_active
        else:
            user_info["is_active"] = True  # 默认激活
        if hasattr(user, 'is_verified'):
            user_info["is_verified"] = user.is_verified
        else:
            user_info["is_verified"] = True  # 默认验证
        
        return {
            "success": True,
            "message": "登录成功",
            "user": user_info,
            "access_token": access_token  # 也返回token给前端
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 登录异常: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

@router.post("/logout")
async def logout(response: Response):
    """用户退出登录"""
    try:
        response.delete_cookie(key="access_token", path="/")
        print("✅ 用户退出登录成功")
        
        return {
            "success": True,
            "message": "退出登录成功"
        }
    except Exception as e:
        print(f"❌ 退出登录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"退出登录失败: {str(e)}")

@router.get("/check")
async def check_auth_status(
    request: Request,
    db: Session = Depends(get_db)
):
    """检查用户认证状态"""
    try:
        token = request.cookies.get("access_token")
        
        if not token:
            return {
                "authenticated": False,
                "user": None
            }
        
        print(f"🔍 检查token: {token[:50]}...")
        
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            username: str = payload.get("sub")
            
            if username is None:
                print("❌ Token中没有用户名")
                return {
                    "authenticated": False,
                    "user": None,
                    "error": "Invalid token payload"
                }
            
            user = db.query(User).filter(User.username == username).first()
            
            if user is None:
                print(f"❌ 用户 {username} 不存在")
                return {
                    "authenticated": False,
                    "user": None,
                    "error": "User not found"
                }
            
            if not user.is_active:
                print(f"❌ 用户 {username} 已被禁用")
                return {
                    "authenticated": False,
                    "user": None,
                    "error": "User inactive"
                }
            
            print(f"✅ 用户 {username} 认证成功")
            
            return {
                "authenticated": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role.value,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified
                }
            }
            
        except JWTError as e:
            print(f"❌ JWT验证失败: {str(e)}")
            return {
                "authenticated": False,
                "user": None,
                "error": f"JWT validation failed: {str(e)}"
            }
            
    except Exception as e:
        print(f"❌ 认证检查失败: {str(e)}")
        return {
            "authenticated": False,
            "user": None,
            "error": f"Auth check failed: {str(e)}"
        }