"""
数据库服务工具类
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.image import Image, Tag, ImageTag


class DatabaseService:
    """数据库服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # 图片相关操作
    def create_image(self, **kwargs) -> Image:
        """创建图片记录"""
        image = Image(**kwargs)
        self.db.add(image)
        self.db.commit()
        self.db.refresh(image)
        return image
    
    def get_image_by_id(self, image_id: int) -> Optional[Image]:
        """根据ID获取图片"""
        return self.db.query(Image).filter(Image.id == image_id).first()
    
    def get_images_by_tags(self, tag_names: List[str], limit: int = 20) -> List[Image]:
        """根据标签名称搜索图片"""
        if not tag_names:
            return self.db.query(Image).filter(Image.is_active == True).limit(limit).all()
        
        # 构建查询 - 找到包含任一标签的图片
        query = self.db.query(Image).join(ImageTag).join(Tag).filter(
            and_(
                Image.is_active == True,
                Tag.name.in_(tag_names)
            )
        ).distinct().limit(limit)
        
        return query.all()
    
    def update_image_view_count(self, image_id: int):
        """更新图片查看次数"""
        image = self.get_image_by_id(image_id)
        if image:
            image.view_count += 1
            self.db.commit()
    
    # 标签相关操作
    def get_or_create_tag(self, name: str, category: str, description: str = "") -> Tag:
        """获取或创建标签"""
        tag = self.db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(name=name, category=category, description=description)
            self.db.add(tag)
            self.db.commit()
            self.db.refresh(tag)
        return tag
    
    def get_tags_by_category(self, category: str) -> List[Tag]:
        """根据分类获取标签"""
        return self.db.query(Tag).filter(
            and_(Tag.category == category, Tag.is_active == True)
        ).order_by(Tag.usage_count.desc()).all()
    
    def get_popular_tags(self, limit: int = 20) -> List[Tag]:
        """获取热门标签"""
        return self.db.query(Tag).filter(Tag.is_active == True).order_by(
            Tag.usage_count.desc()
        ).limit(limit).all()
    
    def search_tags(self, keyword: str, limit: int = 10) -> List[Tag]:
        """搜索标签"""
        return self.db.query(Tag).filter(
            and_(
                Tag.is_active == True,
                or_(
                    Tag.name.contains(keyword),
                    Tag.description.contains(keyword)
                )
            )
        ).limit(limit).all()
    
    # 图片标签关联操作
    def add_tags_to_image(self, image_id: int, tag_names: List[str], source: str = "ai", confidences: List[float] = None):
        """为图片添加标签"""
        if confidences is None:
            confidences = [1.0] * len(tag_names)
        
        # 确保长度一致
        if len(confidences) != len(tag_names):
            confidences = [1.0] * len(tag_names)
        
        for i, tag_name in enumerate(tag_names):
            # 获取或创建标签（这里需要指定分类，实际使用时需要AI分析）
            tag = self.get_or_create_tag(tag_name, "auto", f"AI生成的标签: {tag_name}")
            
            # 检查是否已存在关联
            existing = self.db.query(ImageTag).filter(
                and_(ImageTag.image_id == image_id, ImageTag.tag_id == tag.id)
            ).first()
            
            if not existing:
                image_tag = ImageTag(
                    image_id=image_id,
                    tag_id=tag.id,
                    confidence=confidences[i],
                    source=source
                )
                self.db.add(image_tag)
                
                # 更新标签使用次数
                tag.usage_count += 1
        
        self.db.commit()
    
    def get_image_tags(self, image_id: int) -> List[Tag]:
        """获取图片的标签"""
        return self.db.query(Tag).join(ImageTag).filter(
            ImageTag.image_id == image_id
        ).all()
    
    def remove_tag_from_image(self, image_id: int, tag_id: int):
        """从图片移除标签"""
        image_tag = self.db.query(ImageTag).filter(
            and_(ImageTag.image_id == image_id, ImageTag.tag_id == tag_id)
        ).first()
        
        if image_tag:
            self.db.delete(image_tag)
            
            # 更新标签使用次数
            tag = self.db.query(Tag).filter(Tag.id == tag_id).first()
            if tag and tag.usage_count > 0:
                tag.usage_count -= 1
            
            self.db.commit()