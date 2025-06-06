"""
更新数据库结构以支持GPT-4o - 修复版本
"""
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models.image import Image, Tag, ImageTag

def update_database_schema():
    """更新数据库架构"""
    print("🔄 更新数据库结构以支持GPT-4o...")
    
    with engine.connect() as conn:
        try:
            # 检查字段是否已存在的SQL
            check_columns = """
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'images'
            """
            
            result = conn.execute(text(check_columns))
            existing_columns = {row[0] for row in result}
            
            # 需要添加的字段
            new_columns = {
                'ai_model': "ALTER TABLE images ADD COLUMN ai_model VARCHAR(50) DEFAULT 'gpt-4o' COMMENT '使用的AI模型'",
                'ai_analysis_raw': "ALTER TABLE images ADD COLUMN ai_analysis_raw JSON COMMENT '完整的AI分析结果JSON'",
                'ai_searchable_keywords': "ALTER TABLE images ADD COLUMN ai_searchable_keywords JSON COMMENT 'AI提取的搜索关键词'",
                'ai_mood': "ALTER TABLE images ADD COLUMN ai_mood VARCHAR(200) COMMENT 'AI分析的整体氛围'",
                'ai_style': "ALTER TABLE images ADD COLUMN ai_style VARCHAR(200) COMMENT 'AI分析的视觉风格'"
            }
            
            for column_name, command in new_columns.items():
                if column_name not in existing_columns:
                    try:
                        conn.execute(text(command))
                        print(f"✅ 添加字段: {column_name}")
                    except Exception as e:
                        print(f"❌ 添加字段失败 {column_name}: {e}")
                else:
                    print(f"⚠️  字段已存在，跳过: {column_name}")
            
            conn.commit()
            print("✅ 数据库结构更新完成")
            
        except Exception as e:
            print(f"❌ 数据库更新失败: {e}")
            conn.rollback()

def add_new_predefined_tags():
    """添加新的预定义标签，跳过重复的"""
    from app.models.image import PREDEFINED_TAGS
    
    db = SessionLocal()
    try:
        print("🏷️  添加新的预定义标签...")
        
        existing_names = {tag.name for tag in db.query(Tag.name).all()}
        new_tags = []
        skipped_tags = []
        
        for tag_data in PREDEFINED_TAGS:
            if tag_data['name'] not in existing_names:
                new_tags.append(tag_data)
            else:
                skipped_tags.append(tag_data['name'])
        
        if new_tags:
            for tag_data in new_tags:
                tag = Tag(**tag_data)
                db.add(tag)
            
            db.commit()
            print(f"✅ 添加了 {len(new_tags)} 个新标签")
        
        if skipped_tags:
            print(f"⚠️  跳过了 {len(skipped_tags)} 个重复标签: {', '.join(skipped_tags[:5])}{'...' if len(skipped_tags) > 5 else ''}")
        
        if not new_tags and not skipped_tags:
            print("✅ 所有标签已存在")
            
    except Exception as e:
        print(f"❌ 添加标签失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_database_schema()
    add_new_predefined_tags()