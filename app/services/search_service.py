"""
搜索服务 - 自然语言处理和图片检索
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.image import Image, Tag, ImageTag, TagCategory
from app.services.database_service import DatabaseService


class SearchService:
    """搜索服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.db_service = DatabaseService(db)
        
        # 关键词映射字典
        self.keyword_mappings = {
            # 姿势相关
            "站着": ["站姿", "站立"],
            "坐着": ["坐姿"],
            "躺着": ["躺姿"],
            "蹲着": ["蹲姿"],
            
            # 性别相关
            "女人": ["女性"],
            "男人": ["男性"],
            "女孩": ["女性"],
            "男孩": ["男性"],
            "女的": ["女性"],
            "男的": ["男性"],
            
            # 年龄相关
            "小孩": ["儿童"],
            "孩子": ["儿童"],
            "年轻": ["青年"],
            "老人": ["老年"],
            
            # 服装相关
            "西装": ["正装"],
            "便装": ["休闲装"],
            "裙子": ["裙子"],
            "牛仔": ["牛仔裤"],
            
            # 场景相关
            "室内": ["室内"],
            "户外": ["户外"],
            "外面": ["户外"],
            "里面": ["室内"],
            "办公": ["办公室"],
            "家里": ["家居"],
            "公园": ["公园"],
            
            # 角度相关
            "正面": ["正面"],
            "侧面": ["侧面"],
            "背面": ["背面"],
            "从上": ["俯视"],
            "从下": ["仰视"],
            "俯拍": ["俯视"],
            "仰拍": ["仰视"],
            
            # 表情相关
            "笑": ["微笑"],
            "严肃": ["严肃"],
            "想": ["思考表情"],
            "放松": ["放松"],
            
            # 动作相关
            "走": ["行走"],
            "看书": ["阅读"],
            "读书": ["阅读"],
            "伸懒腰": ["伸展"],
            
            # 道具相关
            "椅子": ["椅子"],
            "桌子": ["桌子"],
            "书": ["书本"],
            "咖啡": ["咖啡杯"],
            "没有道具": ["无道具"],
            "无道具": ["无道具"],
            
            # 光线相关
            "自然光": ["自然光"],
            "阳光": ["自然光"],
            "人造光": ["人工光"],
            "灯光": ["人工光"],
            "逆光": ["逆光"],
            "柔光": ["柔和光"],
            "强光": ["强光"],
        }
        
        # 否定词
        self.negative_words = ["不", "没有", "不是", "非", "除了", "不要"]
        
    def parse_natural_language(self, query: str) -> Dict[str, Any]:
        """解析自然语言查询"""
        query = query.strip().lower()
        
        # 提取的标签和否定标签
        positive_tags = []
        negative_tags = []
        
        # 当前是否在否定上下文中
        is_negative = False
        
        # 分词并处理
        words = self._simple_tokenize(query)
        
        for i, word in enumerate(words):
            # 检查否定词
            if word in self.negative_words:
                is_negative = True
                continue
            
            # 检查是否匹配关键词
            matched_tags = self._match_keywords(word)
            if matched_tags:
                if is_negative:
                    negative_tags.extend(matched_tags)
                    is_negative = False  # 重置否定状态
                else:
                    positive_tags.extend(matched_tags)
        
        # 去重
        positive_tags = list(set(positive_tags))
        negative_tags = list(set(negative_tags))
        
        # 分析查询意图
        intent = self._analyze_intent(query)
        
        return {
            "original_query": query,
            "positive_tags": positive_tags,
            "negative_tags": negative_tags,
            "intent": intent,
            "parsed_successfully": len(positive_tags) > 0
        }
    
    def _simple_tokenize(self, text: str) -> List[str]:
        """简单分词"""
        # 使用正则表达式分词
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text)
        return words
    
    def _match_keywords(self, word: str) -> List[str]:
        """匹配关键词到标签"""
        matched_tags = []
        
        # 直接匹配
        if word in self.keyword_mappings:
            matched_tags.extend(self.keyword_mappings[word])
        
        # 模糊匹配
        for keyword, tags in self.keyword_mappings.items():
            if word in keyword or keyword in word:
                matched_tags.extend(tags)
        
        return matched_tags
    
    def _analyze_intent(self, query: str) -> str:
        """分析查询意图"""
        if any(word in query for word in ["坐", "站", "躺", "蹲"]):
            return "pose_search"
        elif any(word in query for word in ["男", "女"]):
            return "gender_search"
        elif any(word in query for word in ["室内", "户外", "办公"]):
            return "scene_search"
        else:
            return "general_search"
    
    def search_images(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """根据自然语言查询搜索图片"""
        
        # 解析查询
        parsed = self.parse_natural_language(query)
        
        if not parsed["parsed_successfully"]:
            # 如果解析失败，尝试基于描述的模糊搜索
            return self._fallback_search(query, limit)
        
        # 构建数据库查询
        images = self._build_database_query(parsed, limit)
        
        # 构建结果
        result = {
            "query": query,
            "parsed": parsed,
            "total": len(images),
            "images": []
        }
        
        # 处理图片结果
        for image in images:
            image_tags = self.db_service.get_image_tags(image.id)
            
            result["images"].append({
                "id": image.id,
                "filename": image.filename,
                "url": f"/uploads/{image.file_path.split('/')[-1]}",
                "width": image.width,
                "height": image.height,
                "description": image.ai_description,
                "confidence": image.ai_confidence,
                "upload_time": image.upload_time.isoformat(),
                "view_count": image.view_count,
                "tags": [{"name": tag.name, "category": tag.category} for tag in image_tags],
                "uploader": image.uploader
            })
        
        return result
    
    def _build_database_query(self, parsed: Dict[str, Any], limit: int):
        """构建数据库查询"""
        base_query = self.db.query(Image).filter(Image.is_active == True)
        
        positive_tags = parsed["positive_tags"]
        negative_tags = parsed["negative_tags"]
        
        if positive_tags:
            # 包含指定标签的图片
            positive_subquery = self.db.query(ImageTag.image_id).join(Tag).filter(
                Tag.name.in_(positive_tags)
            ).subquery()
            
            base_query = base_query.filter(Image.id.in_(positive_subquery))
        
        if negative_tags:
            # 排除指定标签的图片
            negative_subquery = self.db.query(ImageTag.image_id).join(Tag).filter(
                Tag.name.in_(negative_tags)
            ).subquery()
            
            base_query = base_query.filter(~Image.id.in_(negative_subquery))
        
        # 按相关性排序（这里简化为按查看次数和上传时间）
        base_query = base_query.order_by(
            Image.view_count.desc(),
            Image.upload_time.desc()
        )
        
        return base_query.limit(limit).all()
    
    def _fallback_search(self, query: str, limit: int) -> Dict[str, Any]:
        """备用搜索 - 基于描述的模糊搜索"""
        
        # 在AI描述中搜索关键词
        images = self.db.query(Image).filter(
            and_(
                Image.is_active == True,
                Image.ai_description.contains(query)
            )
        ).order_by(Image.upload_time.desc()).limit(limit).all()
        
        result = {
            "query": query,
            "parsed": {"fallback": True},
            "total": len(images),
            "images": []
        }
        
        for image in images:
            image_tags = self.db_service.get_image_tags(image.id)
            
            result["images"].append({
                "id": image.id,
                "filename": image.filename,
                "url": f"/uploads/{image.file_path.split('/')[-1]}",
                "width": image.width,
                "height": image.height,
                "description": image.ai_description,
                "confidence": image.ai_confidence,
                "upload_time": image.upload_time.isoformat(),
                "view_count": image.view_count,
                "tags": [{"name": tag.name, "category": tag.category} for tag in image_tags],
                "uploader": image.uploader
            })
        
        return result
    
    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """获取搜索建议"""
        suggestions = []
        
        # 基于关键词映射的建议
        for keyword in self.keyword_mappings.keys():
            if partial_query in keyword:
                suggestions.append(keyword)
        
        # 基于热门标签的建议
        popular_tags = self.db_service.get_popular_tags(limit=10)
        for tag in popular_tags:
            if partial_query in tag.name:
                suggestions.append(tag.name)
        
        return suggestions[:5]  # 返回前5个建议
    
    def get_popular_searches(self) -> List[str]:
        """获取热门搜索词"""
        return [
            "女性坐姿",
            "男性站立",
            "室内正面",
            "户外侧面",
            "思考表情",
            "阅读动作",
            "办公室场景",
            "自然光照"
        ]