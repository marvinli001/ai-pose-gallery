"""
应用配置 - 添加OSS云存储支持
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


class Settings(BaseSettings):
    """应用设置"""
    
    # MySQL 配置
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "password"
    mysql_database: str = "ai_pose_gallery"
    
    # OpenAI GPT-4o 配置
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.1
    
    # 图片存储配置
    storage_type: str = "local"  # local, oss, s3
    upload_dir: str = "./uploads"
    max_file_size: int = 10 * 1024 * 1024
    allowed_extensions: set = {".jpg", ".jpeg", ".png", ".webp"}
    image_analysis_timeout: int = 60
    
    # 阿里云OSS配置
    oss_enabled: bool = False
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_bucket_name: str = ""
    oss_endpoint: str = ""
    oss_region: str = "oss-cn-hangzhou"
    oss_custom_domain: str = ""  # 自定义域名
    oss_folder_prefix: str = "ai-pose-gallery/"  # 文件夹前缀
    
    # AWS S3配置 (预留)
    s3_enabled: bool = False
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket_name: str = ""
    s3_region: str = "us-east-1"
    s3_custom_domain: str = ""
    
    # 小红书API配置 (预留)
    xiaohongshu_enabled: bool = False
    xiaohongshu_api_key: str = ""
    
    # 搜索配置
    search_results_per_page: int = 20
    search_max_results: int = 100
    enable_semantic_search: bool = True
    
    # 缓存配置
    enable_redis_cache: bool = False
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600
    
    # 管理员配置
    admin_password: str = "admin123"
    
    # 应用配置
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **kwargs):
        load_dotenv(override=True)
        super().__init__(**kwargs)
    
    @property
    def database_url(self) -> str:
        """构建MySQL连接URL"""
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
    
    @property
    def use_oss_storage(self) -> bool:
        """是否使用OSS存储"""
        return self.storage_type == "oss" and self.oss_enabled
    
    @property
    def use_s3_storage(self) -> bool:
        """是否使用S3存储"""
        return self.storage_type == "s3" and self.s3_enabled


@lru_cache()
def get_settings():
    """获取设置单例"""
    return Settings()


def create_directories():
    """创建必要的目录"""
    settings = get_settings()
    
    # 始终创建本地上传目录（作为临时存储）
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs("./cache", exist_ok=True)
    
    print(f"✅ 创建目录: {settings.upload_dir}")
    
    if settings.use_oss_storage:
        print("🗂️  已启用阿里云OSS存储")
    elif settings.use_s3_storage:
        print("🗂️  已启用AWS S3存储")
    else:
        print("🗂️  使用本地文件存储")