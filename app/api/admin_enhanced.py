"""
增强版管理员API - 添加更多图片管理功能
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text, desc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import os
import asyncio
import zipfile
import io
from pathlib import Path

from app.database import get_db
from app.auth.dependencies import require_admin, require_user
from app.models.user import User, UserRole
from app.models.image import Image, Tag, ImageTag
from app.services.database_service import DatabaseService
from app.services.gpt4o_service import gpt4o_analyzer
from app.services.storage_service import storage_manager

router = APIRouter()


@router.get("/images/analytics")
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
            func.avg(Image.ai_confidence).label('avg_confidence')
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
            func.count(Image.id).label('count')
        ).filter(Image.is_active == True).group_by('year', 'month').order_by('year', 'month').limit(12).all()
        
        # 标签使用频率
        tag_usage = db.query(
            Tag.name,
            func.count(ImageTag.image_id).label('usage_count')
        ).join(ImageTag).join(Image).filter(
            Image.is_active == True
        ).group_by(Tag.name).order_by(desc('usage_count')).limit(20).all()
        
        # 文件大小分布
        size_distribution = db.query(
            func.case([
                (Image.file_size < 100000, 'small'),
                (Image.file_size < 1000000, 'medium'),
                (Image.file_size < 5000000, 'large'),
            ], else_='xlarge').label('size_category'),
            func.count(Image.id).label('count')
        ).filter(Image.is_active == True).group_by('size_category').all()
        
        return {
            "success": True,
            "data": {
                "uploader_stats": [
                    {
                        "uploader": stat.uploader,
                        "count": stat.count,
                        "avg_confidence": round(stat.avg_confidence or 0, 2)
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
                        "date": f"{stat.year}-{stat.month:02d}"
                    }
                    for stat in monthly_uploads
                ],
                "tag_usage": [
                    {
                        "tag": stat.name,
                        "count": stat.usage_count
                    }
                    for stat in tag_usage
                ],
                "size_distribution": [
                    {
                        "category": stat.size_category,
                        "count": stat.count
                    }
                    for stat in size_distribution
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图片分析数据失败: {str(e)}")


@router.post("/images/batch-update")
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
                db_service = DatabaseService(db)
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
        
        db.commit()
        
        return {
            "success": True,
            "message": f"成功更新 {updated_count} 张图片",
            "updated_count": updated_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量更新失败: {str(e)}")


@router.get("/images/export")
async def export_images_data(
    format: str = Query("csv", description="导出格式: csv, json"),
    status: Optional[str] = Query(None),
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
                "mood": getattr(image, 'ai_mood', ''),
                "style": getattr(image, 'ai_style', ''),
                "tags": ",".join(tag_names),
                "keywords": ",".join(searchable_keywords),
                "upload_time": image.upload_time.isoformat(),
                "view_count": image.view_count,
                "is_active": image.is_active
            })
        
        if format == "csv":
            import csv
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=export_data[0].keys() if export_data else [])
            writer.writeheader()
            writer.writerows(export_data)
            
            response = StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=images_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
            return response
        
        else:  # JSON格式
            response_data = json.dumps(export_data, ensure_ascii=False, indent=2)
            response = StreamingResponse(
                io.BytesIO(response_data.encode()),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=images_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
            )
            return response
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出数据失败: {str(e)}")


@router.post("/images/duplicate-check")
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
            ]
        }
        
        return {
            "success": True,
            "data": duplicate_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查重复图片失败: {str(e)}")


@router.get("/users/analytics")
async def get_users_analytics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取用户分析数据"""
    try:
        # 用户注册趋势（近30天）
        registration_trend = db.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            User.created_at >= datetime.now() - timedelta(days=30)
        ).group_by(func.date(User.created_at)).order_by('date').all()
        
        # 用户活跃度（最后登录时间分布）
        activity_distribution = db.query(
            func.case([
                (User.last_login >= datetime.now() - timedelta(days=1), 'today'),
                (User.last_login >= datetime.now() - timedelta(days=7), 'week'),
                (User.last_login >= datetime.now() - timedelta(days=30), 'month'),
                (User.last_login.isnot(None), 'older'),
            ], else_='never').label('activity'),
            func.count(User.id).label('count')
        ).group_by('activity').all()
        
        # 上传活跃度分布
        upload_distribution = db.query(
            func.case([
                (User.upload_count == 0, 'none'),
                (User.upload_count <= 5, 'low'),
                (User.upload_count <= 20, 'medium'),
                (User.upload_count <= 100, 'high'),
            ], else_='very_high').label('upload_level'),
            func.count(User.id).label('count')
        ).group_by('upload_level').all()
        
        # 角色分布
        role_distribution = db.query(
            User.role,
            func.count(User.id).label('count')
        ).group_by(User.role).all()
        
        return {
            "success": True,
            "data": {
                "registration_trend": [
                    {
                        "date": trend.date.isoformat(),
                        "count": trend.count
                    }
                    for trend in registration_trend
                ],
                "activity_distribution": [
                    {
                        "activity": activity.activity,
                        "count": activity.count
                    }
                    for activity in activity_distribution
                ],
                "upload_distribution": [
                    {
                        "level": upload.upload_level,
                        "count": upload.count
                    }
                    for upload in upload_distribution
                ],
                "role_distribution": [
                    {
                        "role": role.role.value,
                        "count": role.count
                    }
                    for role in role_distribution
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户分析数据失败: {str(e)}")


@router.post("/users/batch-update")
async def batch_update_users(
    user_ids: List[int],
    action: str,
    value: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """批量更新用户"""
    try:
        updated_count = 0
        
        for user_id in user_ids:
            # 防止修改自己
            if user_id == current_user.id:
                continue
                
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                continue
                
            if action == "activate":
                user.is_active = True
                updated_count += 1
            elif action == "deactivate":
                user.is_active = False
                updated_count += 1
            elif action == "verify":
                user.is_verified = True
                updated_count += 1
            elif action == "unverify":
                user.is_verified = False
                updated_count += 1
            elif action == "change_role" and value:
                try:
                    user.role = UserRole(value)
                    updated_count += 1
                except ValueError:
                    continue
        
        db.commit()
        
        return {
            "success": True,
            "message": f"成功更新 {updated_count} 个用户",
            "updated_count": updated_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量更新用户失败: {str(e)}")


@router.get("/system/performance")
async def get_system_performance(
    current_user: User = Depends(require_admin)
):
    """获取系统性能数据"""
    try:
        import psutil
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        
        # 进程信息
        process = psutil.Process()
        process_memory = process.memory_info()
        
        # 网络统计（如果可用）
        try:
            network = psutil.net_io_counters()
            network_data = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
        except:
            network_data = None
        
        return {
            "success": True,
            "data": {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "process": {
                    "memory_rss": process_memory.rss,
                    "memory_vms": process_memory.vms,
                    "pid": process.pid
                },
                "network": network_data,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"获取性能数据失败: {str(e)}",
            "data": {}
        }


@router.post("/system/cleanup")
async def system_cleanup(
    cleanup_type: str = Query(..., description="清理类型: temp_files, logs, cache, orphaned_files"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """系统清理"""
    try:
        cleanup_result = {
            "type": cleanup_type,
            "files_removed": 0,
            "space_freed": 0,
            "details": []
        }
        
        if cleanup_type == "temp_files":
            # 清理临时文件
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_files = []
            
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.startswith('tmp') or file.endswith('.tmp'):
                        file_path = os.path.join(root, file)
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            temp_files.append(file)
                            cleanup_result["files_removed"] += 1
                            cleanup_result["space_freed"] += file_size
                        except:
                            continue
            
            cleanup_result["details"] = temp_files[:10]  # 只显示前10个
            
        elif cleanup_type == "orphaned_files":
            # 检查孤立文件（数据库中不存在但文件系统中存在的文件）
            from app.config import get_settings
            settings = get_settings()
            upload_dir = settings.upload_dir
            
            # 获取数据库中的所有文件路径
            db_files = set()
            images = db.query(Image.file_path).filter(Image.is_active == True).all()
            for image in images:
                if image.file_path:
                    db_files.add(os.path.basename(image.file_path))
            
            # 扫描上传目录
            orphaned_files = []
            if os.path.exists(upload_dir):
                for file in os.listdir(upload_dir):
                    file_path = os.path.join(upload_dir, file)
                    if os.path.isfile(file_path) and file not in db_files:
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            orphaned_files.append(file)
                            cleanup_result["files_removed"] += 1
                            cleanup_result["space_freed"] += file_size
                        except:
                            continue
            
            cleanup_result["details"] = orphaned_files
            
        elif cleanup_type == "cache":
            # 清理应用缓存
            import gc
            gc.collect()
            cleanup_result["details"] = ["Python garbage collection completed"]
            
        elif cleanup_type == "logs":
            # 清理日志文件（如果有的话）
            log_files = []
            for log_file in ["app.log", "error.log", "access.log"]:
                if os.path.exists(log_file):
                    try:
                        file_size = os.path.getsize(log_file)
                        with open(log_file, 'w') as f:
                            f.write("")  # 清空而不是删除
                        log_files.append(log_file)
                        cleanup_result["files_removed"] += 1
                        cleanup_result["space_freed"] += file_size
                    except:
                        continue
            
            cleanup_result["details"] = log_files
        
        return {
            "success": True,
            "data": cleanup_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系统清理失败: {str(e)}")


@router.get("/system/database-stats")
async def get_database_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取数据库统计信息"""
    try:
        stats = {}
        
        # 表大小统计
        table_stats = db.execute(text("""
            SELECT 
                TABLE_NAME,
                TABLE_ROWS,
                DATA_LENGTH,
                INDEX_LENGTH,
                (DATA_LENGTH + INDEX_LENGTH) as TOTAL_SIZE
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TOTAL_SIZE DESC
        """)).fetchall()
        
        stats["table_stats"] = [
            {
                "table": row.TABLE_NAME,
                "rows": row.TABLE_ROWS or 0,
                "data_size": row.DATA_LENGTH or 0,
                "index_size": row.INDEX_LENGTH or 0,
                "total_size": row.TOTAL_SIZE or 0
            }
            for row in table_stats
        ]
        
        # 数据库大小
        db_size = db.execute(text("""
            SELECT 
                SUM(DATA_LENGTH + INDEX_LENGTH) as total_size,
                SUM(DATA_LENGTH) as data_size,
                SUM(INDEX_LENGTH) as index_size
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE()
        """)).fetchone()
        
        stats["database_size"] = {
            "total_size": db_size.total_size or 0,
            "data_size": db_size.data_size or 0,
            "index_size": db_size.index_size or 0
        }
        
        # 连接信息
        connections = db.execute(text("SHOW STATUS LIKE 'Threads_connected'")).fetchone()
        max_connections = db.execute(text("SHOW VARIABLES LIKE 'max_connections'")).fetchone()
        
        stats["connections"] = {
            "current": int(connections.Value) if connections else 0,
            "max": int(max_connections.Value) if max_connections else 0
        }
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"获取数据库统计失败: {str(e)}",
            "data": {}
        }