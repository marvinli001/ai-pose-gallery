"""
数据库迁移主脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from migrations.add_oss_fields import upgrade as add_oss_fields_upgrade

def run_migrations():
    """运行所有迁移"""
    print("🚀 开始数据库迁移...")
    
    try:
        # 运行添加OSS字段的迁移
        add_oss_fields_upgrade()
        print("✅ 所有迁移执行完成!")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)