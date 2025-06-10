"""
添加OSS相关字段的迁移脚本
"""
from sqlalchemy import text
from app.database import get_db

def upgrade():
    """升级数据库 - 添加新字段"""
    db = next(get_db())
    
    try:
        print("🔧 开始升级数据库...")
        
        # 检查字段是否已存在
        result = db.execute(text("PRAGMA table_info(images)")).fetchall()
        existing_columns = [row[1] for row in result]
        
        # 添加 oss_key 字段
        if 'oss_key' not in existing_columns:
            db.execute(text("ALTER TABLE images ADD COLUMN oss_key VARCHAR(500)"))
            print("✅ 添加 oss_key 字段")
        else:
            print("⏭️ oss_key 字段已存在")
        
        # 添加 url 字段
        if 'url' not in existing_columns:
            db.execute(text("ALTER TABLE images ADD COLUMN url VARCHAR(1000)"))
            print("✅ 添加 url 字段")
        else:
            print("⏭️ url 字段已存在")
        
        # 创建索引
        try:
            db.execute(text("CREATE INDEX IF NOT EXISTS idx_images_oss_key ON images(oss_key)"))
            print("✅ 创建 oss_key 索引")
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
    print("⚠️ SQLite 不支持删除列，请手动处理或重建数据库")