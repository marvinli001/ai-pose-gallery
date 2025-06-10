"""
修复OSS图片URL的脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db
from app.models.image import Image
from app.services.storage_service import StorageManager

def fix_oss_image_urls():
    """修复现有OSS图片的URL"""
    print("🔧 开始修复OSS图片URL...")
    
    db = next(get_db())
    storage = StorageManager()
    
    try:
        # 查找所有可能是OSS图片的记录
        images = db.query(Image).all()
        
        print(f"📊 总共找到 {len(images)} 张图片")
        
        fixed_count = 0
        skipped_count = 0
        
        # 获取OSS中的所有文件
        print("📥 获取OSS文件列表...")
        oss_objects = storage.list_oss_objects("ai-pose-gallery/")
        print(f"📊 OSS中找到 {len(oss_objects)} 个文件")
        
        for image in images:
            try:
                # 如果已经有正确的OSS信息，跳过
                if image.oss_key and image.url and image.url.startswith('https://'):
                    print(f"⏭️ 跳过已修复的图片: {image.id}")
                    skipped_count += 1
                    continue
                
                # 尝试根据文件大小匹配OSS文件
                matched_obj = None
                
                # 方法1：精确匹配文件大小
                for obj in oss_objects:
                    if abs(obj['size'] - image.file_size) < 100:  # 大小差异小于100字节
                        matched_obj = obj
                        break
                
                # 方法2：如果文件名相似
                if not matched_obj:
                    for obj in oss_objects:
                        obj_filename = obj['key'].split('/')[-1]
                        if (image.filename in obj_filename or 
                            obj_filename in image.filename or
                            image.original_filename in obj_filename):
                            matched_obj = obj
                            break
                
                # 如果找到匹配的OSS文件
                if matched_obj:
                    # 更新图片记录
                    image.oss_key = matched_obj['key']
                    image.file_path = matched_obj['key']
                    image.url = storage.get_oss_url(matched_obj['key'])
                    
                    db.commit()
                    fixed_count += 1
                    print(f"✅ 修复图片 {image.id}: {image.filename} -> {image.url}")
                    
                else:
                    print(f"⚠️ 未找到匹配的OSS文件: {image.id} - {image.filename}")
                    
            except Exception as e:
                print(f"❌ 修复图片 {image.id} 失败: {e}")
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
        images = db.query(Image).all()
        
        local_count = 0
        oss_count = 0
        invalid_count = 0
        
        for image in images:
            if image.oss_key and image.url and image.url.startswith('https://'):
                oss_count += 1
            elif image.file_path and not image.file_path.startswith('http'):
                local_count += 1
            else:
                invalid_count += 1
                print(f"⚠️ 无效图片: {image.id} - {image.filename}")
        
        print(f"\n📊 图片URL统计:")
        print(f"🌐 OSS图片: {oss_count} 张")
        print(f"💾 本地图片: {local_count} 张")
        print(f"❌ 无效图片: {invalid_count} 张")
        print(f"📊 总计: {len(images)} 张")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='修复OSS图片URL')
    parser.add_argument('--check', action='store_true', help='仅检查不修复')
    args = parser.parse_args()
    
    if args.check:
        check_image_urls()
    else:
        success = fix_oss_image_urls()
        if success:
            print("\n" + "="*50)
            check_image_urls()
        sys.exit(0 if success else 1)