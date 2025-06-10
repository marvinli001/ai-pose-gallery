"""
云存储服务 - 支持阿里云OSS和AWS S3
"""
import os
import uuid
import asyncio
from typing import Optional, Tuple, Dict, Any
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path
from PIL import Image
import aiofiles
import oss2
import boto3
from botocore.exceptions import ClientError
from urllib.parse import urljoin

from app.config import get_settings

settings = get_settings()


class StorageService:
    """云存储服务基类"""
    
    def __init__(self):
        self.settings = settings
    
    async def upload_file(self, file_content: bytes, filename: str, content_type: str = None) -> Dict[str, Any]:
        """上传文件"""
        raise NotImplementedError
    
    async def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        raise NotImplementedError
    
    def get_file_url(self, file_path: str) -> str:
        """获取文件访问URL"""
        raise NotImplementedError
    
    def generate_filename(self, original_filename: str) -> str:
        """生成唯一文件名"""
        ext = Path(original_filename).suffix.lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        return unique_name


class LocalStorageService(StorageService):
    """本地文件存储服务"""
    
    async def upload_file(self, file_content: bytes, filename: str, content_type: str = None) -> Dict[str, Any]:
        """上传文件到本地"""
        file_path = os.path.join(self.settings.upload_dir, filename)
        
        # 确保目录存在
        os.makedirs(self.settings.upload_dir, exist_ok=True)
        
        # 异步写入文件
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        return {
            "success": True,
            "file_path": file_path,
            "url": self.get_file_url(filename),
            "storage_type": "local"
        }
    
    async def delete_file(self, file_path: str) -> bool:
        """删除本地文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"❌ 删除本地文件失败: {e}")
            return False
    
    def get_file_url(self, filename: str) -> str:
        """获取本地文件URL"""
        return f"/uploads/{filename}"


class OSSStorageService(StorageService):
    """阿里云OSS存储服务"""
    
    def __init__(self):
        super().__init__()
        self.auth = oss2.Auth(
            self.settings.oss_access_key_id,
            self.settings.oss_access_key_secret
        )
        self.bucket = oss2.Bucket(
            self.auth,
            self.settings.oss_endpoint,
            self.settings.oss_bucket_name
        )
    
    async def upload_file(self, file_content: bytes, filename: str, content_type: str = None) -> Dict[str, Any]:
        """上传文件到阿里云OSS"""
        try:
            # 构建OSS文件路径
            oss_key = f"{self.settings.oss_folder_prefix}{filename}"
            
            # 设置元数据
            headers = {}
            if content_type:
                headers['Content-Type'] = content_type
            
            # 在新线程中执行OSS上传（因为oss2不支持async）
            def _upload():
                return self.bucket.put_object(oss_key, file_content, headers=headers)
            
            result = await asyncio.get_event_loop().run_in_executor(None, _upload)
            
            if result.status == 200:
                return {
                    "success": True,
                    "file_path": oss_key,
                    "url": self.get_file_url(oss_key),
                    "storage_type": "oss",
                    "etag": result.etag
                }
            else:
                raise Exception(f"OSS upload failed with status: {result.status}")
                
        except Exception as e:
            print(f"❌ OSS上传失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "storage_type": "oss"
            }
    
    async def delete_file(self, oss_key: str) -> bool:
        """删除OSS文件"""
        try:
            def _delete():
                return self.bucket.delete_object(oss_key)
            
            result = await asyncio.get_event_loop().run_in_executor(None, _delete)
            return result.status == 204
            
        except Exception as e:
            print(f"❌ 删除OSS文件失败: {e}")
            return False
    
    def get_file_url(self, oss_key: str) -> str:
        """获取OSS文件URL"""
        if self.settings.oss_custom_domain:
            # 使用自定义域名
            return f"https://{self.settings.oss_custom_domain}/{oss_key}"
        else:
            # 使用默认域名
            return f"https://{self.settings.oss_bucket_name}.{self.settings.oss_endpoint}/{oss_key}"
    
    async def get_signed_url(self, oss_key: str, expires: int = 3600) -> str:
        """获取签名URL（私有文件访问）"""
        try:
            def _get_signed_url():
                return self.bucket.sign_url('GET', oss_key, expires)
            
            return await asyncio.get_event_loop().run_in_executor(None, _get_signed_url)
            
        except Exception as e:
            print(f"❌ 生成OSS签名URL失败: {e}")
            return self.get_file_url(oss_key)

    async def list_objects(self, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, Any]]:
        """列出OSS存储桶中的对象"""
        try:
            def _list_objects():
                return self.bucket.list_objects_v2(prefix=prefix, max_keys=max_keys)
            
            result = await asyncio.get_event_loop().run_in_executor(None, _list_objects)
            
            objects = []
            for obj in result.object_list:
                # 只返回图片文件
                if any(obj.key.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']):
                    objects.append({
                        'key': obj.key,
                        'size': obj.size,
                        'last_modified': obj.last_modified,
                        'etag': obj.etag
                    })
            
            return objects
        except Exception as e:
            print(f"❌ 列出OSS对象失败: {e}")
            return []

    async def get_object_content(self, oss_key: str) -> bytes:
        """获取OSS对象内容"""
        try:
            def _get_object():
                return self.bucket.get_object(oss_key)
            
            result = await asyncio.get_event_loop().run_in_executor(None, _get_object)
            return result.read()
        except Exception as e:
            print(f"❌ 获取OSS对象内容失败: {e}")
            return b""

class S3StorageService(StorageService):
    """AWS S3存储服务"""
    
    def __init__(self):
        super().__init__()
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.settings.s3_access_key,
            aws_secret_access_key=self.settings.s3_secret_key,
            region_name=self.settings.s3_region
        )
    
    async def upload_file(self, file_content: bytes, filename: str, content_type: str = None) -> Dict[str, Any]:
        """上传文件到AWS S3"""
        try:
            s3_key = f"ai-pose-gallery/{filename}"
            
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            # 在新线程中执行S3上传
            def _upload():
                return self.s3_client.put_object(
                    Bucket=self.settings.s3_bucket_name,
                    Key=s3_key,
                    Body=file_content,
                    **extra_args
                )
            
            result = await asyncio.get_event_loop().run_in_executor(None, _upload)
            
            return {
                "success": True,
                "file_path": s3_key,
                "url": self.get_file_url(s3_key),
                "storage_type": "s3",
                "etag": result.get('ETag', '').strip('"')
            }
            
        except ClientError as e:
            print(f"❌ S3上传失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "storage_type": "s3"
            }
    
    async def delete_file(self, s3_key: str) -> bool:
        """删除S3文件"""
        try:
            def _delete():
                return self.s3_client.delete_object(
                    Bucket=self.settings.s3_bucket_name,
                    Key=s3_key
                )
            
            await asyncio.get_event_loop().run_in_executor(None, _delete)
            return True
            
        except ClientError as e:
            print(f"❌ 删除S3文件失败: {e}")
            return False
    
    def get_file_url(self, s3_key: str) -> str:
        """获取S3文件URL"""
        if self.settings.s3_custom_domain:
            return f"https://{self.settings.s3_custom_domain}/{s3_key}"
        else:
            return f"https://{self.settings.s3_bucket_name}.s3.{self.settings.s3_region}.amazonaws.com/{s3_key}"


class StorageManager:
    def __init__(self):
        self.storage_type = os.getenv('STORAGE_TYPE', 'local')
        if self.storage_type == 'oss':
            self.oss_enabled = os.getenv('OSS_ENABLED', 'false').lower() == 'true'
            self.oss_bucket = os.getenv('OSS_BUCKET_NAME', '')
            self.oss_endpoint = os.getenv('OSS_ENDPOINT', '')
            self.oss_region = os.getenv('OSS_REGION', '')
            self.oss_custom_domain = os.getenv('OSS_CUSTOM_DOMAIN', '')
            self.oss_folder_prefix = os.getenv('OSS_FOLDER_PREFIX', '').rstrip('/')
            
            # 修复自定义域名协议
            if self.oss_custom_domain:
                if not self.oss_custom_domain.startswith(('http://', 'https://')):
                    self.oss_custom_domain = f"https://{self.oss_custom_domain}"
                self.oss_custom_domain = self.oss_custom_domain.rstrip('/')

    def get_image_url(self, file_path: str) -> str:
        """获取图片访问URL"""
        if not file_path:
            return "/static/images/placeholder.jpg"
            
        # 移除开头的斜杠
        clean_path = file_path.lstrip('/')
        
        if self.storage_type == 'oss' and self.oss_enabled:
            # 移除重复的前缀
            if self.oss_folder_prefix and clean_path.startswith(self.oss_folder_prefix):
                clean_path = clean_path[len(self.oss_folder_prefix):].lstrip('/')
            
            # 构建完整的OSS URL
            if self.oss_custom_domain:
                # 使用自定义域名
                if self.oss_folder_prefix:
                    full_url = f"{self.oss_custom_domain}/{self.oss_folder_prefix}/{clean_path}"
                else:
                    full_url = f"{self.oss_custom_domain}/{clean_path}"
                return full_url
            else:
                # 使用默认OSS域名
                if self.oss_folder_prefix:
                    full_path = f"{self.oss_folder_prefix}/{clean_path}"
                else:
                    full_path = clean_path
                return f"https://{self.oss_bucket}.{self.oss_endpoint}/{full_path}"
        else:
            # 本地存储
            return f"/uploads/{clean_path}"
        
    def get_full_image_path(self, filename: str) -> str:
        """获取完整的图片存储路径"""
        if self.storage_type == 'oss':
            if self.oss_folder_prefix:
                return f"{self.oss_folder_prefix}/{filename}"
            return filename
        else:
            return filename
        
    

    
    @property
    def service(self) -> StorageService:
        """获取存储服务实例"""
        if self._service is None:
            if self.settings.use_oss_storage:
                self._service = OSSStorageService()
                print("🗂️  使用阿里云OSS存储")
            elif self.settings.use_s3_storage:
                self._service = S3StorageService()
                print("🗂️  使用AWS S3存储")
            else:
                self._service = LocalStorageService()
                print("🗂️  使用本地文件存储")
        
        return self._service
    
    async def upload_image(self, file_content: bytes, original_filename: str) -> Dict[str, Any]:
        """上传图片"""
        # 验证文件
        file_size = len(file_content)
        is_valid, message = self.validate_image_file(original_filename, file_size)
        if not is_valid:
            return {"success": False, "error": message}
        
        # 生成文件名
        filename = self.service.generate_filename(original_filename)
        
        # 检测内容类型
        content_type = self.get_content_type(original_filename)
        
        # 上传文件
        upload_result = await self.service.upload_file(file_content, filename, content_type)
        
        if upload_result.get("success"):
            # 获取图片尺寸信息
            width, height = self.get_image_dimensions(file_content)
            
            upload_result.update({
                "original_filename": original_filename,
                "filename": filename,
                "file_size": file_size,
                "width": width,
                "height": height,
                "content_type": content_type
            })
        
        return upload_result
    
    async def delete_image(self, file_path: str) -> bool:
        """删除图片"""
        return await self.service.delete_file(file_path)
    
    def get_image_url(self, file_path: str) -> str:
        """获取图片URL"""
        if self.settings.use_oss_storage or self.settings.use_s3_storage:
            return self.service.get_file_url(file_path)
        else:
            # 本地存储，提取文件名
            filename = Path(file_path).name
            return self.service.get_file_url(filename)
    
    def validate_image_file(self, filename: str, file_size: int) -> Tuple[bool, str]:
        """验证图片文件"""
        # 检查文件扩展名
        ext = Path(filename).suffix.lower()
        if ext not in self.settings.allowed_extensions:
            return False, f"不支持的文件类型：{ext}。支持的类型：{', '.join(self.settings.allowed_extensions)}"
        
        # 检查文件大小
        if file_size > self.settings.max_file_size:
            max_mb = self.settings.max_file_size / (1024 * 1024)
            return False, f"文件太大：{file_size / (1024 * 1024):.1f}MB。最大允许：{max_mb:.1f}MB"
        
        return True, "验证通过"
    
    def get_content_type(self, filename: str) -> str:
        """获取文件内容类型"""
        ext = Path(filename).suffix.lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp'
        }
        return content_types.get(ext, 'application/octet-stream')
    
    def get_image_dimensions(self, file_content: bytes) -> Tuple[int, int]:
        """获取图片尺寸"""
        try:
            from io import BytesIO
            with Image.open(BytesIO(file_content)) as img:
                return img.width, img.height
        except Exception as e:
            print(f"❌ 获取图片尺寸失败: {e}")
            return 0, 0


# 创建全局存储管理器实例
storage_manager = StorageManager()