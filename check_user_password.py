"""
检查用户密码状态
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.auth.password import get_password_hash, verify_password

def check_user_password():
    db = SessionLocal()
    
    try:
        # 查找你的用户
        users = db.query(User).filter(User.username.in_(['marvinli001', 'admin'])).all()
        
        for user in users:
            print(f"\n👤 用户: {user.username}")
            print(f"📧 邮箱: {user.email}")
            print(f"🔑 密码哈希: {user.password_hash}")
            print(f"🔑 哈希长度: {len(user.password_hash) if user.password_hash else 0}")
            print(f"🔑 哈希前缀: {user.password_hash[:20] if user.password_hash else 'None'}...")
            
            # 检查是否是bcrypt格式
            if user.password_hash:
                if user.password_hash.startswith('$2b$') or user.password_hash.startswith('$2a$'):
                    print("✅ 密码哈希格式正确 (bcrypt)")
                    
                    # 测试密码验证
                    test_passwords = ['admin123', 'admin', 'password', '123456']
                    for pwd in test_passwords:
                        try:
                            result = verify_password(pwd, user.password_hash)
                            print(f"🧪 测试密码 '{pwd}': {'✅ 正确' if result else '❌ 错误'}")
                            if result:
                                print(f"🎉 找到正确密码: {pwd}")
                                break
                        except Exception as e:
                            print(f"🧪 测试密码 '{pwd}': ❌ 验证失败 - {str(e)}")
                else:
                    print("❌ 密码哈希格式不正确")
                    print("🔧 需要重新生成密码哈希")
            else:
                print("❌ 密码哈希为空")
        
    except Exception as e:
        print(f"❌ 检查失败: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    check_user_password()