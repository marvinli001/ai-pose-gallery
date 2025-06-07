"""
简单的密码重置脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User, UserRole
from datetime import datetime

def reset_password_simple():
    db = SessionLocal()
    
    try:
        # 查找用户
        user = db.query(User).filter(User.username == 'admin').first()
        
        if not user:
            print("❌ 用户不存在")
            return
        
        print(f"✅ 找到用户: {user.username}")
        
        # 使用简单的bcrypt加密
        import bcrypt
        
        # 设置密码为 admin123
        password = "admin123"
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        print(f"🔑 新密码: {password}")
        print(f"🔐 新哈希: {hashed.decode('utf-8')}")
        
        # 更新密码
        user.password_hash = hashed.decode('utf-8')
        user.role = UserRole.ADMIN
        user.is_active = True
        user.is_verified = True
        
        db.commit()
        
        print("✅ 密码重置成功")
        
        # 验证密码
        stored_hash = user.password_hash.encode('utf-8')
        test_password = "admin123".encode('utf-8')
        
        if bcrypt.checkpw(test_password, stored_hash):
            print("✅ 密码验证成功")
        else:
            print("❌ 密码验证失败")
            
    except Exception as e:
        print(f"❌ 操作失败: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_password_simple()