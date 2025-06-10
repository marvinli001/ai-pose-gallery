"""
添加OSS相关字段的迁移脚本 - MySQL版本
"""
from sqlalchemy import text
from app.database import get_db

def upgrade():
    """升级数据库 - 添加新字段"""
    db = next(get_db())
    
    try:
        print("🔧 开始升级数据库...")
        
        # 检查字段是否已存在 - MySQL语法
        result = db.execute(text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'images'
        """)).fetchall()
        
        existing_columns = [row[0] for row in result]
        print(f"📊 现有字段: {existing_columns}")
        
        # 添加 oss_key 字段
        if 'oss_key' not in existing_columns:
            db.execute(text("""
                ALTER TABLE images 
                ADD COLUMN oss_key VARCHAR(500) NULL
            """))
            print("✅ 添加 oss_key 字段")
        else:
            print("⏭️ oss_key 字段已存在")
        
        # 添加 url 字段
        if 'url' not in existing_columns:
            db.execute(text("""
                ALTER TABLE images 
                ADD COLUMN url VARCHAR(1000) NULL
            """))
            print("✅ 添加 url 字段")
        else:
            print("⏭️ url 字段已存在")
        
        # 创建索引 - MySQL语法
        try:
            # 检查索引是否已存在
            index_result = db.execute(text("""
                SELECT INDEX_NAME 
                FROM INFORMATION_SCHEMA.STATISTICS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'images' 
                AND INDEX_NAME = 'idx_images_oss_key'
            """)).fetchall()
            
            if not index_result:
                db.execute(text("""
                    CREATE INDEX idx_images_oss_key ON images(oss_key)
                """))
                print("✅ 创建 oss_key 索引")
            else:
                print("⏭️ oss_key 索引已存在")
                
        except Exception as e:
            print(f"⚠️ 创建索引时出现警告: {e}")
        
        db.commit()
        print("🎉 数据库升级完成!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 数据库升级失败: {e}")
        raise
    finally:
        db.close()

def downgrade():
    """降级数据库 - 移除新字段"""
    db = next(get_db())
    
    try:
        print("🔧 开始降级数据库...")
        
        # 删除索引
        try:
            db.execute(text("DROP INDEX idx_images_oss_key ON images"))
            print("✅ 删除 oss_key 索引")
        except Exception as e:
            print(f"⚠️ 删除索引失败: {e}")
        
        # 删除字段
        try:
            db.execute(text("ALTER TABLE images DROP COLUMN oss_key"))
            print("✅ 删除 oss_key 字段")
        except Exception as e:
            print(f"⚠️ 删除 oss_key 字段失败: {e}")
        
        try:
            db.execute(text("ALTER TABLE images DROP COLUMN url"))
            print("✅ 删除 url 字段")
        except Exception as e:
            print(f"⚠️ 删除 url 字段失败: {e}")
        
        db.commit()
        print("🎉 数据库降级完成!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 数据库降级失败: {e}")
        raise
    finally:
        db.close()