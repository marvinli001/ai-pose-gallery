"""
数据库初始化脚本
"""
from sqlalchemy.orm import Session
from app.database import SessionLocal, create_tables
from app.models.image import Tag, PREDEFINED_TAGS, TagCategory

def init_predefined_tags():
    """初始化预定义标签"""
    db = SessionLocal()
    try:
        print("🏷️  初始化预定义标签...")
        
        # 检查是否已经有标签
        existing_count = db.query(Tag).count()
        if existing_count > 0:
            print(f"⚠️  数据库中已有 {existing_count} 个标签")
            
            # 检查是否需要添加新标签
            existing_names = {tag.name for tag in db.query(Tag.name).all()}
            new_tags = [tag for tag in PREDEFINED_TAGS if tag['name'] not in existing_names]
            
            if new_tags:
                print(f"📝 发现 {len(new_tags)} 个新标签需要添加...")
                for tag_data in new_tags:
                    tag = Tag(**tag_data)
                    db.add(tag)
                db.commit()
                print(f"✅ 成功添加 {len(new_tags)} 个新标签")
            else:
                print("✅ 所有预定义标签已存在，跳过初始化")
            return
        
        # 添加预定义标签
        added_count = 0
        for tag_data in PREDEFINED_TAGS:
            # 检查标签是否已存在
            existing_tag = db.query(Tag).filter(Tag.name == tag_data['name']).first()
            if not existing_tag:
                tag = Tag(**tag_data)
                db.add(tag)
                added_count += 1
            else:
                print(f"⚠️  标签 '{tag_data['name']}' 已存在，跳过")
        
        db.commit()
        print(f"✅ 成功初始化 {added_count} 个预定义标签")
        
        # 显示各分类的标签数量
        print("\n📊 标签分类统计:")
        categories = [
            (TagCategory.POSE, "姿势类型"),
            (TagCategory.GENDER, "性别"),
            (TagCategory.AGE, "年龄"),
            (TagCategory.CLOTHING, "服装"),
            (TagCategory.PROPS, "道具"),
            (TagCategory.SCENE, "场景"),
            (TagCategory.LIGHTING, "光线"),
            (TagCategory.ANGLE, "角度"),
            (TagCategory.EMOTION, "表情"),
            (TagCategory.ACTION, "动作"),
        ]
        
        for category, name in categories:
            count = db.query(Tag).filter(Tag.category == category).count()
            print(f"   {name}: {count} 个")
            
    except Exception as e:
        print(f"❌ 标签初始化失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def verify_database():
    """验证数据库结构"""
    db = SessionLocal()
    try:
        print("\n🔍 验证数据库结构...")
        
        # 检查表是否存在
        from app.models.image import Image, Tag, ImageTag
        
        image_count = db.query(Image).count()
        tag_count = db.query(Tag).count()
        image_tag_count = db.query(ImageTag).count()
        
        print(f"✅ 数据表验证成功:")
        print(f"   images 表: {image_count} 条记录")
        print(f"   tags 表: {tag_count} 条记录")
        print(f"   image_tags 表: {image_tag_count} 条记录")
        
        # 测试查询一些标签
        sample_tags = db.query(Tag).limit(10).all()
        print(f"\n📋 示例标签:")
        for tag in sample_tags:
            print(f"   {tag.name} ({tag.category})")
            
        # 检查是否有重复标签名
        from sqlalchemy import func
        duplicate_names = db.query(Tag.name, func.count(Tag.id)).group_by(Tag.name).having(func.count(Tag.id) > 1).all()
        if duplicate_names:
            print(f"\n⚠️  发现重复标签名:")
            for name, count in duplicate_names:
                print(f"   {name}: {count} 个")
        else:
            print(f"\n✅ 没有重复标签名")
            
    except Exception as e:
        print(f"❌ 数据库验证失败: {e}")
        raise
    finally:
        db.close()

def main():
    """主函数"""
    print("🚀 开始数据库初始化...")
    
    try:
        # 创建数据表
        print("📋 创建数据表...")
        create_tables()
        
        # 初始化预定义标签
        init_predefined_tags()
        
        # 验证数据库
        verify_database()
        
        print("\n🎉 数据库初始化完成!")
        
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        raise

if __name__ == "__main__":
    main()