"""
密码加密和验证模块 - 修复版本兼容性
"""
import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 加密后的密码哈希
        
    Returns:
        bool: 密码是否匹配
    """
    try:
        # 直接使用bcrypt验证
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        print(f"❌ 密码验证失败: {str(e)}")
        return False

def get_password_hash(password: str) -> str:
    """
    获取密码哈希
    
    Args:
        password: 明文密码
        
    Returns:
        str: 加密后的密码哈希
    """
    try:
        # 直接使用bcrypt生成哈希
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        print(f"❌ 密码加密失败: {str(e)}")
        raise e

def check_password_strength(password: str) -> dict:
    """
    检查密码强度
    
    Args:
        password: 明文密码
        
    Returns:
        dict: 密码强度检查结果
    """
    result = {
        "valid": True,
        "errors": [],
        "score": 0,
        "strength": "弱"
    }
    
    # 长度检查
    if len(password) < 6:
        result["valid"] = False
        result["errors"].append("密码长度至少6位")
    elif len(password) >= 8:
        result["score"] += 1
    
    # 复杂度检查
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    if has_lower:
        result["score"] += 1
    if has_upper:
        result["score"] += 1
    if has_digit:
        result["score"] += 1
    if has_special:
        result["score"] += 1
    
    # 强度评分
    if result["score"] >= 4:
        result["strength"] = "强"
    elif result["score"] >= 3:
        result["strength"] = "中等"
    elif result["score"] >= 2:
        result["strength"] = "一般"
    else:
        result["strength"] = "弱"
    
    return result

def generate_random_password(length: int = 12) -> str:
    """
    生成随机密码
    
    Args:
        length: 密码长度
        
    Returns:
        str: 随机密码
    """
    import secrets
    import string
    
    # 定义字符集
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    
    # 确保至少包含各种字符类型
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*")
    ]
    
    # 填充剩余长度
    for _ in range(length - 4):
        password.append(secrets.choice(alphabet))
    
    # 打乱顺序
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)

# 便捷函数
def hash_password_for_user(password: str) -> str:
    """为用户创建密码哈希（便捷函数）"""
    return get_password_hash(password)

def validate_password_for_login(plain_password: str, stored_hash: str) -> bool:
    """登录时验证密码（便捷函数）"""
    return verify_password(plain_password, stored_hash)