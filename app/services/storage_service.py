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
from fastapi import UploadFile
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

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
        self.settings = get_settings()  # 添加这行
        self.storage_type = os.getenv('STORAGE_TYPE', 'local')
        if self.storage_type == 'oss':
            self.oss_enabled = os.getenv('OSS_ENABLED', 'false').lower() == 'true'
            self.oss_bucket = os.getenv('OSS_BUCKET_NAME', '')
            self.oss_bucket_name = self.oss_bucket  # 添加别名
            self.oss_endpoint = os.getenv('OSS_ENDPOINT', '')
            self.oss_region = os.getenv('OSS_REGION', '')
            self.oss_custom_domain = os.getenv('OSS_CUSTOM_DOMAIN', '')
            self.oss_folder_prefix = os.getenv('OSS_FOLDER_PREFIX', '').rstrip('/')
            
            # OSS认证信息
            self.oss_access_key_id = os.getenv('OSS_ACCESS_KEY_ID', '')
            self.oss_access_key_secret = os.getenv('OSS_ACCESS_KEY_SECRET', '')
            
            # 修复自定义域名协议
            if self.oss_custom_domain:
                if not self.oss_custom_domain.startswith(('http://', 'https://')):
                    self.oss_custom_domain = f"https://{self.oss_custom_domain}"
                self.oss_custom_domain = self.oss_custom_domain.rstrip('/')
            
            # 初始化OSS客户端
            self._init_oss_client()
        else:
            self.oss_enabled = False
            self.oss_bucket = None

    def _init_oss_client(self):
        """初始化OSS客户端"""
        if self.oss_enabled and all([
            self.oss_access_key_id, 
            self.oss_access_key_secret, 
            self.oss_bucket_name, 
            self.oss_endpoint
        ]):
            try:
                import oss2
                auth = oss2.Auth(self.oss_access_key_id, self.oss_access_key_secret)
                self.oss_bucket_client = oss2.Bucket(auth, self.oss_endpoint, self.oss_bucket_name)
                print(f"✅ OSS客户端初始化成功: {self.oss_bucket_name}")
            except Exception as e:
                print(f"❌ OSS客户端初始化失败: {e}")
                self.oss_bucket_client = None
        else:
            self.oss_bucket_client = None
            print("⚠️ OSS未配置或配置不完整")

    def list_oss_objects(self, prefix: str = "") -> List[Dict]:
        """获取OSS对象列表"""
        if not self.oss_bucket_client:
            print("❌ OSS客户端未初始化")
            return []
        
        objects = []
        try:
            print(f"🔍 获取OSS对象列表，前缀: {prefix}")
            
            # 使用oss2的ObjectIterator
            import oss2
            for obj in oss2.ObjectIterator(self.oss_bucket_client, prefix=prefix):
                # 只处理图片文件
                if self._is_image_file(obj.key):
                    objects.append({
                        'key': obj.key,
                        'size': obj.size,
                        'last_modified': obj.last_modified,
                        'etag': obj.etag
                    })
            
            print(f"✅ 找到 {len(objects)} 个图片文件")
            return objects
            
        except Exception as e:
            print(f"❌ 获取OSS对象列表失败: {e}")
            return []
        
    def _is_image_file(self, filename: str) -> bool:
        """检查是否为图片文件"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        return any(filename.lower().endswith(ext) for ext in image_extensions)

    def check_oss_connection(self) -> bool:
        """检查OSS连接"""
        if not self.oss_bucket_client:
            return False
        
        try:
            # 尝试列出存储桶信息
            self.oss_bucket_client.get_bucket_info()
            return True
        except Exception as e:
            print(f"❌ OSS连接检查失败: {e}")
            return False
        
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
        """删除图片文件"""
        try:
            # 删除原始文件
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # 删除static目录中的文件
            if file_path.startswith('uploads/'):
                static_path = f"static/{file_path}"
            else:
                static_path = f"static/uploads/{os.path.basename(file_path)}"
            
            if os.path.exists(static_path):
                os.remove(static_path)
            
            logger.info(f"文件删除成功: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return False
        
    def get_file_info(self, file_path: str) -> dict:
        """获取文件信息"""
        try:
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                return {
                    'exists': True,
                    'size': stat.st_size,
                    'modified': stat.st_mtime
                }
            else:
                return {'exists': False}
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return {'exists': False, 'error': str(e)}

    
    def get_image_url(self, file_path: str) -> str:
        """获取图片访问URL"""
        if not file_path:
            return "/static/images/placeholder.jpg"
        
        # 如果已经是完整URL，直接返回
        if file_path.startswith('http'):
            return file_path
            
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
        
    def get_oss_url(self, key: str) -> str:
        """获取OSS文件的访问URL"""
        if not key:
            return "/static/images/placeholder.jpg"
        
        # 移除开头的斜杠
        clean_key = key.lstrip('/')
        
        if self.oss_custom_domain:
            # 使用自定义域名
            return f"{self.oss_custom_domain}/{clean_key}"
        else:
            # 使用默认OSS域名
            endpoint_clean = self.oss_endpoint.replace('https://', '').replace('http://', '')
            return f"https://{self.oss_bucket_name}.{endpoint_clean}/{clean_key}"

        
    async def save_upload_file(self, file: UploadFile, subfolder: str = "") -> tuple[str, str]:
        """保存上传的文件"""
        try:
            # 验证文件扩展名
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in self.settings['allowed_extensions']:
                raise ValueError(f"不支持的文件类型: {file_ext}")
            
            # 生成唯一文件名
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            
            # 确定保存路径
            if subfolder:
                save_dir = self.upload_dir / subfolder
                save_dir.mkdir(parents=True, exist_ok=True)
                file_path = save_dir / unique_filename
                relative_path = f"{subfolder}/{unique_filename}"
            else:
                file_path = self.upload_dir / unique_filename
                relative_path = unique_filename
            
            # 保存文件
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                
                # 检查文件大小
                if len(content) > self.settings['max_file_size']:
                    raise ValueError(f"文件太大，最大允许 {self.settings['max_file_size']//1024//1024}MB")
                
                await f.write(content)
            
            # 复制到static目录以便web访问
            static_path = Path('static/uploads') / relative_path
            static_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(static_path, 'wb') as f:
                await f.write(content)
            
            logger.info(f"文件保存成功: {file_path}")
            return str(file_path), relative_path
            
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            raise
    
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