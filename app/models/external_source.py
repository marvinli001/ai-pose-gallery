"""
外部数据源模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON
from sqlalchemy.sql import func
from app.database import Base


class ExternalContent(Base):
    """外部内容表"""
    __tablename__ = "external_contents"
    
    id = Column(Integer, primary_key=True, index=True, comment="内容ID")
    external_id = Column(String(100), nullable=False, index=True, comment="外部平台ID")
    source_platform = Column(String(50), nullable=False, index=True, comment="来源平台")
    source_url = Column(String(500), comment="原始链接")
    
    # 内容信息
    title = Column(String(500), comment="标题")
    description = Column(Text, comment="描述")
    author = Column(String(200), comment="作者")
    category = Column(String(100), comment="分类")
    
    # 媒体信息
    image_urls = Column(JSON, comment="图片URL列表")
    video_urls = Column(JSON, comment="视频URL列表")
    
    # 互动数据
    like_count = Column(Integer, default=0, comment="点赞数")
    comment_count = Column(Integer, default=0, comment="评论数")
    share_count = Column(Integer, default=0, comment="分享数")
    view_count = Column(Integer, default=0, comment="查看数")
    
    # AI分析结果
    ai_relevance_score = Column(Float, comment="AI相关性评分")
    ai_quality_score = Column(Float, comment="AI质量评分")
    ai_analysis_result = Column(JSON, comment="AI分析结果")
    ai_suggested_tags = Column(JSON, comment="AI建议的标签")
    ai_analysis_reason = Column(Text, comment="AI分析原因")
    
    # 导入信息
    import_keyword = Column(String(200), comment="导入关键词")
    import_time = Column(DateTime(timezone=True), server_default=func.now(), comment="导入时间")
    last_sync_time = Column(DateTime(timezone=True), comment="最后同步时间")
    
    # 状态信息
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_processed = Column(Boolean, default=False, comment="是否已处理")
    process_status = Column(String(50), default="pending", comment="处理状态")
    
    # 原始数据
    raw_data = Column(JSON, comment="原始数据JSON")
    
    def __repr__(self):
        return f"<ExternalContent(id={self.id}, platform='{self.source_platform}', title='{self.title}')>"


class ExternalImage(Base):
    """外部图片表"""
    __tablename__ = "external_images"
    
    id = Column(Integer, primary_key=True, index=True, comment="图片ID")
    content_id = Column(Integer, comment="关联内容ID")
    external_id = Column(String(100), comment="外部图片ID")
    
    # 图片信息
    original_url = Column(String(1000), nullable=False, comment="原始URL")
    local_path = Column(String(500), comment="本地存储路径")
    cloud_path = Column(String(500), comment="云存储路径")
    
    file_size = Column(Integer, comment="文件大小")
    width = Column(Integer, comment="图片宽度")
    height = Column(Integer, comment="图片高度")
    format = Column(String(20), comment="图片格式")
    
    # AI分析结果
    ai_description = Column(Text, comment="AI生成的描述")
    ai_tags = Column(JSON, comment="AI生成的标签")
    ai_confidence = Column(Float, comment="AI分析置信度")
    ai_analysis_raw = Column(JSON, comment="完整AI分析结果")
    
    # 状态信息
    download_status = Column(String(50), default="pending", comment="下载状态")
    analysis_status = Column(String(50), default="pending", comment="分析状态")
    is_active = Column(Boolean, default=True, comment="是否激活")
    
    # 时间信息
    created_time = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    downloaded_time = Column(DateTime(timezone=True), comment="下载时间")
    analyzed_time = Column(DateTime(timezone=True), comment="分析时间")
    
    def __repr__(self):
        return f"<ExternalImage(id={self.id}, url='{self.original_url}')>"