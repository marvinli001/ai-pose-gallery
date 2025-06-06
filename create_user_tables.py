"""
创建用户相关表
"""
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models.user import User, UserSession, UserFavorite
from app.models.image import Image
from app.services.auth_service import AuthService

def create_user_tables():
    """创建用户相关表"""
    print("🔄 创建用户相关表...")
    
    try:
        # 创建表
        from app.database import Base
        Base.metadata.create_all(bind=engine, tables=[
            User.__table__,
            UserSession.__table__,
            UserFavorite.__table__
        ])
        
        print("✅ 用户相关表创建成功")
        
        # 创建默认管理员用户
        create_default_admin()
        
        # 显示表信息
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT TABLE_NAME, TABLE_COMMENT 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME IN ('users', 'user_sessions', 'user_favorites')
            """))
            
            print("\n📋 已创建的用户表:")
            for row in result:
                print(f"   {row[0]}: {row[1]}")
                
    except Exception as e:
        print(f"❌ 创建表失败: {e}")

def create_default_admin():
    """创建默认管理员用户"""
    try:
        db = SessionLocal()
        auth_service = AuthService(db)
        
        # 检查是否已存在管理员
        from app.models.user import UserRole
        admin_exists = db.query(User).filter(User.role == UserRole.ADMIN).first()
        
        if not admin_exists:
            # 创建默认管理员
            result = auth_service.create_user(
                username="admin",
                email="admin@example.com",
                password="admin123",  # 在生产环境中应该使用更强的密码
                full_name="系统管理员"
            )
            
            if result["success"]:
                # 设置为管理员角色
                admin_user = db.query(User).filter(User.username == "admin").first()
                if admin_user:
                    admin_user.role = UserRole.ADMIN
                    admin_user.is_verified = True
                    db.commit()
                    print("✅ 默认管理员创建成功 - 用户名: admin, 密码: admin123")
            else:
                print(f"❌ 创建默认管理员失败: {result['error']}")
        else:
            print("ℹ️ 管理员用户已存在")
            
        # 创建测试用户 marvinli001
        test_user_exists = db.query(User).filter(User.username == "marvinli001").first()
        if not test_user_exists:
            result = auth_service.create_user(
                username="marvinli001",
                email="marvinli001@example.com",
                password="123456",
                full_name="Marvin Li"
            )
            
            if result["success"]:
                print("✅ 测试用户创建成功 - 用户名: marvinli001, 密码: 123456")
            else:
                print(f"❌ 创建测试用户失败: {result['error']}")
        else:
            print("ℹ️ 测试用户 marvinli001 已存在")
                
        db.close()
        
    except Exception as e:
        print(f"❌ 创建默认用户失败: {e}")

if __name__ == "__main__":
    create_user_tables()