"""
数据库管理工具
"""
import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.image import Image, Tag, ImageTag

def show_stats():
    """显示数据库统计信息"""
    db = SessionLocal()
    try:
        print("📊 数据库统计信息:")
        print(f"   图片总数: {db.query(Image).count()}")
        print(f"   激活图片: {db.query(Image).filter(Image.is_active == True).count()}")
        print(f"   标签总数: {db.query(Tag).count()}")
        print(f"   激活标签: {db.query(Tag).filter(Tag.is_active == True).count()}")
        print(f"   关联总数: {db.query(ImageTag).count()}")
        
        print("\n🏷️  标签分类统计:")
        from sqlalchemy import func
        category_stats = db.query(
            Tag.category, 
            func.count(Tag.id).label('count')
        ).filter(Tag.is_active == True).group_by(Tag.category).all()
        
        for category, count in category_stats:
            print(f"   {category}: {count} 个")
            
    finally:
        db.close()

def list_tags(category=None, limit=10):
    """列出标签"""
    db = SessionLocal()
    try:
        query = db.query(Tag).filter(Tag.is_active == True)
        if category:
            query = query.filter(Tag.category == category)
        
        tags = query.order_by(Tag.usage_count.desc()).limit(limit).all()
        
        print(f"\n🏷️  标签列表 {'(' + category + ')' if category else ''}:")
        for tag in tags:
            print(f"   {tag.name} ({tag.category}) - 使用次数: {tag.usage_count}")
            
    finally:
        db.close()

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python db_manager.py stats              # 显示统计")
        print("  python db_manager.py tags               # 列出所有标签")
        print("  python db_manager.py tags [category]    # 列出指定分类标签")
        return
    
    command = sys.argv[1]
    
    if command == "stats":
        show_stats()
    elif command == "tags":
        category = sys.argv[2] if len(sys.argv) > 2 else None
        list_tags(category)
    else:
        print(f"未知命令: {command}")

if __name__ == "__main__":
    main()