"""
数据库服务工具类 - 修复版本
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_
from app.models.image import Image, Tag, ImageTag
import traceback


class DatabaseService:
    """数据库服务类 - 修复版本"""
    
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
    
    def get_image_by_id(self, image_id: int, include_deleted: bool = False) -> Optional[Image]:
        """根据ID获取图片"""
        try:
            query = self.db.query(Image).filter(Image.id == image_id)
            if not include_deleted:
                query = query.filter(Image.is_active == True)
            return query.first()
        except SQLAlchemyError as e:
            print(f"❌ 获取图片失败 ID {image_id}: {e}")
            return None
    
    def get_images_by_tags(self, tag_names: List[str], limit: int = 20) -> List[Image]:
        """根据标签名称搜索图片"""
        try:
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
        except SQLAlchemyError as e:
            print(f"❌ 按标签搜索图片失败: {e}")
            return []
    
    def update_image_view_count(self, image_id: int):
        """更新图片查看次数"""
        try:
            image = self.get_image_by_id(image_id)
            if image:
                image.view_count += 1
                self.db.commit()
        except SQLAlchemyError as e:
            print(f"❌ 更新查看次数失败 ID {image_id}: {e}")
            self.db.rollback()
    
    # 标签相关操作
    def get_or_create_tag(self, name: str, category: str, description: str = "") -> Tag:
        """获取或创建标签"""
        try:
            tag = self.db.query(Tag).filter(Tag.name == name).first()
            if not tag:
                tag = Tag(name=name, category=category, description=description)
                self.db.add(tag)
                self.db.commit()
                self.db.refresh(tag)
            return tag
        except SQLAlchemyError as e:
            print(f"❌ 获取或创建标签失败 {name}: {e}")
            self.db.rollback()
            raise
    
    def get_tags_by_category(self, category: str) -> List[Tag]:
        """根据分类获取标签"""
        try:
            return self.db.query(Tag).filter(
                and_(Tag.category == category, Tag.is_active == True)
            ).order_by(Tag.usage_count.desc()).all()
        except SQLAlchemyError as e:
            print(f"❌ 按分类获取标签失败 {category}: {e}")
            return []
    
    def get_popular_tags(self, limit: int = 20) -> List[Tag]:
        """获取热门标签"""
        try:
            return self.db.query(Tag).filter(Tag.is_active == True).order_by(
                Tag.usage_count.desc()
            ).limit(limit).all()
        except SQLAlchemyError as e:
            print(f"❌ 获取热门标签失败: {e}")
            return []
    
    def search_tags(self, keyword: str, limit: int = 10) -> List[Tag]:
        """搜索标签"""
        try:
            return self.db.query(Tag).filter(
                and_(
                    Tag.is_active == True,
                    or_(
                        Tag.name.contains(keyword),
                        Tag.description.contains(keyword)
                    )
                )
            ).limit(limit).all()
        except SQLAlchemyError as e:
            print(f"❌ 搜索标签失败 {keyword}: {e}")
            return []
    
    # 图片标签关联操作
    def add_tags_to_image(self, image_id: int, tag_names: List[str], source: str = "ai", confidences: List[float] = None):
        """为图片添加标签 - 原版本"""
        try:
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
        except SQLAlchemyError as e:
            print(f"❌ 添加标签到图片失败 ID {image_id}: {e}")
            self.db.rollback()
            raise
    
    def add_tags_to_image_safe(self, image_id: int, tag_names: List[str], source: str = "ai", confidences: List[float] = None):
        """为图片添加标签 - 改进版本，更安全"""
        if confidences is None:
            confidences = [1.0] * len(tag_names)
        
        # 确保长度一致
        if len(confidences) != len(tag_names):
            confidences = [1.0] * len(tag_names)
        
        for i, tag_name in enumerate(tag_names):
            try:
                # 获取或创建标签
                tag = self.get_or_create_tag(tag_name, "auto", f"AI生成的标签: {tag_name}")
                
                # 使用更严格的重复检查
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
                    
                    print(f"✅ 添加标签: {tag_name}")
                else:
                    print(f"⚠️ 标签已存在，跳过: {tag_name}")
                    
            except SQLAlchemyError as tag_error:
                print(f"❌ 添加单个标签失败 {tag_name}: {tag_error}")
                # 继续处理其他标签，不中断整个过程
                continue
        
        # 在调用方处理 commit，这里不自动提交
    
    def get_image_tags(self, image_id: int) -> List[Tag]:
        """获取图片的标签 - 增强错误处理"""
        try:
            print(f"🔍 正在获取图片 {image_id} 的标签...")
            
            # 首先检查图片是否存在
            image_exists = self.db.query(Image).filter(Image.id == image_id).first()
            if not image_exists:
                print(f"⚠️ 图片 {image_id} 不存在")
                return []
            
            # 使用子查询避免潜在的JOIN问题
            tag_ids = self.db.query(ImageTag.tag_id).filter(
                ImageTag.image_id == image_id
            ).subquery()
            
            tags = self.db.query(Tag).filter(
                Tag.id.in_(tag_ids)
            ).all()
            
            print(f"✅ 成功获取图片 {image_id} 的 {len(tags)} 个标签")
            return tags
            
        except SQLAlchemyError as e:
            print(f"❌ 获取图片标签失败 ID {image_id}: {e}")
            print(f"详细错误: {traceback.format_exc()}")
            # 不回滚，因为这只是查询操作
            return []
        except Exception as e:
            print(f"❌ 获取图片标签出现未知错误 ID {image_id}: {e}")
            print(f"详细错误: {traceback.format_exc()}")
            return []
    
    def remove_tag_from_image(self, image_id: int, tag_id: int):
        """从图片移除标签"""
        try:
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
        except SQLAlchemyError as e:
            print(f"❌ 移除图片标签失败 Image ID {image_id}, Tag ID {tag_id}: {e}")
            self.db.rollback()