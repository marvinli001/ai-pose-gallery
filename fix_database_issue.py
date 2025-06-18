"""
修复数据库事务问题的临时脚本
"""
import sys
import traceback
from app.database import SessionLocal
from app.services.database_service import DatabaseService
from app.models.image import Image, Tag, ImageTag

def test_get_image_tags():
    """测试 get_image_tags 方法"""
    db = SessionLocal()
    try:
        db_service = DatabaseService(db)
        
        # 测试有问题的图片ID
        problem_image_ids = [1, 2]
        
        for image_id in problem_image_ids:
            print(f"\n🔍 测试图片 ID: {image_id}")
            
            try:
                # 检查图片是否存在
                image = db_service.get_image_by_id(image_id, include_deleted=True)
                if not image:
                    print(f"⚠️ 图片 {image_id} 不存在")
                    continue
                
                print(f"📄 图片信息: {image.filename}, 状态: {image.ai_analysis_status}")
                
                # 尝试获取标签
                tags = db_service.get_image_tags(image_id)
                print(f"✅ 成功获取 {len(tags)} 个标签")
                
                for tag in tags:
                    print(f"  - {tag.name} ({tag.category})")
                    
            except Exception as e:
                print(f"❌ 测试图片 {image_id} 失败: {e}")
                traceback.print_exc()
                
        db.commit()
        print(f"\n✅ 测试完成")
        
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

def check_database_integrity():
    """检查数据库完整性"""
    db = SessionLocal()
    try:
        print("🔍 检查数据库完整性...")
        
        # 检查image_tags表的外键完整性
        orphaned_tags = db.execute("""
            SELECT it.id, it.image_id, it.tag_id 
            FROM image_tags it 
            LEFT JOIN images i ON it.image_id = i.id 
            LEFT JOIN tags t ON it.tag_id = t.id 
            WHERE i.id IS NULL OR t.id IS NULL
            LIMIT 10
        """).fetchall()
        
        if orphaned_tags:
            print(f"⚠️ 发现 {len(orphaned_tags)} 个孤立的标签关联记录:")
            for orphan in orphaned_tags:
                print(f"  - ImageTag ID: {orphan[0]}, Image ID: {orphan[1]}, Tag ID: {orphan[2]}")
            return False
        else:
            print("✅ 没有发现孤立的标签关联记录")
            
        # 检查数据库连接状态
        db.execute("SELECT 1").fetchone()
        print("✅ 数据库连接正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库完整性检查失败: {e}")
        traceback.print_exc()
        return False
    finally:
        db.close()

def fix_orphaned_records():
    """清理孤立的记录"""
    db = SessionLocal()
    try:
        print("🧹 开始清理孤立记录...")
        
        # 删除指向不存在图片的标签关联
        deleted_count = db.execute("""
            DELETE it FROM image_tags it 
            LEFT JOIN images i ON it.image_id = i.id 
            WHERE i.id IS NULL
        """).rowcount
        
        if deleted_count > 0:
            print(f"🗑️ 删除了 {deleted_count} 个指向不存在图片的标签关联")
        
        # 删除指向不存在标签的关联
        deleted_count2 = db.execute("""
            DELETE it FROM image_tags it 
            LEFT JOIN tags t ON it.tag_id = t.id 
            WHERE t.id IS NULL
        """).rowcount
        
        if deleted_count2 > 0:
            print(f"🗑️ 删除了 {deleted_count2} 个指向不存在标签的关联")
        
        db.commit()
        print("✅ 清理完成")
        
    except Exception as e:
        print(f"❌ 清理孤立记录失败: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

def main():
    """主函数"""
    print("🚀 开始数据库问题诊断和修复...")
    
    # 1. 检查数据库完整性
    if not check_database_integrity():
        print("\n🔧 发现数据库完整性问题，开始修复...")
        fix_orphaned_records()
        
        # 再次检查
        if not check_database_integrity():
            print("❌ 修复后仍有问题，请手动检查数据库")
            return
    
    # 2. 测试有问题的方法
    test_get_image_tags()
    
    print("\n✅ 诊断和修复完成")

if __name__ == "__main__":
    main()