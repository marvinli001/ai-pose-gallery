"""
认证服务
"""
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.user import User, UserSession, UserRole
from app.config import get_settings

settings = get_settings()


class AuthService:
    """认证服务类"""
    
    SECRET_KEY = "your-secret-key-change-in-production"  # 在生产环境中应该从环境变量读取
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS = 24
    
    def __init__(self, db: Session):
        self.db = db
    
    def hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{password_hash.hex()}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            salt, stored_hash = password_hash.split(':')
            password_hash_computed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return stored_hash == password_hash_computed.hex()
        except:
            return False
    
    def create_user(self, username: str, email: str, password: str, full_name: str = None) -> Dict[str, Any]:
        """创建用户"""
        try:
            # 检查用户名和邮箱是否已存在
            existing_user = self.db.query(User).filter(
                or_(User.username == username, User.email == email)
            ).first()
            
            if existing_user:
                if existing_user.username == username:
                    return {"success": False, "error": "用户名已存在"}
                else:
                    return {"success": False, "error": "邮箱已存在"}
            
            # 创建新用户
            user = User(
                username=username,
                email=email,
                password_hash=self.hash_password(password),
                full_name=full_name or username,
                role=UserRole.USER
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            return {
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role.value
                }
            }
            
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": f"创建用户失败: {str(e)}"}
    
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录认证"""
        try:
            # 查找用户（支持用户名或邮箱登录）
            user = self.db.query(User).filter(
                and_(
                    or_(User.username == username, User.email == username),
                    User.is_active == True
                )
            ).first()
            
            if not user:
                return {"success": False, "error": "用户不存在或已被禁用"}
            
            if not self.verify_password(password, user.password_hash):
                return {"success": False, "error": "密码错误"}
            
            # 更新登录统计
            user.login_count += 1
            user.last_login = datetime.utcnow()
            self.db.commit()
            
            # 生成访问令牌
            access_token = self.create_access_token(user.id)
            
            return {
                "success": True,
                "access_token": access_token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role.value,
                    "avatar_url": user.avatar_url,
                    "upload_count": user.upload_count
                }
            }
            
        except Exception as e:
            return {"success": False, "error": f"登录失败: {str(e)}"}
    
    def create_access_token(self, user_id: int) -> str:
        """创建访问令牌"""
        expire = datetime.utcnow() + timedelta(hours=self.ACCESS_TOKEN_EXPIRE_HOURS)
        to_encode = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        try:
            return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        except:
            # 如果jwt版本较低，可能需要这样处理
            import json
            return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM).decode('utf-8')
    
    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证访问令牌"""
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            user_id = payload.get("user_id")
            
            if user_id is None:
                return None
            
            # 验证用户是否存在且激活
            user = self.db.query(User).filter(
                and_(User.id == user_id, User.is_active == True)
            ).first()
            
            if not user:
                return None
            
            return {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "full_name": user.full_name
            }
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    def get_current_user(self, token: str) -> Optional[User]:
        """获取当前用户"""
        user_info = self.verify_access_token(token)
        if not user_info:
            return None
        
        return self.db.query(User).filter(User.id == user_info["user_id"]).first()
    
    def is_admin(self, user: User) -> bool:
        """检查是否为管理员"""
        return user.role in [UserRole.ADMIN, UserRole.MODERATOR]
    
    def create_session(self, user_id: int, ip_address: str, user_agent: str) -> str:
        """创建用户会话"""
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=self.ACCESS_TOKEN_EXPIRE_HOURS)
        
        session = UserSession(
            user_id=user_id,
            session_token=session_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at
        )
        
        self.db.add(session)
        self.db.commit()
        
        return session_token
    
    def validate_session(self, session_token: str) -> Optional[User]:
        """验证会话"""
        session = self.db.query(UserSession).filter(
            and_(
                UserSession.session_token == session_token,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            )
        ).first()
        
        if not session:
            return None
        
        # 更新最后访问时间
        session.last_accessed = datetime.utcnow()
        self.db.commit()
        
        # 获取用户信息
        user = self.db.query(User).filter(
            and_(User.id == session.user_id, User.is_active == True)
        ).first()
        
        return user
    
    def logout_session(self, session_token: str) -> bool:
        """注销会话"""
        session = self.db.query(UserSession).filter(
            UserSession.session_token == session_token
        ).first()
        
        if session:
            session.is_active = False
            self.db.commit()
            return True
        
        return False