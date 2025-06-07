"""
认证和授权模块
"""

from .password import (
    verify_password,
    get_password_hash,
    check_password_strength,
    generate_random_password,
    hash_password_for_user,
    validate_password_for_login
)

from .dependencies import (
    get_current_user,
    optional_user,
    require_user,
    require_admin,
    require_super_admin
)

__all__ = [
    # 密码相关
    "verify_password",
    "get_password_hash", 
    "check_password_strength",
    "generate_random_password",
    "hash_password_for_user",
    "validate_password_for_login",
    
    # 依赖相关
    "get_current_user",
    "optional_user", 
    "require_user",
    "require_admin",
    "require_super_admin"
]