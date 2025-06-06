"""
测试数据库连接
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.database import test_connection, engine
from sqlalchemy import text

def main():
    print("🔧 测试远程MySQL数据库连接...")
    
    settings = get_settings()
    print(f"📍 连接信息:")
    print(f"   主机: {settings.mysql_host}")
    print(f"   端口: {settings.mysql_port}")
    print(f"   用户: {settings.mysql_user}")
    print(f"   数据库: {settings.mysql_database}")
    
    # 测试基本连接
    if test_connection():
        print("✅ 基本连接测试通过")
        
        # 测试数据库操作
        try:
            with engine.connect() as conn:
                # 测试查询
                result = conn.execute(text("SELECT VERSION()"))
                version = result.fetchone()[0]
                print(f"✅ MySQL版本: {version}")
                
                # 测试数据库是否存在
                result = conn.execute(text("SHOW DATABASES LIKE 'ai_pose_gallery'"))
                if result.fetchone():
                    print("✅ 数据库 ai_pose_gallery 存在")
                else:
                    print("⚠️  数据库 ai_pose_gallery 不存在，请先创建")
                
                print("✅ 数据库连接和操作测试完成")
                
        except Exception as e:
            print(f"❌ 数据库操作测试失败: {e}")
    else:
        print("❌ 数据库连接失败，请检查配置")

if __name__ == "__main__":
    main()