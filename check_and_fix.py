"""
检查和修复缺失的文件
"""
import os
from pathlib import Path

def check_and_create_files():
    """检查并创建缺失的文件"""
    
    # 需要检查的文件和目录
    required_items = [
        # 目录
        ("app", "dir"),
        ("app/api", "dir"),
        ("app/services", "dir"),
        ("app/templates", "dir"),
        ("app/static", "dir"),
        ("uploads", "dir"),
        
        # 文件
        ("app/__init__.py", "file"),
        ("app/api/__init__.py", "file"),
        ("app/services/__init__.py", "file"),
    ]
    
    print("🔍 检查必需的文件和目录...")
    
    for item, item_type in required_items:
        if item_type == "dir":
            if not os.path.exists(item):
                os.makedirs(item, exist_ok=True)
                print(f"✅ 创建目录: {item}")
            else:
                print(f"✓ 目录已存在: {item}")
        
        elif item_type == "file":
            if not os.path.exists(item):
                # 创建空的 __init__.py 文件
                with open(item, 'w', encoding='utf-8') as f:
                    if "__init__.py" in item:
                        f.write('"""\n模块初始化\n"""\n')
                    else:
                        f.write("")
                print(f"✅ 创建文件: {item}")
            else:
                print(f"✓ 文件已存在: {item}")
    
    # 检查关键服务文件
    service_files = [
        "app/services/image_service.py",
        "app/services/database_service.py",
        "app/services/gpt4o_service.py"
    ]
    
    missing_services = []
    for service_file in service_files:
        if not os.path.exists(service_file):
            missing_services.append(service_file)
    
    if missing_services:
        print(f"\n⚠️  缺失的服务文件: {missing_services}")
        print("请确保这些文件存在，否则应用无法正常启动")
    else:
        print(f"\n✅ 所有关键服务文件都存在")
    
    # 检查API文件
    api_files = [
        "app/api/upload.py",
        "app/api/search.py", 
        "app/api/admin.py"
    ]
    
    missing_apis = []
    for api_file in api_files:
        if not os.path.exists(api_file):
            missing_apis.append(api_file)
    
    if missing_apis:
        print(f"\n⚠️  缺失的API文件: {missing_apis}")
    else:
        print(f"\n✅ 所有关键API文件都存在")

if __name__ == "__main__":
    check_and_create_files()
    print("\n🎉 检查完成！现在可以尝试启动应用了。")