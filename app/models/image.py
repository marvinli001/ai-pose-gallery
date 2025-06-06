"""
图片相关数据模型 - 修复重复标签
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Image(Base):
    """图片表"""
    __tablename__ = "images"
    
    id = Column(Integer, primary_key=True, index=True, comment="图片ID")
    filename = Column(String(255), nullable=False, comment="原始文件名")
    file_path = Column(String(500), nullable=False, unique=True, comment="文件存储路径")
    file_size = Column(Integer, nullable=False, comment="文件大小(字节)")
    width = Column(Integer, comment="图片宽度")
    height = Column(Integer, comment="图片高度")
    
    # AI分析结果
    ai_description = Column(Text, comment="AI生成的图片描述")
    ai_analysis_status = Column(String(50), default="pending", comment="AI分析状态: pending, completed, failed")
    ai_confidence = Column(Float, comment="AI分析置信度")
    ai_model = Column(String(50), default="gpt-4o", comment="使用的AI模型")
    ai_analysis_raw = Column(JSON, comment="完整的AI分析结果JSON")
    ai_searchable_keywords = Column(JSON, comment="AI提取的搜索关键词")
    ai_mood = Column(String(200), comment="AI分析的整体氛围")
    ai_style = Column(String(200), comment="AI分析的视觉风格")
    
    # 用户信息
    uploader = Column(String(100), comment="上传者")
    upload_time = Column(DateTime(timezone=True), server_default=func.now(), comment="上传时间")
    
    # 状态字段
    is_active = Column(Boolean, default=True, comment="是否激活")
    view_count = Column(Integer, default=0, comment="查看次数")
    
    # 关联关系
    image_tags = relationship("ImageTag", back_populates="image", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Image(id={self.id}, filename='{self.filename}')>"


class Tag(Base):
    """标签表"""
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True, comment="标签ID")
    name = Column(String(100), nullable=False, unique=True, index=True, comment="标签名称")
    category = Column(String(50), nullable=False, index=True, comment="标签分类")
    description = Column(Text, comment="标签描述")
    
    # 统计信息
    usage_count = Column(Integer, default=0, comment="使用次数")
    created_time = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 状态字段
    is_active = Column(Boolean, default=True, comment="是否激活")
    
    # 关联关系
    image_tags = relationship("ImageTag", back_populates="tag", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}', category='{self.category}')>"


class ImageTag(Base):
    """图片标签关联表"""
    __tablename__ = "image_tags"
    
    id = Column(Integer, primary_key=True, index=True, comment="关联ID")
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False, comment="图片ID")
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False, comment="标签ID")
    
    # AI相关字段
    confidence = Column(Float, comment="标签置信度")
    source = Column(String(50), default="ai", comment="标签来源: ai, manual, gpt4o")
    
    # 时间字段
    created_time = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    # 关联关系
    image = relationship("Image", back_populates="image_tags")
    tag = relationship("Tag", back_populates="image_tags")
    
    def __repr__(self):
        return f"<ImageTag(image_id={self.image_id}, tag_id={self.tag_id})>"


# 标签分类常量
class TagCategory:
    """标签分类枚举"""
    POSE = "pose"           # 姿势类型
    GENDER = "gender"       # 性别
    AGE = "age"            # 年龄
    CLOTHING = "clothing"   # 服装
    PROPS = "props"        # 道具
    SCENE = "scene"        # 场景
    LIGHTING = "lighting"   # 光线
    ANGLE = "angle"        # 角度
    EMOTION = "emotion"    # 表情
    ACTION = "action"      # 动作
    STYLE = "style"        # 风格
    MOOD = "mood"          # 氛围
    COLOR = "color"        # 颜色
    COMPOSITION = "composition"  # 构图


# 预定义标签数据 - 修复重复问题
PREDEFINED_TAGS = [
    # 姿势类型
    {"name": "站姿", "category": TagCategory.POSE, "description": "站立姿势"},
    {"name": "坐姿", "category": TagCategory.POSE, "description": "坐着的姿势"},
    {"name": "躺姿", "category": TagCategory.POSE, "description": "躺着的姿势"},
    {"name": "蹲姿", "category": TagCategory.POSE, "description": "蹲着的姿势"},
    {"name": "跪姿", "category": TagCategory.POSE, "description": "跪着的姿势"},
    {"name": "侧卧", "category": TagCategory.POSE, "description": "侧卧姿势"},
    
    # 性别
    {"name": "女性", "category": TagCategory.GENDER, "description": "女性人物"},
    {"name": "男性", "category": TagCategory.GENDER, "description": "男性人物"},
    
    # 年龄
    {"name": "儿童", "category": TagCategory.AGE, "description": "儿童年龄段"},
    {"name": "青年", "category": TagCategory.AGE, "description": "青年年龄段"},
    {"name": "中年", "category": TagCategory.AGE, "description": "中年年龄段"},
    {"name": "老年", "category": TagCategory.AGE, "description": "老年年龄段"},
    
    # 服装
    {"name": "正装", "category": TagCategory.CLOTHING, "description": "正式服装"},
    {"name": "休闲装", "category": TagCategory.CLOTHING, "description": "休闲服装"},
    {"name": "裙子", "category": TagCategory.CLOTHING, "description": "裙装"},
    {"name": "牛仔裤", "category": TagCategory.CLOTHING, "description": "牛仔裤"},
    {"name": "T恤", "category": TagCategory.CLOTHING, "description": "T恤衫"},
    {"name": "衬衫", "category": TagCategory.CLOTHING, "description": "衬衫"},
    
    # 道具
    {"name": "椅子", "category": TagCategory.PROPS, "description": "椅子道具"},
    {"name": "桌子", "category": TagCategory.PROPS, "description": "桌子道具"},
    {"name": "书本", "category": TagCategory.PROPS, "description": "书本道具"},
    {"name": "咖啡杯", "category": TagCategory.PROPS, "description": "咖啡杯道具"},
    {"name": "手机", "category": TagCategory.PROPS, "description": "手机道具"},
    {"name": "笔记本电脑", "category": TagCategory.PROPS, "description": "笔记本电脑"},
    {"name": "无道具", "category": TagCategory.PROPS, "description": "没有道具"},
    
    # 场景
    {"name": "室内", "category": TagCategory.SCENE, "description": "室内环境"},
    {"name": "户外", "category": TagCategory.SCENE, "description": "户外环境"},
    {"name": "办公室", "category": TagCategory.SCENE, "description": "办公室环境"},
    {"name": "家居", "category": TagCategory.SCENE, "description": "家居环境"},
    {"name": "公园", "category": TagCategory.SCENE, "description": "公园环境"},
    {"name": "咖啡厅", "category": TagCategory.SCENE, "description": "咖啡厅环境"},
    {"name": "图书馆", "category": TagCategory.SCENE, "description": "图书馆环境"},
    
    # 光线
    {"name": "自然光", "category": TagCategory.LIGHTING, "description": "自然光照"},
    {"name": "人工光", "category": TagCategory.LIGHTING, "description": "人工光照"},
    {"name": "柔和光", "category": TagCategory.LIGHTING, "description": "柔和光线"},
    {"name": "强光", "category": TagCategory.LIGHTING, "description": "强烈光线"},
    {"name": "逆光", "category": TagCategory.LIGHTING, "description": "逆光效果"},
    {"name": "暖光", "category": TagCategory.LIGHTING, "description": "暖色调光线"},
    {"name": "冷光", "category": TagCategory.LIGHTING, "description": "冷色调光线"},
    
    # 角度
    {"name": "正面", "category": TagCategory.ANGLE, "description": "正面角度"},
    {"name": "侧面", "category": TagCategory.ANGLE, "description": "侧面角度"},
    {"name": "背面", "category": TagCategory.ANGLE, "description": "背面角度"},
    {"name": "俯视", "category": TagCategory.ANGLE, "description": "俯视角度"},
    {"name": "仰视", "category": TagCategory.ANGLE, "description": "仰视角度"},
    {"name": "平视", "category": TagCategory.ANGLE, "description": "平视角度"},
    
    # 表情
    {"name": "微笑", "category": TagCategory.EMOTION, "description": "微笑表情"},
    {"name": "严肃", "category": TagCategory.EMOTION, "description": "严肃表情"},
    {"name": "思考表情", "category": TagCategory.EMOTION, "description": "思考的表情"},
    {"name": "放松", "category": TagCategory.EMOTION, "description": "放松状态"},
    {"name": "专注", "category": TagCategory.EMOTION, "description": "专注表情"},
    {"name": "自信", "category": TagCategory.EMOTION, "description": "自信表情"},
    
    # 动作
    {"name": "站立", "category": TagCategory.ACTION, "description": "站立动作"},
    {"name": "行走", "category": TagCategory.ACTION, "description": "行走动作"},
    {"name": "阅读", "category": TagCategory.ACTION, "description": "阅读动作"},
    {"name": "思考动作", "category": TagCategory.ACTION, "description": "思考动作"},
    {"name": "伸展", "category": TagCategory.ACTION, "description": "伸展动作"},
    {"name": "交谈", "category": TagCategory.ACTION, "description": "交谈动作"},
    {"name": "工作状态", "category": TagCategory.ACTION, "description": "工作状态"},  # 改名避免重复
    
    # 风格
    {"name": "现代风格", "category": TagCategory.STYLE, "description": "现代风格"},  # 改名避免重复
    {"name": "简约风格", "category": TagCategory.STYLE, "description": "简约风格"},  # 改名避免重复
    {"name": "优雅风格", "category": TagCategory.STYLE, "description": "优雅风格"},  # 改名避免重复
    {"name": "活力风格", "category": TagCategory.STYLE, "description": "活力风格"},  # 改名避免重复
    {"name": "商务风格", "category": TagCategory.STYLE, "description": "商务风格"},  # 改名避免重复
    
    # 氛围
    {"name": "温馨氛围", "category": TagCategory.MOOD, "description": "温馨氛围"},  # 改名避免重复
    {"name": "宁静氛围", "category": TagCategory.MOOD, "description": "宁静氛围"},  # 改名避免重复
    {"name": "活跃氛围", "category": TagCategory.MOOD, "description": "活跃氛围"},  # 改名避免重复
    {"name": "商务氛围", "category": TagCategory.MOOD, "description": "商务氛围"},  # 改名避免重复
    {"name": "轻松氛围", "category": TagCategory.MOOD, "description": "轻松氛围"},  # 改名避免重复
]