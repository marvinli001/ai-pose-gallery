"""
用户模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class UserRole(enum.Enum):
    """用户角色枚举"""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, comment="用户ID")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, index=True, comment="邮箱")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    full_name = Column(String(100), comment="全名")
    avatar_url = Column(String(500), comment="头像URL")
    
    # 角色和权限
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False, comment="用户角色")
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_verified = Column(Boolean, default=False, comment="是否验证邮箱")
    
    # 统计信息
    upload_count = Column(Integer, default=0, comment="上传图片数量")
    login_count = Column(Integer, default=0, comment="登录次数")
    last_login = Column(DateTime(timezone=True), comment="最后登录时间")
    
    # 个人信息
    bio = Column(Text, comment="个人简介")
    location = Column(String(100), comment="所在地")
    website = Column(String(200), comment="个人网站")
    
    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role.value}')>"


class UserSession(Base):
    """用户会话表"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True, comment="会话ID")
    user_id = Column(Integer, nullable=False, index=True, comment="用户ID")
    session_token = Column(String(255), unique=True, nullable=False, index=True, comment="会话令牌")
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(Text, comment="用户代理")
    
    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    expires_at = Column(DateTime(timezone=True), nullable=False, comment="过期时间")
    last_accessed = Column(DateTime(timezone=True), server_default=func.now(), comment="最后访问时间")
    
    is_active = Column(Boolean, default=True, comment="是否激活")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id})>"


class UserFavorite(Base):
    """用户收藏表"""
    __tablename__ = "user_favorites"
    
    id = Column(Integer, primary_key=True, index=True, comment="收藏ID")
    user_id = Column(Integer, nullable=False, index=True, comment="用户ID")
    image_id = Column(Integer, nullable=False, index=True, comment="图片ID")
    
    # 收藏信息
    notes = Column(Text, comment="收藏备注")
    folder_name = Column(String(100), comment="收藏夹名称")
    
    # 时间信息
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="收藏时间")
    
    def __repr__(self):
        return f"<UserFavorite(id={self.id}, user_id={self.user_id}, image_id={self.image_id})>"