"""
管理员API - 完整后台管理功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text, desc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import os
import asyncio
from pathlib import Path

from app.database import get_db
from app.auth.dependencies import require_admin, require_user
from app.models.user import User, UserRole
from app.models.image import Image, Tag, ImageTag
from app.services.database_service import DatabaseService
from app.services.gpt4o_service import gpt4o_analyzer
from app.services.storage_service import storage_manager
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取管理员统计数据"""
    try:
        # 基础统计
        total_images = db.query(Image).count()
        active_images = db.query(Image).filter(Image.is_active == True).count()
        deleted_images = total_images - active_images
        
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        
        total_tags = db.query(Tag).count()
        active_tags = db.query(Tag).filter(Tag.is_active == True).count()
        
        # AI分析状态统计
        pending_analysis = db.query(Image).filter(
            and_(Image.is_active == True, Image.ai_analysis_status == 'pending')
        ).count()
        
        completed_analysis = db.query(Image).filter(
            and_(Image.is_active == True, Image.ai_analysis_status == 'completed')
        ).count()
        
        failed_analysis = db.query(Image).filter(
            and_(Image.is_active == True, Image.ai_analysis_status == 'failed')
        ).count()
        
        # 今日统计
        today = datetime.now().date()
        today_uploads = db.query(Image).filter(
            and_(
                Image.is_active == True,
                func.date(Image.upload_time) == today
            )
        ).count()
        
        today_registrations = db.query(User).filter(
            func.date(User.created_at) == today
        ).count()
        
        # 存储统计
        total_file_size = db.query(func.sum(Image.file_size)).filter(
            Image.is_active == True
        ).scalar() or 0
        
        # 用户角色统计
        admin_count = db.query(User).filter(User.role == UserRole.ADMIN).count()
        moderator_count = db.query(User).filter(User.role == UserRole.MODERATOR).count()
        user_count = db.query(User).filter(User.role == UserRole.USER).count()
        
        # 近7天趋势
        week_ago = datetime.now() - timedelta(days=7)
        week_uploads = []
        week_registrations = []
        
        for i in range(7):
            day = (datetime.now() - timedelta(days=6-i)).date()
            day_uploads = db.query(Image).filter(
                and_(
                    Image.is_active == True,
                    func.date(Image.upload_time) == day
                )
            ).count()
            
            day_registrations = db.query(User).filter(
                func.date(User.created_at) == day
            ).count()
            
            week_uploads.append({"date": day.isoformat(), "count": day_uploads})
            week_registrations.append({"date": day.isoformat(), "count": day_registrations})
        
        return {
            "success": True,
            "data": {
                "overview": {
                    "total_images": total_images,
                    "active_images": active_images,
                    "deleted_images": deleted_images,
                    "total_users": total_users,
                    "active_users": active_users,
                    "total_tags": total_tags,
                    "active_tags": active_tags,
                    "total_file_size_mb": round(total_file_size / (1024 * 1024), 2)
                },
                "ai_analysis": {
                    "pending": pending_analysis,
                    "completed": completed_analysis,
                    "failed": failed_analysis,
                    "total": pending_analysis + completed_analysis + failed_analysis
                },
                "today": {
                    "uploads": today_uploads,
                    "registrations": today_registrations
                },
                "users_by_role": {
                    "admin": admin_count,
                    "moderator": moderator_count,
                    "user": user_count
                },
                "trends": {
                    "week_uploads": week_uploads,
                    "week_registrations": week_registrations
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计数据失败: {str(e)}")


@router.get("/images")
async def get_admin_images(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选: active, deleted, all"),
    ai_status: Optional[str] = Query(None, description="AI分析状态: pending, completed, failed"),
    uploader: Optional[str] = Query(None, description="上传者筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
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
        
        # 总数
        total = query.count()
        
        # 分页查询
        images = query.order_by(desc(Image.upload_time)).offset(offset).limit(per_page).all()
        
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
                "thumbnail_url": storage_manager.get_image_url(image.file_path, size="thumbnail"),
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
                "tags": [{"name": tag.name, "category": tag.category} for tag in tags],
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


@router.put("/images/{image_id}")
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
        image = db_service.get_image_by_id(image_id)
        
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
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新图片信息失败: {str(e)}")


@router.post("/images/{image_id}/reanalyze")
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
        image = db_service.get_image_by_id(image_id)
        
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        # 更新状态为重新分析中
        image.ai_analysis_status = 'pending'
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动重新分析失败: {str(e)}")


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
                    image.ai_model = 'gpt-4o-reanalyzed'
                    
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


@router.delete("/images/{image_id}")
async def delete_image_admin(
    image_id: int,
    permanent: bool = Query(False, description="是否永久删除"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """删除图片（管理员）"""
    try:
        db_service = DatabaseService(db)
        image = db_service.get_image_by_id(image_id)
        
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
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除图片失败: {str(e)}")


@router.post("/images/{image_id}/restore")
async def restore_image(
    image_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """恢复已删除的图片"""
    try:
        db_service = DatabaseService(db)
        image = db_service.get_image_by_id(image_id, include_deleted=True)
        
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")
        
        image.is_active = True
        db.commit()
        
        return {
            "success": True,
            "message": "图片恢复成功"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"恢复图片失败: {str(e)}")


@router.post("/batch/analyze")
async def batch_analyze_images(
    background_tasks: BackgroundTasks,
    status_filter: str = Query("pending", description="分析状态筛选"),
    limit: int = Query(50, description="批量处理数量限制"),
    custom_prompt: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """批量分析图片"""
    try:
        # 查找需要分析的图片
        query = db.query(Image).filter(Image.is_active == True)
        
        if status_filter == "pending":
            query = query.filter(Image.ai_analysis_status == 'pending')
        elif status_filter == "failed":
            query = query.filter(Image.ai_analysis_status == 'failed')
        elif status_filter == "all":
            pass  # 不添加状态过滤
        
        images = query.limit(limit).all()
        
        if not images:
            return {
                "success": True,
                "message": "没有找到需要分析的图片",
                "count": 0
            }
        
        # 启动批量分析任务
        background_tasks.add_task(
            batch_analyze_task,
            [img.id for img in images],
            custom_prompt
        )
        
        return {
            "success": True,
            "message": f"已启动批量分析任务，将处理 {len(images)} 张图片",
            "count": len(images)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动批量分析失败: {str(e)}")


async def batch_analyze_task(image_ids: List[int], custom_prompt: Optional[str] = None):
    """批量分析任务"""
    print(f"🚀 开始批量分析 {len(image_ids)} 张图片")
    
    for i, image_id in enumerate(image_ids):
        try:
            from app.database import SessionLocal
            db = SessionLocal()
            
            image = db.query(Image).filter(Image.id == image_id).first()
            if image:
                print(f"📊 分析进度: {i+1}/{len(image_ids)} - 图片ID: {image_id}")
                await reanalyze_image_task(image_id, image.file_path, custom_prompt)
                
                # 添加延迟避免API限制
                await asyncio.sleep(2)
            
            db.close()
            
        except Exception as e:
            print(f"❌ 批量分析图片 {image_id} 失败: {e}")
            continue
    
    print(f"✅ 批量分析完成")


@router.post("/scan-directory")
async def scan_and_import_directory(
    background_tasks: BackgroundTasks,
    directory_path: str = Query(..., description="要扫描的目录路径"),
    auto_analyze: bool = Query(True, description="是否自动分析新图片"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """扫描目录并导入新图片"""
    try:
        # 验证目录路径
        if not os.path.exists(directory_path):
            raise HTTPException(status_code=400, detail="指定的目录不存在")
        
        if not os.path.isdir(directory_path):
            raise HTTPException(status_code=400, detail="指定的路径不是目录")
        
        # 启动扫描任务
        background_tasks.add_task(
            scan_directory_task,
            directory_path,
            current_user.username,
            auto_analyze
        )
        
        return {
            "success": True,
            "message": f"已启动目录扫描任务: {directory_path}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动目录扫描失败: {str(e)}")


async def scan_directory_task(directory_path: str, uploader: str, auto_analyze: bool = True):
    """扫描目录任务"""
    print(f"📁 开始扫描目录: {directory_path}")
    
    supported_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
    imported_count = 0
    skipped_count = 0
    
    try:
        from app.database import SessionLocal
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = Path(file).suffix.lower()
                
                if file_ext not in supported_extensions:
                    continue
                
                try:
                    # 检查文件是否已存在
                    db = SessionLocal()
                    existing = db.query(Image).filter(
                        or_(
                            Image.filename == file,
                            Image.file_path.contains(file)
                        )
                    ).first()
                    
                    if existing:
                        skipped_count += 1
                        db.close()
                        continue
                    
                    # 读取文件
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    # 上传到存储
                    upload_result = await storage_manager.upload_image(file_content, file)
                    
                    if upload_result.get("success"):
                        # 创建数据库记录
                        db_service = DatabaseService(db)
                        image = db_service.create_image(
                            filename=file,
                            file_path=upload_result["file_path"],
                            file_size=upload_result["file_size"],
                            width=upload_result["width"],
                            height=upload_result["height"],
                            uploader=uploader,
                            ai_analysis_status="pending" if auto_analyze else "skipped",
                            ai_model="gpt-4o"
                        )
                        
                        imported_count += 1
                        
                        # 自动分析
                        if auto_analyze:
                            await reanalyze_image_task(image.id, upload_result["file_path"])
                        
                        print(f"✅ 导入图片: {file}")
                    else:
                        print(f"❌ 上传失败: {file}")
                    
                    db.close()
                    
                except Exception as e:
                    print(f"❌ 处理文件 {file} 失败: {e}")
                    continue
    
    except Exception as e:
        print(f"❌ 扫描目录失败: {e}")
    
    print(f"📁 目录扫描完成 - 导入: {imported_count}, 跳过: {skipped_count}")

@router.post("/scan-oss")
async def scan_oss_directory(
    background_tasks: BackgroundTasks,
    oss_prefix: str = Query("", description="OSS前缀路径"),
    auto_analyze: bool = Query(True, description="是否自动分析新图片"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """扫描OSS存储桶并导入新图片"""
    try:
        # 检查OSS是否启用
        if not get_settings().use_oss_storage:
            raise HTTPException(status_code=400, detail="OSS存储未启用")
        
        # 启动OSS扫描任务
        background_tasks.add_task(
            scan_oss_task,
            oss_prefix,
            current_user.username,
            auto_analyze
        )
        
        return {
            "success": True,
            "message": f"已启动OSS扫描任务: {oss_prefix or '根目录'}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动OSS扫描失败: {str(e)}")

@router.get("/users")
async def get_admin_users(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    role: Optional[str] = Query(None, description="角色筛选"),
    status: Optional[str] = Query(None, description="状态筛选: active, inactive"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取用户管理列表"""
    try:
        offset = (page - 1) * per_page
        
        # 构建查询
        query = db.query(User)
        
        # 角色筛选
        if role:
            try:
                query = query.filter(User.role == UserRole(role))
            except ValueError:
                pass
        
        # 状态筛选
        if status == "active":
            query = query.filter(User.is_active == True)
        elif status == "inactive":
            query = query.filter(User.is_active == False)
        
        # 搜索
        if search:
            query = query.filter(
                or_(
                    User.username.contains(search),
                    User.email.contains(search),
                    User.full_name.contains(search)
                )
            )
        
        # 总数
        total = query.count()
        
        # 分页查询
        users = query.order_by(desc(User.created_at)).offset(offset).limit(per_page).all()
        
        # 处理结果
        result_users = []
        for user in users:
            result_users.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "upload_count": user.upload_count,
                "login_count": user.login_count,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat(),
                "avatar_url": user.avatar_url,
                "location": user.location,
                "website": user.website
            })
        
        return {
            "success": True,
            "data": {
                "users": result_users,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 防止修改自己的权限
        if user.id == current_user.id and role is not None:
            raise HTTPException(status_code=400, detail="不能修改自己的角色")
        
        # 更新角色
        if role is not None:
            try:
                user.role = UserRole(role)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的角色")
        
        # 更新状态
        if is_active is not None:
            # 防止禁用自己
            if user.id == current_user.id and not is_active:
                raise HTTPException(status_code=400, detail="不能禁用自己的账号")
            user.is_active = is_active
        
        if is_verified is not None:
            user.is_verified = is_verified
        
        db.commit()
        
        return {
            "success": True,
            "message": "用户信息更新成功"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新用户信息失败: {str(e)}")


@router.get("/system-info")
async def get_system_info(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取系统信息"""
    try:
        import psutil
        import platform
        from app.config import get_settings
        
        settings = get_settings()
        
        # 系统信息
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "disk_usage_gb": round(psutil.disk_usage('/').used / (1024**3), 2),
            "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2)
        }
        
        # 应用配置
        app_config = {
            "debug": settings.debug,
            "upload_dir": settings.upload_dir,
            "max_file_size_mb": round(settings.max_file_size / (1024**2), 2),
            "allowed_extensions": settings.allowed_extensions,
            "storage_type": getattr(settings, 'storage_type', 'local'),
            "database_url": settings.database_url.split('@')[-1] if '@' in settings.database_url else "配置已隐藏"
        }
        
        # 数据库信息
        db_info = {}
        try:
            result = db.execute(text("SELECT VERSION() as version")).fetchone()
            db_info["version"] = result[0] if result else "未知"
            
            result = db.execute(text("SHOW STATUS LIKE 'Connections'")).fetchone()
            db_info["connections"] = result[1] if result else "未知"
            
            result = db.execute(text("SHOW STATUS LIKE 'Uptime'")).fetchone()
            db_info["uptime_seconds"] = result[1] if result else "未知"
        except:
            db_info = {"error": "无法获取数据库信息"}
        
        return {
            "success": True,
            "data": {
                "system": system_info,
                "application": app_config,
                "database": db_info,
                "storage": {
                    "type": getattr(settings, 'storage_type', 'local'),
                    "upload_dir": settings.upload_dir
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"获取系统信息失败: {str(e)}",
            "data": {}
        }


@router.post("/clear-cache")
async def clear_system_cache(
    current_user: User = Depends(require_admin)
):
    """清理系统缓存"""
    try:
        import gc
        
        # 强制垃圾回收
        gc.collect()
        
        # 这里可以添加其他缓存清理逻辑
        # 比如Redis缓存、文件缓存等
        
        return {
            "success": True,
            "message": "系统缓存清理完成"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理缓存失败: {str(e)}")