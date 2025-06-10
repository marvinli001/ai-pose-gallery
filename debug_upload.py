"""
调试上传功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.storage_service import storage_manager

def debug_storage_manager():
    """调试StorageManager"""
    print("🔍 调试StorageManager...")
    
    print(f"存储类型: {storage_manager.storage_type}")
    print(f"OSS启用: {storage_manager.oss_enabled}")
    print(f"OSS客户端: {'已初始化' if storage_manager.oss_bucket_client else '未初始化'}")
    
    # 检查service属性
    try:
        service = storage_manager.service
        print(f"StorageService: {type(service).__name__}")
    except Exception as e:
        print(f"❌ 获取StorageService失败: {e}")
    
    # 检查必要方法
    methods = ['upload_image', 'validate_image_file', 'get_content_type', 'get_image_dimensions']
    for method in methods:
        has_method = hasattr(storage_manager, method)
        print(f"方法 {method}: {'✅' if has_method else '❌'}")
    
    # 测试OSS连接
    if storage_manager.oss_enabled:
        connection_ok = storage_manager.check_oss_connection()
        print(f"OSS连接: {'✅' if connection_ok else '❌'}")

if __name__ == "__main__":
    debug_storage_manager()