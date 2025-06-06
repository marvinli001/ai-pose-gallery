"""
调试配置加载
"""
import os
from dotenv import load_dotenv

def debug_env():
    print("🔧 调试环境变量加载...")
    
    # 检查 .env 文件
    if os.path.exists('.env'):
        print("✅ .env 文件存在")
        
        # 显示文件内容
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read()
            print("\n📋 .env 文件内容:")
            for i, line in enumerate(content.split('\n'), 1):
                if line.strip():
                    print(f"  {i:2d}: {line}")
    else:
        print("❌ .env 文件不存在")
        return
    
    # 加载环境变量
    load_dotenv()
    
    print(f"\n🔍 环境变量读取结果:")
    vars_to_check = ['MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
    
    for var in vars_to_check:
        value = os.getenv(var)
        if var == 'MYSQL_PASSWORD':
            print(f"  {var}: {'***' if value else 'None'}")
        else:
            print(f"  {var}: {value}")
    
    # 测试配置类
    try:
        from app.config import get_settings
        settings = get_settings()
        
        print(f"\n📊 Settings 对象结果:")
        print(f"  mysql_host: {settings.mysql_host}")
        print(f"  mysql_port: {settings.mysql_port}")
        print(f"  mysql_user: {settings.mysql_user}")
        print(f"  mysql_password: ***")
        print(f"  mysql_database: {settings.mysql_database}")
        print(f"  database_url: {settings.database_url}")
        
    except Exception as e:
        print(f"❌ Settings 加载失败: {e}")

if __name__ == "__main__":
    debug_env()