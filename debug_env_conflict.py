"""
调试环境变量冲突
"""
import os
from dotenv import load_dotenv, dotenv_values

def check_env_conflict():
    print("🔧 检查环境变量冲突...")
    
    # 检查系统环境变量
    print("\n🖥️  系统环境变量:")
    system_vars = ['MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
    for var in system_vars:
        value = os.environ.get(var)
        if value:
            if var == 'MYSQL_PASSWORD':
                print(f"  {var}: ***")
            else:
                print(f"  {var}: {value}")
        else:
            print(f"  {var}: (未设置)")
    
    # 检查 .env 文件
    print("\n📄 .env 文件变量:")
    env_vars = dotenv_values('.env')
    for var in system_vars:
        value = env_vars.get(var)
        if value:
            if var == 'MYSQL_PASSWORD':
                print(f"  {var}: ***")
            else:
                print(f"  {var}: {value}")
        else:
            print(f"  {var}: (未设置)")
    
    # 清除系统环境变量并重新加载
    print("\n🧹 清除系统环境变量...")
    for var in system_vars:
        if var in os.environ:
            del os.environ[var]
            print(f"  清除: {var}")
    
    # 重新加载 .env
    load_dotenv(override=True)
    
    print("\n✅ 重新加载后的结果:")
    for var in system_vars:
        value = os.getenv(var)
        if var == 'MYSQL_PASSWORD':
            print(f"  {var}: {'***' if value else '(未设置)'}")
        else:
            print(f"  {var}: {value or '(未设置)'}")

if __name__ == "__main__":
    check_env_conflict()