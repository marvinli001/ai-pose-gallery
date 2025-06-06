"""
将marvinli001用户升级为管理员
"""
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User, UserRole

def upgrade_user_to_admin():
    """将marvinli001升级为管理员"""
    db = SessionLocal()
    try:
        # 查找用户
        user = db.query(User).filter(User.username == "marvinli001").first()
        
        if user:
            # 升级为管理员
            user.role = UserRole.ADMIN
            user.is_verified = True
            db.commit()
            print(f"✅ 用户 {user.username} 已升级为管理员")
            print(f"   角色: {user.role.value}")
            print(f"   邮箱验证: {user.is_verified}")
        else:
            print("❌ 未找到用户 marvinli001")
    
    except Exception as e:
        print(f"❌ 升级用户失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    upgrade_user_to_admin()