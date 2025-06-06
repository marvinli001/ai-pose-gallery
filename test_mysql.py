"""
测试MySQL连接
"""
import pymysql
import os
from dotenv import load_dotenv

def test_direct_connection():
    """直接测试MySQL连接"""
    load_dotenv()
    
    config = {
        'host': os.getenv('MYSQL_HOST'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'database': os.getenv('MYSQL_DATABASE'),
        'charset': 'utf8mb4'
    }
    
    print("🔧 测试MySQL直连...")
    print(f"📍 连接信息: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
    
    try:
        # 直接连接测试
        connection = pymysql.connect(**config)
        print("✅ 直连成功!")
        
        with connection.cursor() as cursor:
            # 测试查询
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            print(f"✅ MySQL版本: {version}")
            
            # 测试数据库
            cursor.execute("SELECT DATABASE()")
            db = cursor.fetchone()[0]
            print(f"✅ 当前数据库: {db}")
            
            # 测试创建表权限
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✅ 当前表数量: {len(tables)}")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_sqlalchemy_connection():
    """测试SQLAlchemy连接"""
    print("\n🔧 测试SQLAlchemy连接...")
    
    try:
        from app.config import get_settings
        settings = get_settings()
        print(f"📍 SQLAlchemy URL: {settings.database_url}")
        
        from sqlalchemy import create_engine, text
        
        # 创建引擎
        engine = create_engine(settings.database_url, echo=False)  # 关闭详细日志
        
        # 测试连接
        with engine.connect() as connection:
            # 测试基本查询
            result = connection.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            print(f"✅ 基本查询成功: {test_value}")
            
            # 测试版本查询
            result = connection.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            print(f"✅ MySQL版本: {version}")
            
            # 测试数据库查询
            result = connection.execute(text("SELECT DATABASE()"))
            db = result.fetchone()[0]
            print(f"✅ 当前数据库: {db}")
            
            print("✅ SQLAlchemy连接成功!")
            return True
            
    except Exception as e:
        print(f"❌ SQLAlchemy测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始数据库连接测试...\n")
    
    # 测试直连
    direct_ok = test_direct_connection()
    
    # 测试SQLAlchemy
    sqlalchemy_ok = test_sqlalchemy_connection()
    
    print(f"\n📊 测试结果:")
    print(f"   直连: {'✅' if direct_ok else '❌'}")
    print(f"   SQLAlchemy: {'✅' if sqlalchemy_ok else '❌'}")
    
    if direct_ok and sqlalchemy_ok:
        print("\n🎉 所有测试通过! 可以启动应用了!")
    else:
        print("\n❌ 还有问题需要解决")