"""
智能搜索服务 - 添加相似图片推荐功能
"""
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text

from app.models.image import Image, Tag, ImageTag
from app.services.database_service import DatabaseService
from app.services.gpt4o_service import gpt4o_analyzer


class SmartSearchService:
    """智能搜索服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.db_service = DatabaseService(db)
    
    async def find_similar_images(self, image_id: int, similarity_type: str = "tags", limit: int = 6) -> Dict[str, Any]:
        """查找相似图片"""
        try:
            # 获取目标图片
            target_image = self.db_service.get_image_by_id(image_id)
            if not target_image:
                return {"success": False, "error": "图片不存在"}
            
            # 根据相似度类型查找
            if similarity_type == "tags":
                similar_images = await self._find_similar_by_tags(target_image, limit)
            elif similarity_type == "style":
                similar_images = await self._find_similar_by_style(target_image, limit)
            elif similarity_type == "mood":
                similar_images = await self._find_similar_by_mood(target_image, limit)
            elif similarity_type == "ai":
                similar_images = await self._find_similar_by_ai(target_image, limit)
            else:
                similar_images = await self._find_similar_by_tags(target_image, limit)
            
            return {
                "success": True,
                "target_image_id": image_id,
                "similarity_type": similarity_type,
                "similar_images": similar_images,
                "total": len(similar_images)
            }
            
        except Exception as e:
            print(f"❌ 查找相似图片失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _find_similar_by_tags(self, target_image: Image, limit: int) -> List[Dict[str, Any]]:
        """基于标签查找相似图片"""
        # 获取目标图片的标签
        target_tags = self.db_service.get_image_tags(target_image.id)
        if not target_tags:
            return []
        
        target_tag_names = [tag.name for tag in target_tags]
        
        # 查找有相同标签的图片
        similar_images_query = self.db.query(Image).join(ImageTag).join(Tag).filter(
            and_(
                Image.is_active == True,
                Image.id != target_image.id,
                Tag.name.in_(target_tag_names)
            )
        ).group_by(Image.id).order_by(
            func.count(Tag.id).desc(),  # 按匹配标签数量排序
            Image.view_count.desc()
        ).limit(limit)
        
        similar_images = similar_images_query.all()
        return await self._format_similar_images(similar_images, target_tag_names)
    
    async def _find_similar_by_style(self, target_image: Image, limit: int) -> List[Dict[str, Any]]:
        """基于风格查找相似图片"""
        target_style = getattr(target_image, 'ai_style', None)
        if not target_style:
            return await self._find_similar_by_tags(target_image, limit)
        
        # 查找相同风格的图片
        similar_images = self.db.query(Image).filter(
            and_(
                Image.is_active == True,
                Image.id != target_image.id,
                Image.ai_style.contains(target_style)
            )
        ).order_by(
            Image.ai_confidence.desc(),
            Image.view_count.desc()
        ).limit(limit).all()
        
        return await self._format_similar_images(similar_images, [target_style])
    
    async def _find_similar_by_mood(self, target_image: Image, limit: int) -> List[Dict[str, Any]]:
        """基于氛围查找相似图片"""
        target_mood = getattr(target_image, 'ai_mood', None)
        if not target_mood:
            return await self._find_similar_by_tags(target_image, limit)
        
        # 查找相同氛围的图片
        similar_images = self.db.query(Image).filter(
            and_(
                Image.is_active == True,
                Image.id != target_image.id,
                Image.ai_mood.contains(target_mood)
            )
        ).order_by(
            Image.ai_confidence.desc(),
            Image.view_count.desc()
        ).limit(limit).all()
        
        return await self._format_similar_images(similar_images, [target_mood])
    
    async def _find_similar_by_ai(self, target_image: Image, limit: int) -> List[Dict[str, Any]]:
        """基于AI关键词查找相似图片"""
        target_keywords = []
        if hasattr(target_image, 'ai_searchable_keywords') and target_image.ai_searchable_keywords:
            try:
                if isinstance(target_image.ai_searchable_keywords, str):
                    target_keywords = json.loads(target_image.ai_searchable_keywords)
                else:
                    target_keywords = target_image.ai_searchable_keywords
            except:
                pass
        
        if not target_keywords:
            return await self._find_similar_by_tags(target_image, limit)
        
        # 构建搜索条件
        keyword_conditions = []
        for keyword in target_keywords[:3]:  # 只使用前3个关键词
            keyword_conditions.append(Image.ai_searchable_keywords.contains(f'"{keyword}"'))
        
        if not keyword_conditions:
            return await self._find_similar_by_tags(target_image, limit)
        
        # 查找相似图片
        similar_images = self.db.query(Image).filter(
            and_(
                Image.is_active == True,
                Image.id != target_image.id,
                or_(*keyword_conditions)
            )
        ).order_by(
            Image.ai_confidence.desc(),
            Image.view_count.desc()
        ).limit(limit).all()
        
        return await self._format_similar_images(similar_images, target_keywords)
    
    async def _format_similar_images(self, images: List[Image], reference_terms: List[str]) -> List[Dict[str, Any]]:
        """格式化相似图片结果"""
        result_images = []
        
        for image in images:
            # 获取标签
            tags = self.db_service.get_image_tags(image.id)
            
            # 解析搜索关键词
            searchable_keywords = []
            if hasattr(image, 'ai_searchable_keywords') and image.ai_searchable_keywords:
                try:
                    if isinstance(image.ai_searchable_keywords, str):
                        searchable_keywords = json.loads(image.ai_searchable_keywords)
                    else:
                        searchable_keywords = image.ai_searchable_keywords
                except:
                    pass
            
            # 计算相似度得分（简化计算）
            similarity_score = self._calculate_similarity_score(
                image, tags, searchable_keywords, reference_terms
            )
            
            result_images.append({
                "id": image.id,
                "filename": image.filename,
                "url": f"/uploads/{image.file_path.split('/')[-1]}",
                "width": image.width,
                "height": image.height,
                "description": image.ai_description or "",
                "confidence": image.ai_confidence or 0.0,
                "mood": getattr(image, 'ai_mood', ''),
                "style": getattr(image, 'ai_style', ''),
                "upload_time": image.upload_time.isoformat(),
                "view_count": image.view_count,
                "uploader": image.uploader,
                "tags": [{"name": tag.name, "category": tag.category} for tag in tags],
                "searchable_keywords": searchable_keywords,
                "similarity_score": similarity_score
            })
        
        # 按相似度排序
        result_images.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return result_images
    
    def _calculate_similarity_score(self, image: Image, tags: List[Tag], 
                                  searchable_keywords: List[str], reference_terms: List[str]) -> float:
        """计算相似度得分"""
        score = 0.0
        
        # 标签匹配度 (40%)
        tag_names = [tag.name for tag in tags]
        tag_matches = len(set(tag_names) & set(reference_terms))
        tag_score = tag_matches / max(len(reference_terms), 1) * 0.4
        
        # 关键词匹配度 (30%)
        keyword_matches = len(set(searchable_keywords) & set(reference_terms))
        keyword_score = keyword_matches / max(len(reference_terms), 1) * 0.3
        
        # AI置信度 (20%)
        confidence_score = (image.ai_confidence or 0.0) * 0.2
        
        # 流行度 (10%)
        popularity_score = min(image.view_count / 100, 1.0) * 0.1
        
        score = tag_score + keyword_score + confidence_score + popularity_score
        
        return min(score, 1.0)
    
    # 保持原有的搜索功能...
    async def search_with_gpt4o(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """使用GPT-4o进行智能搜索"""
        try:
            # 1. 使用GPT-4o增强查询
            enhanced_query = await gpt4o_analyzer.enhance_search_query(query)
            
            # 2. 获取所有可能相关的图片描述
            candidate_images = await self._get_candidate_images(enhanced_query, limit * 2)
            
            # 3. 如果候选图片数量较少，直接返回
            if len(candidate_images) <= limit:
                return {
                    "query": query,
                    "enhanced_query": enhanced_query,
                    "total": len(candidate_images),
                    "images": candidate_images,
                    "search_method": "enhanced_keyword"
                }
            
            # 4. 使用GPT-4o进行语义相似度排序
            descriptions = [img["description"] for img in candidate_images]
            similarity_result = await gpt4o_analyzer.search_similar_images(query, descriptions)
            
            # 5. 根据相似度重新排序
            sorted_images = await self._sort_by_similarity(candidate_images, similarity_result)
            
            return {
                "query": query,
                "enhanced_query": enhanced_query,
                "total": len(sorted_images),
                "images": sorted_images[:limit],
                "search_method": "gpt4o_semantic",
                "similarity_analysis": similarity_result.get("query_analysis", "")
            }
            
        except Exception as e:
            print(f"❌ Smart search failed: {e}")
            # 降级到传统搜索
            return await self._fallback_search(query, limit)
    
    async def _get_candidate_images(self, enhanced_query: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """获取候选图片"""
        # 提取关键词
        keywords = enhanced_query.get("keywords", [])
        synonyms = enhanced_query.get("synonyms", [])
        all_search_terms = list(set(keywords + synonyms))
        
        if not all_search_terms:
            # 如果没有关键词，返回最新的图片
            return await self._get_latest_images(limit)
        
        # 构建数据库查询
        base_query = self.db.query(Image).filter(Image.is_active == True)
        
        # 在描述中搜索关键词
        description_conditions = []
        for term in all_search_terms:
            description_conditions.append(Image.ai_description.contains(term))
        
        # 在标签中搜索关键词
        tag_subquery = self.db.query(ImageTag.image_id).join(Tag).filter(
            Tag.name.in_(all_search_terms)
        ).subquery()
        
        # 在搜索关键词中搜索
        keyword_conditions = []
        for term in all_search_terms:
            keyword_conditions.append(
                Image.ai_searchable_keywords.contains(f'"{term}"')
            )
        
        # 组合查询条件
        final_query = base_query.filter(
            or_(
                or_(*description_conditions) if description_conditions else False,
                Image.id.in_(tag_subquery),
                or_(*keyword_conditions) if keyword_conditions else False
            )
        ).order_by(
            Image.view_count.desc(),
            Image.upload_time.desc()
        ).limit(limit)
        
        images = final_query.all()
        return await self._format_image_results(images)
    
    async def _get_latest_images(self, limit: int) -> List[Dict[str, Any]]:
        """获取最新图片"""
        images = self.db.query(Image).filter(
            Image.is_active == True
        ).order_by(
            Image.upload_time.desc()
        ).limit(limit).all()
        
        return await self._format_image_results(images)
    
    async def _format_image_results(self, images: List[Image]) -> List[Dict[str, Any]]:
        """格式化图片结果"""
        result_images = []
        
        for image in images:
            # 获取标签
            tags = self.db_service.get_image_tags(image.id)
            
            # 解析搜索关键词
            searchable_keywords = []
            if hasattr(image, 'ai_searchable_keywords') and image.ai_searchable_keywords:
                try:
                    if isinstance(image.ai_searchable_keywords, str):
                        searchable_keywords = json.loads(image.ai_searchable_keywords)
                    else:
                        searchable_keywords = image.ai_searchable_keywords
                except:
                    pass
            
            result_images.append({
                "id": image.id,
                "filename": image.filename,
                "url": f"/uploads/{image.file_path.split('/')[-1]}",
                "width": image.width,
                "height": image.height,
                "description": image.ai_description or "",
                "confidence": image.ai_confidence or 0.0,
                "mood": getattr(image, 'ai_mood', ''),
                "style": getattr(image, 'ai_style', ''),
                "upload_time": image.upload_time.isoformat(),
                "view_count": image.view_count,
                "uploader": image.uploader,
                "tags": [{"name": tag.name, "category": tag.category} for tag in tags],
                "searchable_keywords": searchable_keywords
            })
        
        return result_images
    
    async def _sort_by_similarity(self, images: List[Dict[str, Any]], similarity_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根据相似度排序图片"""
        matches = similarity_result.get("matches", [])
        
        if not matches:
            return images
        
        # 创建相似度映射
        similarity_map = {}
        for match in matches:
            index = match.get("index", 0) - 1  # GPT返回的索引从1开始
            score = match.get("similarity_score", 0.0)
            if 0 <= index < len(images):
                similarity_map[index] = score
        
        # 按相似度排序
        sorted_indices = sorted(
            range(len(images)), 
            key=lambda i: similarity_map.get(i, 0.0), 
            reverse=True
        )
        
        return [images[i] for i in sorted_indices]
    
    async def _fallback_search(self, query: str, limit: int) -> Dict[str, Any]:
        """降级搜索"""
        # 简单的关键词搜索
        images = self.db.query(Image).filter(
            and_(
                Image.is_active == True,
                or_(
                    Image.ai_description.contains(query),
                    Image.filename.contains(query)
                )
            )
        ).order_by(Image.upload_time.desc()).limit(limit).all()
        
        formatted_images = await self._format_image_results(images)
        
        return {
            "query": query,
            "total": len(formatted_images),
            "images": formatted_images,
            "search_method": "fallback_keyword"
        }
    
    async def get_search_suggestions(self, partial_query: str) -> List[str]:
        """获取搜索建议"""
        try:
            # 使用GPT-4o生成搜索建议
            enhance_result = await gpt4o_analyzer.enhance_search_query(partial_query)
            
            suggestions = []
            suggestions.extend(enhance_result.get("related_searches", []))
            suggestions.extend(enhance_result.get("synonyms", []))
            
            # 从数据库中获取相关标签
            db_suggestions = self.db.query(Tag.name).filter(
                and_(
                    Tag.is_active == True,
                    Tag.name.contains(partial_query)
                )
            ).limit(5).all()
            
            suggestions.extend([tag.name for tag in db_suggestions])
            
            # 去重并限制数量
            unique_suggestions = list(set(suggestions))
            return unique_suggestions[:8]
            
        except Exception as e:
            print(f"❌ Get suggestions failed: {e}")
            # 降级到数据库搜索
            db_suggestions = self.db.query(Tag.name).filter(
                and_(
                    Tag.is_active == True,
                    Tag.name.contains(partial_query)
                )
            ).limit(5).all()
            
            return [tag.name for tag in db_suggestions]