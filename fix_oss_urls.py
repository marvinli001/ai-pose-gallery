"""
修复OSS图片URL的脚本 - MySQL版本
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
        
        # 获取OSS中的所有文件
        print("📥 获取OSS文件列表...")
        try:
            oss_objects = storage.list_oss_objects("ai-pose-gallery/")
            print(f"📊 OSS中找到 {len(oss_objects)} 个文件")
        except Exception as e:
            print(f"❌ 获取OSS文件列表失败: {e}")
            return False
        
        for image in images:
            try:
                # 如果已经有正确的OSS信息，跳过
                if (image.oss_key and 
                    image.url and 
                    image.url.startswith('https://') and
                    'ai-pose-gallery' in image.url):
                    print(f"⏭️ 跳过已修复的图片: {image.id} - {image.filename}")
                    skipped_count += 1
                    continue
                
                # 尝试匹配OSS文件
                matched_obj = None
                
                # 方法1：精确匹配文件大小（差异小于1KB）
                for obj in oss_objects:
                    if abs(obj['size'] - (image.file_size or 0)) < 1024:
                        matched_obj = obj
                        print(f"🎯 通过文件大小匹配: {image.filename} -> {obj['key']}")
                        break
                
                # 方法2：文件名相似性匹配
                if not matched_obj and image.filename:
                    # 提取不含扩展名的文件名
                    base_name = os.path.splitext(image.filename)[0]
                    
                    for obj in oss_objects:
                        obj_filename = obj['key'].split('/')[-1]
                        obj_base_name = os.path.splitext(obj_filename)[0]
                        
                        # 检查文件名包含关系
                        if (base_name in obj_filename or 
                            obj_base_name in image.filename or
                            image.original_filename in obj_filename):
                            matched_obj = obj
                            print(f"🎯 通过文件名匹配: {image.filename} -> {obj['key']}")
                            break
                
                # 方法3：如果文件路径包含明显的OSS特征
                if not matched_obj and image.file_path:
                    # 检查是否是错误的OSS路径格式
                    if ('uploads' in image.file_path and 
                        len(image.filename) > 20 and
                        not image.file_path.startswith('/')):
                        
                        # 尝试通过时间范围和大小范围匹配
                        for obj in oss_objects:
                            size_diff = abs(obj['size'] - (image.file_size or 0))
                            if size_diff < 5120:  # 5KB误差
                                matched_obj = obj
                                print(f"🎯 通过大小范围匹配: {image.filename} -> {obj['key']}")
                                break
                
                # 如果找到匹配的OSS文件，更新记录
                if matched_obj:
                    # 构建正确的OSS URL
                    oss_url = storage.get_oss_url(matched_obj['key'])
                    
                    # 更新数据库记录
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
                    print(f"   -> {oss_url}")
                    
                else:
                    print(f"⚠️ 未找到匹配的OSS文件: {image.id} - {image.filename} (size: {image.file_size})")
                    
            except Exception as e:
                print(f"❌ 修复图片 {image.id} 失败: {e}")
                db.rollback()
                continue
        
        print(f"\n🎉 修复完成!")
        print(f"✅ 成功修复: {fixed_count} 张")
        print(f"⏭️ 已跳过: {skipped_count} 张")
        print(f"📊 总计处理: {len(images)} 张")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
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
                SUM(CASE WHEN oss_key IS NOT NULL AND url LIKE 'https://%' THEN 1 ELSE 0 END) as oss_count,
                SUM(CASE WHEN oss_key IS NULL AND file_path NOT LIKE 'http%' THEN 1 ELSE 0 END) as local_count,
                SUM(CASE WHEN (oss_key IS NULL OR url IS NULL) AND file_path NOT LIKE '/uploads/%' THEN 1 ELSE 0 END) as invalid_count
            FROM images
        """)).fetchone()
        
        total, oss_count, local_count, invalid_count = results
        
        print(f"\n📊 图片URL统计:")
        print(f"🌐 OSS图片: {oss_count} 张")
        print(f"💾 本地图片: {local_count} 张")
        print(f"❌ 无效图片: {invalid_count} 张")
        print(f"📊 总计: {total} 张")
        
        # 显示一些示例
        sample_oss = db.execute(text("""
            SELECT id, filename, url 
            FROM images 
            WHERE oss_key IS NOT NULL AND url LIKE 'https://%' 
            LIMIT 3
        """)).fetchall()
        
        if sample_oss:
            print(f"\n🌐 OSS图片示例:")
            for img in sample_oss:
                print(f"  {img[0]}: {img[1]} -> {img[2]}")
        
        # 显示问题图片
        problem_images = db.execute(text("""
            SELECT id, filename, file_path, oss_key, url 
            FROM images 
            WHERE (oss_key IS NULL OR url IS NULL OR url NOT LIKE 'https://%') 
            AND file_path LIKE '%uploads%'
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
    parser.add_argument('--force', action='store_true', help='强制重新修复所有图片')
    args = parser.parse_args()
    
    if args.check:
        check_image_urls()
    else:
        success = fix_oss_image_urls()
        if success:
            print("\n" + "="*50)
            check_image_urls()
        sys.exit(0 if success else 1)