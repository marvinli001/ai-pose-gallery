"""
图片处理服务
"""
import os
import uuid
import aiofiles
from pathlib import Path
from PIL import Image
from typing import Tuple

from app.config import get_settings

settings = get_settings()


class ImageService:
    """图片处理服务类"""
    
    @staticmethod
    def validate_image_file(filename: str, file_size: int) -> Tuple[bool, str]:
        """验证图片文件"""
        # 检查文件扩展名
        ext = Path(filename).suffix.lower()
        if ext not in settings.allowed_extensions:
            return False, f"不支持的文件类型：{ext}。支持的类型：{', '.join(settings.allowed_extensions)}"
        
        # 检查文件大小
        if file_size > settings.max_file_size:
            max_mb = settings.max_file_size / (1024 * 1024)
            return False, f"文件太大：{file_size / (1024 * 1024):.1f}MB。最大允许：{max_mb:.1f}MB"
        
        return True, "验证通过"
    
    @staticmethod
    def generate_filename(original_filename: str) -> str:
        """生成唯一文件名"""
        ext = Path(original_filename).suffix.lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        return unique_name
    
    @staticmethod
    async def save_uploaded_file(file_content: bytes, filename: str) -> str:
        """保存上传的文件"""
        # 确保目录存在
        os.makedirs(settings.upload_dir, exist_ok=True)
        
        file_path = os.path.join(settings.upload_dir, filename)
        
        # 异步写入文件
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        return file_path
    
    @staticmethod
    def get_image_info(file_path: str) -> Tuple[int, int]:
        """获取图片信息"""
        try:
            with Image.open(file_path) as img:
                return img.width, img.height
        except Exception as e:
            print(f"❌ 获取图片信息失败: {e}")
            return 0, 0
    
    @staticmethod
    def get_file_url(filename: str) -> str:
        """获取文件访问URL"""
        return f"/uploads/{filename}"
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """删除文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"❌ 删除文件失败: {e}")
            return False