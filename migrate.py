"""
数据库迁移主脚本 - MySQL版本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from migrations.add_oss_fields import upgrade as add_oss_fields_upgrade, downgrade as add_oss_fields_downgrade

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

def rollback_migrations():
    """回滚迁移"""
    print("🔄 开始回滚迁移...")
    
    try:
        add_oss_fields_downgrade()
        print("✅ 回滚完成!")
        
    except Exception as e:
        print(f"❌ 回滚失败: {e}")
        return False
    
    return True

def check_database_status():
    """检查数据库状态"""
    from app.database import get_db
    from sqlalchemy import text
    
    db = next(get_db())
    
    try:
        print("🔍 检查数据库状态...")
        
        # 检查表是否存在
        tables_result = db.execute(text("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = DATABASE()
        """)).fetchall()
        
        tables = [row[0] for row in tables_result]
        print(f"📊 现有表: {tables}")
        
        if 'images' in tables:
            # 检查images表的字段
            columns_result = db.execute(text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'images'
                ORDER BY ORDINAL_POSITION
            """)).fetchall()
            
            print("\n📋 images表字段:")
            for col in columns_result:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                print(f"  - {col[0]}: {col[1]} ({nullable})")
            
            # 检查索引
            indexes_result = db.execute(text("""
                SELECT INDEX_NAME, COLUMN_NAME 
                FROM INFORMATION_SCHEMA.STATISTICS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'images'
                AND INDEX_NAME != 'PRIMARY'
            """)).fetchall()
            
            if indexes_result:
                print("\n📇 images表索引:")
                for idx in indexes_result:
                    print(f"  - {idx[0]}: {idx[1]}")
            
            # 检查数据量
            count_result = db.execute(text("SELECT COUNT(*) FROM images")).fetchone()
            print(f"\n📊 图片数量: {count_result[0]}")
            
        else:
            print("⚠️ images表不存在")
        
    except Exception as e:
        print(f"❌ 检查数据库状态失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库迁移工具')
    parser.add_argument('--rollback', action='store_true', help='回滚迁移')
    parser.add_argument('--status', action='store_true', help='检查数据库状态')
    args = parser.parse_args()
    
    if args.status:
        check_database_status()
    elif args.rollback:
        success = rollback_migrations()
        sys.exit(0 if success else 1)
    else:
        success = run_migrations()
        if success:
            print("\n" + "="*50)
            check_database_status()
        sys.exit(0 if success else 1)