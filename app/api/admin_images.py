"""
管理员图片管理API - 独立模块
"""
from app.services.storage_service import storage_manager
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text, desc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import os
import io
import csv

from app.database import get_db
from app.auth.dependencies import require_admin
from app.models.user import User
from app.models.image import Image, Tag, ImageTag
from app.services.database_service import DatabaseService
from app.services.gpt4o_service import gpt4o_analyzer
from app.services.storage_service import storage_manager

router = APIRouter()


@router.get("/list")
async def get_images_list(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(15, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query("active", description="状态筛选: active, deleted, all"),
    ai_status: Optional[str] = Query(None, description="AI分析状态: pending, completed, failed"),
    uploader: Optional[str] = Query(None, description="上传者筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("upload_time", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向: asc, desc"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取图片管理列表"""
    try:
        offset = (page - 1) * per_page
        
        # 构建查询
        query = db.query(Image)
        
        # 状态筛选
        if status == "active":
            query = query.filter(Image.is_active == True)
        elif status == "deleted":
            query = query.filter(Image.is_active == False)
        # "all" 不添加过滤条件
        
        # AI分析状态筛选
        if ai_status:
            query = query.filter(Image.ai_analysis_status == ai_status)
        
        # 上传者筛选
        if uploader:
            query = query.filter(Image.uploader.contains(uploader))
        
        # 搜索
        if search:
            query = query.filter(
                or_(
                    Image.filename.contains(search),
                    Image.ai_description.contains(search),
                    Image.uploader.contains(search)
                )
            )
        
        # 排序
        sort_column = getattr(Image, sort_by, Image.upload_time)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # 总数
        total = query.count()
        
        # 分页查询
        images = query.offset(offset).limit(per_page).all()
        
        # 处理结果
        db_service = DatabaseService(db)
        result_images = []
        
        for image in images:
            tags = db_service.get_image_tags(image.id)
            
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
                "url": storage_manager.get_image_url(image.file_path),
                "thumbnail_url": storage_manager.get_image_url(image.file_path),
                "width": image.width,
                "height": image.height,
                "file_size": image.file_size,
                "description": image.ai_description,
                "confidence": image.ai_confidence,
                "ai_analysis_status": image.ai_analysis_status,
                "ai_model": getattr(image, 'ai_model', ''),
                "mood": getattr(image, 'ai_mood', ''),
                "style": getattr(image, 'ai_style', ''),
                "upload_time": image.upload_time.isoformat(),
                "view_count": image.view_count,
                "uploader": image.uploader,
                "is_active": image.is_active,
                "tags": [{"id": tag.id, "name": tag.name, "category": tag.category} for tag in tags],
                "searchable_keywords": searchable_keywords
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


@router.get("/{image_id}/details")
async def get_image_details(
    image_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取图片详细信息"""
    try:
        db_service = DatabaseService(db)
        image = db_service.get_image_by_id(image_id, include_deleted=True)
        
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        tags = db_service.get_image_tags(image_id)
        
        # 解析原始分析结果
        raw_analysis = None
        searchable_keywords = []
        
        if hasattr(image, 'ai_analysis_raw') and image.ai_analysis_raw:
            try:
                if isinstance(image.ai_analysis_raw, str):
                    raw_analysis = json.loads(image.ai_analysis_raw)
                else:
                    raw_analysis = image.ai_analysis_raw
            except:
                pass
        
        if hasattr(image, 'ai_searchable_keywords') and image.ai_searchable_keywords:
            try:
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
                "url": storage_manager.get_image_url(image.file_path),
                "width": image.width,
                "height": image.height,
                "file_size": image.file_size,
                "description": image.ai_description,
                "confidence": image.ai_confidence,
                "ai_analysis_status": image.ai_analysis_status,
                "ai_model": getattr(image, 'ai_model', ''),
                "mood": getattr(image, 'ai_mood', ''),
                "style": getattr(image, 'ai_style', ''),
                "upload_time": image.upload_time.isoformat(),
                "view_count": image.view_count,
                "uploader": image.uploader,
                "is_active": image.is_active,
                "tags": [{"id": tag.id, "name": tag.name, "category": tag.category} for tag in tags],
                "searchable_keywords": searchable_keywords,
                "raw_analysis": raw_analysis
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图片详情失败: {str(e)}")


@router.put("/{image_id}")
async def update_image(
    image_id: int,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
    custom_tags: Optional[List[str]] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """更新图片信息"""
    try:
        db_service = DatabaseService(db)
        image = db_service.get_image_by_id(image_id, include_deleted=True)
        
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        # 更新基本信息
        if description is not None:
            image.ai_description = description
        
        if is_active is not None:
            image.is_active = is_active
        
        # 更新自定义标签
        if custom_tags is not None:
            # 删除现有标签
            db.query(ImageTag).filter(ImageTag.image_id == image_id).delete()
            
            # 添加新标签
            if custom_tags:
                db_service.add_tags_to_image(image_id, custom_tags, 'admin', [0.9] * len(custom_tags))
        
        db.commit()
        
        return {
            "success": True,
            "message": "图片信息更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新图片信息失败: {str(e)}")


@router.post("/{image_id}/reanalyze")
async def reanalyze_image(
    image_id: int,
    background_tasks: BackgroundTasks,
    custom_prompt: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """重新分析图片"""
    try:
        db_service = DatabaseService(db)
        image = db_service.get_image_by_id(image_id, include_deleted=True)
        
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        # 更新状态为重新分析中
        image.ai_analysis_status = 'pending'
        if custom_prompt:
            image.ai_model = 'gpt-4o-custom'
        db.commit()
        
        # 启动重新分析任务
        background_tasks.add_task(
            reanalyze_image_task, 
            image_id, 
            image.file_path,
            custom_prompt
        )
        
        return {
            "success": True,
            "message": "已启动重新分析任务"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动重新分析失败: {str(e)}")


@router.delete("/{image_id}")
async def delete_image(
    image_id: int,
    permanent: bool = Query(False, description="是否永久删除"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """删除图片"""
    try:
        db_service = DatabaseService(db)
        image = db_service.get_image_by_id(image_id, include_deleted=True)
        
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        if permanent:
            # 永久删除：删除文件和数据库记录
            try:
                await storage_manager.delete_image(image.file_path)
            except:
                pass  # 文件可能已经不存在
            
            # 删除相关标签关联
            db.query(ImageTag).filter(ImageTag.image_id == image_id).delete()
            
            # 删除数据库记录
            db.delete(image)
        else:
            # 软删除
            image.is_active = False
        
        db.commit()
        
        return {
            "success": True,
            "message": "图片删除成功" if permanent else "图片已移至回收站"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除图片失败: {str(e)}")


@router.post("/batch-update")
async def batch_update_images(
    image_ids: List[int],
    action: str,
    value: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """批量更新图片"""
    try:
        updated_count = 0
        db_service = DatabaseService(db)
        
        for image_id in image_ids:
            image = db.query(Image).filter(Image.id == image_id).first()
            if not image:
                continue
                
            if action == "activate":
                image.is_active = True
                updated_count += 1
            elif action == "deactivate":
                image.is_active = False
                updated_count += 1
            elif action == "add_tag" and value:
                # 添加标签
                db_service.add_tags_to_image(image_id, [value], 'admin', [0.9])
                updated_count += 1
            elif action == "remove_tag" and value:
                # 删除标签
                db.query(ImageTag).filter(
                    and_(
                        ImageTag.image_id == image_id,
                        ImageTag.tag_id.in_(
                            db.query(Tag.id).filter(Tag.name == value)
                        )
                    )
                ).delete(synchronize_session=False)
                updated_count += 1
            elif action == "delete":
                permanent = value == "permanent"
                if permanent:
                    try:
                        await storage_manager.delete_image(image.file_path)
                    except:
                        pass
                    db.query(ImageTag).filter(ImageTag.image_id == image_id).delete()
                    db.delete(image)
                else:
                    image.is_active = False
                updated_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "message": f"成功更新 {updated_count} 张图片",
            "updated_count": updated_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量更新失败: {str(e)}")


@router.get("/analytics")
async def get_images_analytics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取图片分析数据"""
    try:
        # 按上传者统计
        uploader_stats = db.query(
            Image.uploader,
            func.count(Image.id).label('count'),
            func.avg(Image.ai_confidence).label('avg_confidence'),
            func.sum(Image.file_size).label('total_size')
        ).filter(Image.is_active == True).group_by(Image.uploader).order_by(desc('count')).limit(10).all()
        
        # 按AI状态统计
        ai_status_stats = db.query(
            Image.ai_analysis_status,
            func.count(Image.id).label('count')
        ).filter(Image.is_active == True).group_by(Image.ai_analysis_status).all()
        
        # 按月份统计上传量
        monthly_uploads = db.query(
            func.year(Image.upload_time).label('year'),
            func.month(Image.upload_time).label('month'),
            func.count(Image.id).label('count'),
            func.avg(Image.file_size).label('avg_size')
        ).filter(Image.is_active == True).group_by('year', 'month').order_by('year', 'month').limit(12).all()
        
        # 标签使用频率
        tag_usage = db.query(
            Tag.name,
            func.count(ImageTag.image_id).label('usage_count'),
            Tag.category
        ).join(ImageTag).join(Image).filter(
            Image.is_active == True
        ).group_by(Tag.name, Tag.category).order_by(desc('usage_count')).limit(30).all()
        
        # 文件大小分布
        size_distribution = db.query(
            func.case([
                (Image.file_size < 100000, 'small'),
                (Image.file_size < 1000000, 'medium'),
                (Image.file_size < 5000000, 'large'),
            ], else_='xlarge').label('size_category'),
            func.count(Image.id).label('count'),
            func.sum(Image.file_size).label('total_size')
        ).filter(Image.is_active == True).group_by('size_category').all()
        
        # 图片尺寸分布
        dimension_stats = db.query(
            func.case([
                (func.greatest(Image.width, Image.height) < 500, 'small'),
                (func.greatest(Image.width, Image.height) < 1500, 'medium'),
                (func.greatest(Image.width, Image.height) < 3000, 'large'),
            ], else_='ultra').label('dimension_category'),
            func.count(Image.id).label('count'),
            func.avg(Image.width).label('avg_width'),
            func.avg(Image.height).label('avg_height')
        ).filter(Image.is_active == True).group_by('dimension_category').all()
        
        return {
            "success": True,
            "data": {
                "uploader_stats": [
                    {
                        "uploader": stat.uploader,
                        "count": stat.count,
                        "avg_confidence": round(stat.avg_confidence or 0, 2),
                        "total_size": stat.total_size or 0
                    }
                    for stat in uploader_stats
                ],
                "ai_status_stats": [
                    {
                        "status": stat.ai_analysis_status,
                        "count": stat.count
                    }
                    for stat in ai_status_stats
                ],
                "monthly_uploads": [
                    {
                        "year": stat.year,
                        "month": stat.month,
                        "count": stat.count,
                        "avg_size": round(stat.avg_size or 0, 2),
                        "date": f"{stat.year}-{stat.month:02d}"
                    }
                    for stat in monthly_uploads
                ],
                "tag_usage": [
                    {
                        "tag": stat.name,
                        "count": stat.usage_count,
                        "category": stat.category
                    }
                    for stat in tag_usage
                ],
                "size_distribution": [
                    {
                        "category": stat.size_category,
                        "count": stat.count,
                        "total_size": stat.total_size or 0
                    }
                    for stat in size_distribution
                ],
                "dimension_stats": [
                    {
                        "category": stat.dimension_category,
                        "count": stat.count,
                        "avg_width": round(stat.avg_width or 0, 1),
                        "avg_height": round(stat.avg_height or 0, 1)
                    }
                    for stat in dimension_stats
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图片分析数据失败: {str(e)}")


@router.post("/duplicate-check")
async def check_duplicate_images(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """检查重复图片"""
    try:
        # 按文件名查找重复
        filename_duplicates = db.query(
            Image.filename,
            func.count(Image.id).label('count'),
            func.group_concat(Image.id).label('ids')
        ).filter(Image.is_active == True).group_by(Image.filename).having(func.count(Image.id) > 1).all()
        
        # 按文件大小查找可能重复
        size_duplicates = db.query(
            Image.file_size,
            func.count(Image.id).label('count'),
            func.group_concat(Image.id).label('ids')
        ).filter(
            and_(Image.is_active == True, Image.file_size > 0)
        ).group_by(Image.file_size).having(func.count(Image.id) > 1).all()
        
        # 按尺寸查找可能重复
        dimension_duplicates = db.query(
            Image.width,
            Image.height,
            func.count(Image.id).label('count'),
            func.group_concat(Image.id).label('ids')
        ).filter(
            and_(Image.is_active == True, Image.width > 0, Image.height > 0)
        ).group_by(Image.width, Image.height).having(func.count(Image.id) > 1).all()
        
        duplicate_data = {
            "filename_duplicates": [
                {
                    "filename": dup.filename,
                    "count": dup.count,
                    "image_ids": [int(id) for id in dup.ids.split(',')]
                }
                for dup in filename_duplicates
            ],
            "size_duplicates": [
                {
                    "file_size": dup.file_size,
                    "count": dup.count,
                    "image_ids": [int(id) for id in dup.ids.split(',')]
                }
                for dup in size_duplicates
            ],
            "dimension_duplicates": [
                {
                    "width": dup.width,
                    "height": dup.height,
                    "count": dup.count,
                    "image_ids": [int(id) for id in dup.ids.split(',')]
                }
                for dup in dimension_duplicates
            ]
        }
        
        return {
            "success": True,
            "data": duplicate_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查重复图片失败: {str(e)}")


@router.get("/export")
async def export_images_data(
    format: str = Query("csv", description="导出格式: csv, json"),
    status: Optional[str] = Query("active"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """导出图片数据"""
    try:
        # 构建查询
        query = db.query(Image)
        
        if status == "active":
            query = query.filter(Image.is_active == True)
        elif status == "deleted":
            query = query.filter(Image.is_active == False)
        
        images = query.order_by(desc(Image.upload_time)).all()
        
        # 获取每张图片的标签
        db_service = DatabaseService(db)
        export_data = []
        
        for image in images:
            tags = db_service.get_image_tags(image.id)
            tag_names = [tag.name for tag in tags]
            
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
            
            export_data.append({
                "id": image.id,
                "filename": image.filename,
                "uploader": image.uploader,
                "width": image.width,
                "height": image.height,
                "file_size": image.file_size,
                "description": image.ai_description or "",
                "confidence": image.ai_confidence or 0,
                "ai_status": image.ai_analysis_status,
                "ai_model": getattr(image, 'ai_model', ''),
                "mood": getattr(image, 'ai_mood', ''),
                "style": getattr(image, 'ai_style', ''),
                "tags": ",".join(tag_names),
                "keywords": ",".join(searchable_keywords),
                "upload_time": image.upload_time.isoformat(),
                "view_count": image.view_count,
                "is_active": image.is_active
            })
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == "csv":
            output = io.StringIO()
            if export_data:
                writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
                writer.writeheader()
                writer.writerows(export_data)
            
            response = StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8-sig')),  # 使用BOM以支持Excel
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=images_export_{timestamp}.csv"}
            )
            return response
        
        else:  # JSON格式
            response_data = json.dumps(export_data, ensure_ascii=False, indent=2)
            response = StreamingResponse(
                io.BytesIO(response_data.encode()),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=images_export_{timestamp}.json"}
            )
            return response
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出数据失败: {str(e)}")


# 后台任务函数
async def reanalyze_image_task(image_id: int, file_path: str, custom_prompt: Optional[str] = None):
    """重新分析图片的后台任务"""
    try:
        print(f"🔄 开始重新分析图片 ID: {image_id}")
        
        # 使用自定义提示词或默认分析
        if custom_prompt:
            analysis_result = await gpt4o_analyzer.analyze_with_custom_prompt(file_path, custom_prompt)
        else:
            analysis_result = await gpt4o_analyzer.analyze_for_search(file_path)
        
        # 更新数据库
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            db_service = DatabaseService(db)
            image = db_service.get_image_by_id(image_id)
            
            if image:
                if analysis_result.get("success"):
                    analysis = analysis_result["analysis"]
                    
                    # 更新AI分析结果
                    image.ai_description = analysis.get('description', '')
                    image.ai_confidence = analysis.get('confidence', 0.0)
                    image.ai_analysis_status = 'completed'
                    image.ai_model = 'gpt-4o-reanalyzed' if not custom_prompt else 'gpt-4o-custom'
                    
                    # 存储完整分析结果
                    image.ai_analysis_raw = json.dumps(analysis, ensure_ascii=False)
                    image.ai_mood = analysis.get('mood', '')
                    image.ai_style = analysis.get('style', '')
                    image.ai_searchable_keywords = json.dumps(
                        analysis.get('searchable_keywords', []), 
                        ensure_ascii=False
                    )
                    
                    # 重新处理标签
                    db.query(ImageTag).filter(ImageTag.image_id == image_id).delete()
                    await _process_reanalyzed_tags(db_service, image_id, analysis)
                    
                    db.commit()
                    print(f"✅ 重新分析完成 ID: {image_id}")
                else:
                    image.ai_analysis_status = 'failed'
                    db.commit()
                    print(f"❌ 重新分析失败 ID: {image_id}")
            
        except Exception as e:
            print(f"❌ 更新重新分析结果失败: {e}")
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ 重新分析任务失败: {e}")


async def _process_reanalyzed_tags(db_service: DatabaseService, image_id: int, analysis: dict):
    """处理重新分析的标签"""
    tags = analysis.get('tags', {})
    all_tags = []
    confidences = []
    
    # 处理分类标签
    for category, tag_list in tags.items():
        if isinstance(tag_list, list):
            for tag in tag_list:
                if tag and tag.strip() and tag not in all_tags:
                    all_tags.append(tag.strip())
                    confidences.append(analysis.get('confidence', 0.8))
    
    # 添加搜索关键词作为标签
    searchable_keywords = analysis.get('searchable_keywords', [])
    for keyword in searchable_keywords:
        if keyword and keyword.strip() and keyword not in all_tags:
            all_tags.append(keyword.strip())
            confidences.append(analysis.get('confidence', 0.8))
    
    # 添加到数据库
    if all_tags:
        db_service.add_tags_to_image(image_id, all_tags, 'gpt4o-reanalyzed', confidences)