"""
小红书数据导入API
"""
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from app.database import get_db
from app.services.xiaohongshu_service import xiaohongshu_service
from app.services.database_service import DatabaseService
from app.models.external_source import ExternalContent, ExternalImage

router = APIRouter()


async def process_xiaohongshu_import(keywords: List[str], limit_per_keyword: int, db_session_factory):
    """后台任务：处理小红书内容导入"""
    try:
        print(f"🔄 开始处理小红书导入任务")
        
        # 批量导入内容
        import_result = await xiaohongshu_service.batch_import_content(keywords, limit_per_keyword)
        
        if import_result.get("success"):
            results = import_result.get("results", [])
            
            # 保存到数据库
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                saved_count = 0
                for content_data in results:
                    # 检查是否已存在
                    existing = db.query(ExternalContent).filter(
                        ExternalContent.external_id == content_data.get("id"),
                        ExternalContent.source_platform == "xiaohongshu"
                    ).first()
                    
                    if not existing:
                        # 创建新记录
                        external_content = ExternalContent(
                            external_id=content_data.get("id"),
                            source_platform="xiaohongshu",
                            source_url=content_data.get("url"),
                            title=content_data.get("title"),
                            description=content_data.get("description"),
                            author=content_data.get("author"),
                            category=content_data.get("category"),
                            image_urls=content_data.get("images", []),
                            like_count=content_data.get("like_count", 0),
                            comment_count=content_data.get("comment_count", 0),
                            share_count=content_data.get("share_count", 0),
                            ai_relevance_score=content_data.get("ai_relevance_score"),
                            ai_quality_score=content_data.get("ai_quality_score"),
                            ai_suggested_tags=content_data.get("ai_suggested_tags", []),
                            ai_analysis_reason=content_data.get("ai_analysis_reason"),
                            import_keyword=content_data.get("source_keyword"),
                            raw_data=content_data
                        )
                        
                        db.add(external_content)
                        saved_count += 1
                
                db.commit()
                print(f"✅ 小红书导入完成，保存了 {saved_count} 条内容")
                
            except Exception as e:
                print(f"❌ 保存小红书内容失败: {e}")
                db.rollback()
            finally:
                db.close()
        
    except Exception as e:
        print(f"❌ 小红书导入任务失败: {e}")


@router.post("/import")
async def import_xiaohongshu_content(
    background_tasks: BackgroundTasks,
    keywords: List[str] = Query(..., description="搜索关键词列表"),
    limit_per_keyword: int = Query(10, ge=1, le=50, description="每个关键词的搜索数量"),
    db: Session = Depends(get_db)
):
    """导入小红书内容"""
    try:
        # 启动后台导入任务
        background_tasks.add_task(
            process_xiaohongshu_import,
            keywords,
            limit_per_keyword,
            None  # 传递数据库工厂函数
        )
        
        return {
            "success": True,
            "message": f"小红书内容导入任务已启动，将搜索 {len(keywords)} 个关键词",
            "keywords": keywords,
            "limit_per_keyword": limit_per_keyword
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入任务启动失败: {str(e)}")


@router.get("/search")
async def search_xiaohongshu_content(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="搜索数量"),
    analyze: bool = Query(True, description="是否进行AI分析")
):
    """实时搜索小红书内容"""
    try:
        result = await xiaohongshu_service.search_pose_references(keyword, limit)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/content")
async def get_external_content(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    platform: str = Query("xiaohongshu", description="平台"),
    keyword: Optional[str] = Query(None, description="导入关键词过滤"),
    db: Session = Depends(get_db)
):
    """获取已导入的外部内容"""
    try:
        offset = (page - 1) * per_page
        
        # 构建查询
        query = db.query(ExternalContent).filter(
            ExternalContent.source_platform == platform,
            ExternalContent.is_active == True
        )
        
        if keyword:
            query = query.filter(ExternalContent.import_keyword.contains(keyword))
        
        # 获取总数
        total = query.count()
        
        # 获取分页数据
        contents = query.order_by(
            ExternalContent.import_time.desc()
        ).offset(offset).limit(per_page).all()
        
        # 格式化结果
        result_contents = []
        for content in contents:
            result_contents.append({
                "id": content.id,
                "external_id": content.external_id,
                "title": content.title,
                "description": content.description,
                "author": content.author,
                "source_url": content.source_url,
                "image_urls": content.image_urls or [],
                "like_count": content.like_count,
                "comment_count": content.comment_count,
                "share_count": content.share_count,
                "ai_relevance_score": content.ai_relevance_score,
                "ai_quality_score": content.ai_quality_score,
                "ai_suggested_tags": content.ai_suggested_tags or [],
                "import_keyword": content.import_keyword,
                "import_time": content.import_time.isoformat() if content.import_time else None,
                "is_processed": content.is_processed
            })
        
        return {
            "success": True,
            "data": {
                "contents": result_contents,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取内容失败: {str(e)}")


@router.get("/stats")
async def get_xiaohongshu_stats(db: Session = Depends(get_db)):
    """获取小红书导入统计"""
    try:
        from sqlalchemy import func
        
        # 基础统计
        total_content = db.query(ExternalContent).filter(
            ExternalContent.source_platform == "xiaohongshu"
        ).count()
        
        active_content = db.query(ExternalContent).filter(
            ExternalContent.source_platform == "xiaohongshu",
            ExternalContent.is_active == True
        ).count()
        
        processed_content = db.query(ExternalContent).filter(
            ExternalContent.source_platform == "xiaohongshu",
            ExternalContent.is_processed == True
        ).count()
        
        # 按关键词统计
        keyword_stats = db.query(
            ExternalContent.import_keyword,
            func.count(ExternalContent.id).label('count')
        ).filter(
            ExternalContent.source_platform == "xiaohongshu"
        ).group_by(ExternalContent.import_keyword).all()
        
        # 质量评分统计
        avg_relevance = db.query(
            func.avg(ExternalContent.ai_relevance_score)
        ).filter(
            ExternalContent.source_platform == "xiaohongshu",
            ExternalContent.ai_relevance_score.isnot(None)
        ).scalar() or 0
        
        avg_quality = db.query(
            func.avg(ExternalContent.ai_quality_score)
        ).filter(
            ExternalContent.source_platform == "xiaohongshu",
            ExternalContent.ai_quality_score.isnot(None)
        ).scalar() or 0
        
        return {
            "success": True,
            "data": {
                "total_content": total_content,
                "active_content": active_content,
                "processed_content": processed_content,
                "processing_rate": processed_content / total_content if total_content > 0 else 0,
                "avg_relevance_score": round(avg_relevance, 3),
                "avg_quality_score": round(avg_quality, 3),
                "keyword_distribution": [
                    {"keyword": kw, "count": count} for kw, count in keyword_stats
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.delete("/content/{content_id}")
async def delete_external_content(content_id: int, db: Session = Depends(get_db)):
    """删除外部内容"""
    try:
        content = db.query(ExternalContent).filter(ExternalContent.id == content_id).first()
        
        if not content:
            raise HTTPException(status_code=404, detail="内容不存在")
        
        # 软删除
        content.is_active = False
        db.commit()
        
        return {"success": True, "message": "内容删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")