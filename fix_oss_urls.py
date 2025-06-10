"""
修复OSS图片URL的脚本 - 增强版本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models.image import Image
from app.services.storage_service import StorageManager
from sqlalchemy import text

def fix_oss_image_urls():
    """修复现有OSS图片的URL"""
    print("🔧 开始修复OSS图片URL...")
    
    db = next(get_db())
    storage = StorageManager()
    
    try:
        # 检查必要字段是否存在
        columns_result = db.execute(text("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'images'
        """)).fetchall()
        
        existing_columns = [row[0] for row in columns_result]
        
        if 'oss_key' not in existing_columns or 'url' not in existing_columns:
            print("❌ 请先运行数据库迁移: python migrate.py")
            return False
        
        # 查找所有图片
        images = db.query(Image).all()
        print(f"📊 总共找到 {len(images)} 张图片")
        
        if not images:
            print("⚠️ 数据库中没有图片记录")
            return True
        
        fixed_count = 0
        skipped_count = 0
        removed_count = 0
        
        # 获取OSS中的所有文件
        print("📥 获取OSS文件列表...")
        try:
            oss_objects = storage.list_oss_objects("ai-pose-gallery/")
            print(f"📊 OSS中找到 {len(oss_objects)} 个文件")
            
            # 创建OSS文件名索引
            oss_by_filename = {}
            for obj in oss_objects:
                filename = obj['key'].split('/')[-1]
                oss_by_filename[filename] = obj
                
        except Exception as e:
            print(f"❌ 获取OSS文件列表失败: {e}")
            return False
        
        for image in images:
            try:
                # 检查是否是本地存储的图片（应该删除）
                if (image.file_path and 
                    image.file_path.startswith('uploads/') and
                    not image.oss_key):
                    
                    print(f"🗑️ 删除本地存储的图片记录: {image.id} - {image.filename}")
                    db.delete(image)
                    db.commit()
                    removed_count += 1
                    continue
                
                # 检查URL是否需要修复
                needs_fix = False
                if (not image.url or 
                    'uploads/' in image.url or
                    not image.url.startswith('https://') or
                    'ai-pose-gallery' not in image.url):
                    needs_fix = True
                
                if needs_fix:
                    # 尝试根据文件名匹配OSS文件
                    matched_obj = None
                    
                    # 先尝试直接文件名匹配
                    if image.filename in oss_by_filename:
                        matched_obj = oss_by_filename[image.filename]
                        print(f"🎯 文件名匹配: {image.filename}")
                    
                    # 如果没有找到，尝试其他匹配方式
                    if not matched_obj:
                        for obj in oss_objects:
                            # 尝试大小匹配
                            if abs(obj['size'] - (image.file_size or 0)) < 1024:
                                matched_obj = obj
                                print(f"🎯 大小匹配: {image.filename} -> {obj['key']}")
                                break
                    
                    if matched_obj:
                        # 更新数据库记录
                        oss_url = storage.get_oss_url(matched_obj['key'])
                        
                        db.execute(text("""
                            UPDATE images 
                            SET oss_key = :oss_key, 
                                file_path = :file_path, 
                                url = :url
                            WHERE id = :image_id
                        """), {
                            'oss_key': matched_obj['key'],
                            'file_path': matched_obj['key'],
                            'url': oss_url,
                            'image_id': image.id
                        })
                        
                        db.commit()
                        fixed_count += 1
                        print(f"✅ 修复图片 {image.id}: {image.filename}")
                        print(f"   新URL: {oss_url}")
                    else:
                        print(f"⚠️ 未找到OSS文件，删除记录: {image.id} - {image.filename}")
                        db.delete(image)
                        db.commit()
                        removed_count += 1
                else:
                    print(f"⏭️ 跳过已正确的图片: {image.id} - {image.filename}")
                    skipped_count += 1
                    
            except Exception as e:
                print(f"❌ 处理图片 {image.id} 失败: {e}")
                db.rollback()
                continue
        
        print(f"\n🎉 修复完成!")
        print(f"✅ 成功修复: {fixed_count} 张")
        print(f"🗑️ 删除记录: {removed_count} 张")
        print(f"⏭️ 已跳过: {skipped_count} 张")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False
    finally:
        db.close()
    
    return True

def clean_local_images():
    """清理本地存储的图片记录"""
    print("🧹 清理本地存储的图片记录...")
    
    db = next(get_db())
    
    try:
        # 查找所有本地存储的图片
        local_images = db.execute(text("""
            SELECT id, filename, file_path, oss_key, url
            FROM images 
            WHERE file_path LIKE 'uploads/%' 
            OR (oss_key IS NULL AND file_path NOT LIKE 'ai-pose-gallery/%')
            OR url LIKE '%/uploads/%'
        """)).fetchall()
        
        if not local_images:
            print("✅ 没有找到需要清理的本地图片记录")
            return True
        
        print(f"📊 找到 {len(local_images)} 条本地存储记录:")
        for img in local_images:
            print(f"  {img[0]}: {img[1]} | path: {img[2]} | oss_key: {img[3]} | url: {img[4]}")
        
        confirm = input("\n确认删除这些记录吗？(y/N): ")
        if confirm.lower() != 'y':
            print("❌ 用户取消操作")
            return False
        
        # 删除记录
        result = db.execute(text("""
            DELETE FROM images 
            WHERE file_path LIKE 'uploads/%' 
            OR (oss_key IS NULL AND file_path NOT LIKE 'ai-pose-gallery/%')
            OR url LIKE '%/uploads/%'
        """))
        
        db.commit()
        print(f"✅ 成功删除 {result.rowcount} 条记录")
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()
    
    return True

def check_image_urls():
    """检查图片URL状态"""
    print("🔍 检查图片URL状态...")
    
    db = next(get_db())
    
    try:
        # 统计不同类型的图片
        results = db.execute(text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN oss_key IS NOT NULL AND url LIKE 'https://%ai-pose-gallery%' THEN 1 ELSE 0 END) as oss_count,
                SUM(CASE WHEN file_path LIKE 'uploads/%' OR url LIKE '%/uploads/%' THEN 1 ELSE 0 END) as local_count,
                SUM(CASE WHEN url NOT LIKE 'https://%' OR url IS NULL THEN 1 ELSE 0 END) as invalid_count
            FROM images
        """)).fetchone()
        
        total, oss_count, local_count, invalid_count = results
        
        print(f"\n📊 图片URL统计:")
        print(f"🌐 正确的OSS图片: {oss_count} 张")
        print(f"💾 本地存储图片: {local_count} 张")
        print(f"❌ 无效图片: {invalid_count} 张")
        print(f"📊 总计: {total} 张")
        
        # 显示OSS图片示例
        sample_oss = db.execute(text("""
            SELECT id, filename, url 
            FROM images 
            WHERE oss_key IS NOT NULL AND url LIKE '%ai-pose-gallery%' 
            LIMIT 3
        """)).fetchall()
        
        if sample_oss:
            print(f"\n🌐 正确的OSS图片示例:")
            for img in sample_oss:
                print(f"  {img[0]}: {img[1]} -> {img[2]}")
        
        # 显示问题图片
        problem_images = db.execute(text("""
            SELECT id, filename, file_path, oss_key, url 
            FROM images 
            WHERE file_path LIKE 'uploads/%' 
            OR url LIKE '%/uploads/%'
            OR url NOT LIKE '%ai-pose-gallery%'
            LIMIT 5
        """)).fetchall()
        
        if problem_images:
            print(f"\n⚠️ 需要修复的图片示例:")
            for img in problem_images:
                print(f"  {img[0]}: {img[1]} | path: {img[2]} | oss_key: {img[3]} | url: {img[4]}")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='修复OSS图片URL')
    parser.add_argument('--check', action='store_true', help='仅检查不修复')
    parser.add_argument('--clean', action='store_true', help='清理本地存储记录')
    parser.add_argument('--force', action='store_true', help='强制重新修复所有图片')
    args = parser.parse_args()
    
    if args.check:
        check_image_urls()
    elif args.clean:
        success = clean_local_images()
        if success:
            print("\n" + "="*50)
            check_image_urls()
    else:
        success = fix_oss_image_urls()
        if success:
            print("\n" + "="*50)
            check_image_urls()
        sys.exit(0 if success else 1)