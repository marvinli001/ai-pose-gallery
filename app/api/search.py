"""
搜索API - 添加相似图片推荐功能
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.smart_search_service import SmartSearchService
from app.services.database_service import DatabaseService

router = APIRouter()


@router.get("/similar/{image_id}")
async def get_similar_images(
    image_id: int = Path(..., description="目标图片ID"),
    similarity_type: str = Query("tags", description="相似度类型: tags, style, mood, ai"),
    limit: int = Query(6, ge=1, le=20, description="返回数量"),
    db: Session = Depends(get_db)
):
    """获取相似图片推荐"""
    try:
        search_service = SmartSearchService(db)
        result = await search_service.find_similar_images(image_id, similarity_type, limit)
        
        if result["success"]:
            return {
                "success": True,
                "data": result
            }
        else:
            raise HTTPException(status_code=404, detail=result["error"])
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取相似图片失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取相似图片失败: {str(e)}")


@router.get("/search")
async def search_images(
    q: str = Query(..., description="搜索查询，支持自然语言"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量"),
    use_ai: bool = Query(True, description="使用GPT-4o进行智能搜索"),
    db: Session = Depends(get_db)
):
    """
    GPT-4o驱动的智能图片搜索
    
    支持的查询示例：
    - "女性坐姿"
    - "男性站立 室内"
    - "不要正面角度"
    - "户外 自然光"
    """
    try:
        if use_ai:
            # 使用GPT-4o智能搜索
            search_service = SmartSearchService(db)
            result = await search_service.search_with_gpt4o(q, limit)
        else:
            # 使用传统搜索
            search_service = SmartSearchService(db)
            result = await search_service._fallback_search(q, limit)
        
        # 更新查看次数
        db_service = DatabaseService(db)
        for image_data in result["images"]:
            db_service.update_image_view_count(image_data["id"])
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/search/suggestions")
async def get_search_suggestions(
    q: str = Query(..., description="部分查询词"),
    db: Session = Depends(get_db)
):
    """获取AI驱动的搜索建议"""
    try:
        search_service = SmartSearchService(db)
        suggestions = await search_service.get_search_suggestions(q)
        
        return {
            "success": True,
            "data": {
                "query": q,
                "suggestions": suggestions
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取建议失败: {str(e)}")


@router.get("/search/popular")
async def get_popular_searches(db: Session = Depends(get_db)):
    """获取热门搜索词"""
    popular_searches = [
        "女性坐姿",
        "男性站立",
        "室内场景",
        "户外自然光",
        "思考表情",
        "阅读动作",
        "办公室环境",
        "休闲服装",
        "专业风格",
        "轻松氛围"
    ]
    
    return {
        "success": True,
        "data": {
            "popular_searches": popular_searches
        }
    }


@router.get("/tags")
async def get_all_tags(
    category: Optional[str] = Query(None, description="标签分类"),
    db: Session = Depends(get_db)
):
    """获取所有标签"""
    try:
        db_service = DatabaseService(db)
        
        if category:
            tags = db_service.get_tags_by_category(category)
        else:
            tags = db_service.get_popular_tags(limit=100)
        
        return {
            "success": True,
            "data": {
                "category": category,
                "tags": [
                    {
                        "name": tag.name,
                        "category": tag.category,
                        "description": tag.description,
                        "usage_count": tag.usage_count
                    }
                    for tag in tags
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取标签失败: {str(e)}")


@router.get("/tags/categories")
async def get_tag_categories(db: Session = Depends(get_db)):
    """获取标签分类"""
    from app.models.image import TagCategory
    
    categories = [
        {"key": TagCategory.POSE, "name": "姿势类型"},
        {"key": TagCategory.GENDER, "name": "性别"},
        {"key": TagCategory.AGE, "name": "年龄"},
        {"key": TagCategory.CLOTHING, "name": "服装"},
        {"key": TagCategory.PROPS, "name": "道具"},
        {"key": TagCategory.SCENE, "name": "场景"},
        {"key": TagCategory.LIGHTING, "name": "光线"},
        {"key": TagCategory.ANGLE, "name": "角度"},
        {"key": TagCategory.EMOTION, "name": "表情"},
        {"key": TagCategory.ACTION, "name": "动作"},
        {"key": TagCategory.STYLE, "name": "风格"},
        {"key": TagCategory.MOOD, "name": "氛围"},
    ]
    
    return {
        "success": True,
        "data": {
            "categories": categories
        }
    }


@router.get("/images/{image_id}")
async def get_image_detail(
    image_id: int,
    db: Session = Depends(get_db)
):
    """获取图片详情"""
    try:
        db_service = DatabaseService(db)
        image = db_service.get_image_by_id(image_id)
        
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        # 获取标签
        tags = db_service.get_image_tags(image_id)
        
        # 更新查看次数
        db_service.update_image_view_count(image_id)
        
        # 解析搜索关键词
        searchable_keywords = []
        if hasattr(image, 'ai_searchable_keywords') and image.ai_searchable_keywords:
            try:
                import json
                if isinstance(image.ai_searchable_keywords, str):
                    searchable_keywords = json.loads(image.ai_searchable_keywords)
                else:
                    searchable_keywords = image.ai_searchable_keywords
            except:
                pass
        
        return {
            "success": True,
            "data": {
                "id": image.id,
                "filename": image.filename,
                "url": f"/uploads/{image.file_path.split('/')[-1]}",
                "width": image.width,
                "height": image.height,
                "file_size": image.file_size,
                "description": image.ai_description,
                "confidence": image.ai_confidence,
                "model": getattr(image, 'ai_model', 'gpt-4o'),
                "mood": getattr(image, 'ai_mood', ''),
                "style": getattr(image, 'ai_style', ''),
                "upload_time": image.upload_time.isoformat(),
                "view_count": image.view_count,
                "uploader": image.uploader,
                "tags": [
                    {
                        "name": tag.name,
                        "category": tag.category,
                        "description": tag.description
                    }
                    for tag in tags
                ],
                "searchable_keywords": searchable_keywords
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图片详情失败: {str(e)}")


@router.get("/images")
async def get_images(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取图片列表"""
    try:
        from app.models.image import Image
        
        offset = (page - 1) * per_page
        
        # 查询图片
        images = db.query(Image).filter(
            Image.is_active == True
        ).order_by(
            Image.upload_time.desc()
        ).offset(offset).limit(per_page).all()
        
        # 总数
        total = db.query(Image).filter(Image.is_active == True).count()
        
        # 处理结果
        db_service = DatabaseService(db)
        result_images = []
        
        for image in images:
            tags = db_service.get_image_tags(image.id)
            result_images.append({
                "id": image.id,
                "filename": image.filename,
                "url": f"/uploads/{image.file_path.split('/')[-1]}",
                "width": image.width,
                "height": image.height,
                "description": image.ai_description,
                "confidence": image.ai_confidence,
                "upload_time": image.upload_time.isoformat(),
                "view_count": image.view_count,
                "uploader": image.uploader,
                "tags": [{"name": tag.name, "category": tag.category} for tag in tags]
            })
        
        return {
            "success": True,
            "data": {
                "images": result_images,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图片列表失败: {str(e)}")