"""
修复用户密码
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.auth.password import get_password_hash
from datetime import datetime

def fix_user_password():
    db = SessionLocal()
    
    try:
        # 查找用户
        user = db.query(User).filter(User.username == 'marvinli001').first()
        
        if not user:
            print("❌ 用户 marvinli001 不存在，正在创建...")
            
            # 创建新用户
            user = User(
                username='marvinli001',
                email='marvinli001@example.com',
                password_hash=get_password_hash('admin123'),  # 使用正确的字段名
                full_name='Marvin Li',
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
                created_at=datetime.now(),
                upload_count=0,
                login_count=0
            )
            
            db.add(user)
            db.commit()
            
            print("✅ 用户创建成功")
            print("👤 用户名: marvinli001")
            print("🔑 密码: admin123")
            print("📧 邮箱: marvinli001@example.com")
            
        else:
            print(f"✅ 找到用户: {user.username}")
            print(f"📧 当前邮箱: {user.email}")
            print(f"🔑 当前密码哈希: {user.password_hash}")
            
            # 重置密码
            new_password = input("请输入新密码 (直接回车使用 admin123): ").strip()
            if not new_password:
                new_password = 'admin123'
            
            # 生成新的密码哈希
            new_hash = get_password_hash(new_password)
            print(f"🔑 新密码哈希: {new_hash}")
            
            # 更新密码
            user.password_hash = new_hash
            
            # 确保用户是管理员且激活
            user.role = UserRole.ADMIN
            user.is_active = True
            user.is_verified = True
            
            db.commit()
            
            print("✅ 密码更新成功")
            print(f"👤 用户名: {user.username}")
            print(f"🔑 新密码: {new_password}")
            print(f"👑 角色: {user.role.value}")
            
        # 验证密码是否正确设置
        from app.auth.password import verify_password
        
        test_password = 'admin123'
        if verify_password(test_password, user.password_hash):
            print(f"✅ 密码验证成功: {test_password}")
        else:
            print(f"❌ 密码验证失败: {test_password}")
            
    except Exception as e:
        print(f"❌ 操作失败: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_user_password()