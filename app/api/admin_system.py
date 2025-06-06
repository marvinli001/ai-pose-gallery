"""
管理员系统设置API - 独立模块
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text, desc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import os
import psutil
import gc
import shutil
import tempfile
from pathlib import Path

from app.database import get_db
from app.auth.dependencies import require_admin
from app.models.user import User
from app.models.image import Image
from app.config import get_settings

router = APIRouter()


@router.get("/info")
async def get_system_info(
    current_user: User = Depends(require_admin)
):
    """获取系统信息"""
    try:
        settings = get_settings()
        
        # 系统基本信息
        system_info = {
            "os": os.name,
            "platform": psutil.platform,
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }
        
        # 内存信息
        memory = psutil.virtual_memory()
        memory_info = {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent,
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2)
        }
        
        # 磁盘信息
        disk = psutil.disk_usage('/')
        disk_info = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": round((disk.used / disk.total) * 100, 2),
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2)
        }
        
        # 应用信息
        current_process = psutil.Process()
        app_info = {
            "pid": current_process.pid,
            "memory_rss": current_process.memory_info().rss,
            "memory_vms": current_process.memory_info().vms,
            "memory_percent": current_process.memory_percent(),
            "cpu_percent": current_process.cpu_percent(),
            "create_time": datetime.fromtimestamp(current_process.create_time()).isoformat(),
            "num_threads": current_process.num_threads()
        }
        
        # 网络信息（如果可用）
        try:
            network = psutil.net_io_counters()
            network_info = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
        except:
            network_info = None
        
        # 上传目录信息
        upload_dir = getattr(settings, 'upload_dir', 'uploads')
        upload_info = {}
        if os.path.exists(upload_dir):
            upload_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(upload_dir)
                for filename in filenames
            )
            upload_file_count = sum(
                len(filenames)
                for dirpath, dirnames, filenames in os.walk(upload_dir)
            )
            upload_info = {
                "path": upload_dir,
                "size": upload_size,
                "size_gb": round(upload_size / (1024**3), 2),
                "file_count": upload_file_count
            }
        
        return {
            "success": True,
            "data": {
                "system": system_info,
                "memory": memory_info,
                "disk": disk_info,
                "application": app_info,
                "network": network_info,
                "upload_directory": upload_info,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")


@router.get("/performance")
async def get_performance_metrics(
    current_user: User = Depends(require_admin)
):
    """获取性能指标"""
    try:
        # CPU信息
        cpu_info = {
            "percent": psutil.cpu_percent(interval=1),
            "per_cpu": psutil.cpu_percent(interval=1, percpu=True),
            "count": psutil.cpu_count(),
            "count_logical": psutil.cpu_count(logical=True)
        }
        
        # 内存信息
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        memory_info = {
            "virtual": {
                "total": memory.total,
                "used": memory.used,
                "available": memory.available,
                "percent": memory.percent
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent
            }
        }
        
        # 磁盘IO
        try:
            disk_io = psutil.disk_io_counters()
            disk_info = {
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count,
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes,
                "read_time": disk_io.read_time,
                "write_time": disk_io.write_time
            }
        except:
            disk_info = None
        
        # 网络IO
        try:
            net_io = psutil.net_io_counters()
            network_info = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout
            }
        except:
            network_info = None
        
        # 进程信息
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "cpu_percent": proc.info['cpu_percent'],
                    "memory_percent": proc.info['memory_percent']
                })
            except:
                continue
        
        # 按CPU使用率排序，取前10
        top_processes = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:10]
        
        return {
            "success": True,
            "data": {
                "cpu": cpu_info,
                "memory": memory_info,
                "disk_io": disk_info,
                "network_io": network_info,
                "top_processes": top_processes,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取性能指标失败: {str(e)}")


@router.get("/database-stats")
async def get_database_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取数据库统计信息"""
    try:
        stats = {}
        
        # 基本表统计
        table_stats = {
            "users": db.query(func.count(User.id)).scalar(),
            "images": db.query(func.count(Image.id)).scalar(),
            "active_images": db.query(func.count(Image.id)).filter(Image.is_active == True).scalar(),
            "inactive_images": db.query(func.count(Image.id)).filter(Image.is_active == False).scalar()
        }
        
        # 数据库文件大小（SQLite）
        try:
            settings = get_settings()
            db_url = settings.database_url
            if "sqlite" in db_url:
                db_path = db_url.replace("sqlite:///", "")
                if os.path.exists(db_path):
                    db_size = os.path.getsize(db_path)
                    stats["database_file"] = {
                        "path": db_path,
                        "size": db_size,
                        "size_mb": round(db_size / (1024**2), 2)
                    }
        except:
            pass
        
        # 最近活动统计
        now = datetime.now()
        recent_stats = {
            "users_today": db.query(func.count(User.id)).filter(
                User.created_at >= now.replace(hour=0, minute=0, second=0)
            ).scalar(),
            "users_week": db.query(func.count(User.id)).filter(
                User.created_at >= now - timedelta(days=7)
            ).scalar(),
            "images_today": db.query(func.count(Image.id)).filter(
                Image.upload_time >= now.replace(hour=0, minute=0, second=0)
            ).scalar(),
            "images_week": db.query(func.count(Image.id)).filter(
                Image.upload_time >= now - timedelta(days=7)
            ).scalar()
        }
        
        # 数据库连接统计（如果可用）
        try:
            # 这里可以添加具体数据库的连接统计
            connection_stats = {
                "active_connections": 1,  # 当前连接
                "max_connections": "unknown"
            }
        except:
            connection_stats = None
        
        return {
            "success": True,
            "data": {
                "table_stats": table_stats,
                "recent_activity": recent_stats,
                "connection_stats": connection_stats,
                "database_file": stats.get("database_file"),
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据库统计失败: {str(e)}")


@router.post("/cleanup")
async def system_cleanup(
    cleanup_type: str = Query(..., description="清理类型: temp_files, logs, cache, orphaned_files, thumbnails"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """系统清理"""
    try:
        cleanup_result = {
            "type": cleanup_type,
            "files_removed": 0,
            "space_freed": 0,
            "details": [],
            "errors": []
        }
        
        if cleanup_type == "temp_files":
            # 清理临时文件
            temp_dir = tempfile.gettempdir()
            removed_files = []
            
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.startswith(('tmp', 'temp')) or file.endswith('.tmp'):
                        file_path = os.path.join(root, file)
                        try:
                            # 检查文件是否超过1小时
                            if os.path.getmtime(file_path) < (datetime.now().timestamp() - 3600):
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                removed_files.append(file)
                                cleanup_result["files_removed"] += 1
                                cleanup_result["space_freed"] += file_size
                        except Exception as e:
                            cleanup_result["errors"].append(f"删除 {file} 失败: {str(e)}")
            
            cleanup_result["details"] = removed_files[:20]  # 只显示前20个
            
        elif cleanup_type == "orphaned_files":
            # 检查孤立文件
            settings = get_settings()
            upload_dir = getattr(settings, 'upload_dir', 'uploads')
            
            if os.path.exists(upload_dir):
                # 获取数据库中的所有文件路径
                db_files = set()
                images = db.query(Image.file_path).all()
                for image in images:
                    if image.file_path:
                        filename = os.path.basename(image.file_path)
                        db_files.add(filename)
                
                # 扫描上传目录
                orphaned_files = []
                for root, dirs, files in os.walk(upload_dir):
                    for file in files:
                        if file not in db_files and not file.startswith('.'):
                            file_path = os.path.join(root, file)
                            try:
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                orphaned_files.append(file)
                                cleanup_result["files_removed"] += 1
                                cleanup_result["space_freed"] += file_size
                            except Exception as e:
                                cleanup_result["errors"].append(f"删除 {file} 失败: {str(e)}")
                
                cleanup_result["details"] = orphaned_files
            
        elif cleanup_type == "cache":
            # 清理Python缓存
            before_objects = len(gc.get_objects())
            collected = gc.collect()
            after_objects = len(gc.get_objects())
            
            cleanup_result["details"] = [
                f"垃圾回收前对象数: {before_objects}",
                f"垃圾回收后对象数: {after_objects}",
                f"回收对象数: {collected}"
            ]
            cleanup_result["files_removed"] = collected
            
        elif cleanup_type == "logs":
            # 清理日志文件
            log_files = []
            log_patterns = ["*.log", "app.log", "error.log", "access.log", "debug.log"]
            
            for pattern in log_patterns:
                for log_file in Path(".").glob(pattern):
                    if log_file.exists():
                        try:
                            file_size = log_file.stat().st_size
                            # 清空而不是删除
                            with open(log_file, 'w') as f:
                                f.write("")
                            log_files.append(str(log_file))
                            cleanup_result["files_removed"] += 1
                            cleanup_result["space_freed"] += file_size
                        except Exception as e:
                            cleanup_result["errors"].append(f"清理 {log_file} 失败: {str(e)}")
            
            cleanup_result["details"] = log_files
            
        elif cleanup_type == "thumbnails":
            # 清理缩略图缓存
            settings = get_settings()
            upload_dir = getattr(settings, 'upload_dir', 'uploads')
            thumb_dir = os.path.join(upload_dir, 'thumbnails')
            
            if os.path.exists(thumb_dir):
                removed_thumbs = []
                for thumb_file in os.listdir(thumb_dir):
                    thumb_path = os.path.join(thumb_dir, thumb_file)
                    try:
                        file_size = os.path.getsize(thumb_path)
                        os.remove(thumb_path)
                        removed_thumbs.append(thumb_file)
                        cleanup_result["files_removed"] += 1
                        cleanup_result["space_freed"] += file_size
                    except Exception as e:
                        cleanup_result["errors"].append(f"删除缩略图 {thumb_file} 失败: {str(e)}")
                
                cleanup_result["details"] = removed_thumbs
        
        return {
            "success": True,
            "data": cleanup_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系统清理失败: {str(e)}")


@router.post("/optimize-database")
async def optimize_database(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """优化数据库"""
    try:
        optimization_result = {
            "operations": [],
            "before_size": 0,
            "after_size": 0,
            "space_saved": 0
        }
        
        # 获取优化前的数据库大小
        try:
            settings = get_settings()
            db_url = settings.database_url
            if "sqlite" in db_url:
                db_path = db_url.replace("sqlite:///", "")
                if os.path.exists(db_path):
                    optimization_result["before_size"] = os.path.getsize(db_path)
        except:
            pass
        
        # SQLite 优化操作
        try:
            # VACUUM 操作
            db.execute(text("VACUUM"))
            optimization_result["operations"].append("VACUUM - 重建数据库文件")
            
            # ANALYZE 操作
            db.execute(text("ANALYZE"))
            optimization_result["operations"].append("ANALYZE - 更新查询优化器统计信息")
            
            # 重建索引
            db.execute(text("REINDEX"))
            optimization_result["operations"].append("REINDEX - 重建所有索引")
            
            db.commit()
            
        except Exception as e:
            optimization_result["operations"].append(f"数据库优化失败: {str(e)}")
        
        # 获取优化后的数据库大小
        try:
            if "sqlite" in db_url and os.path.exists(db_path):
                optimization_result["after_size"] = os.path.getsize(db_path)
                optimization_result["space_saved"] = optimization_result["before_size"] - optimization_result["after_size"]
        except:
            pass
        
        return {
            "success": True,
            "data": optimization_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库优化失败: {str(e)}")


@router.get("/logs")
async def get_system_logs(
    log_type: str = Query("application", description="日志类型: application, error, access"),
    lines: int = Query(100, description="返回行数"),
    current_user: User = Depends(require_admin)
):
    """获取系统日志"""
    try:
        log_files = {
            "application": "app.log",
            "error": "error.log",
            "access": "access.log"
        }
        
        log_file = log_files.get(log_type, "app.log")
        log_content = []
        
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    # 获取最后N行
                    log_content = all_lines[-lines:] if len(all_lines) > lines else all_lines
            except Exception as e:
                log_content = [f"读取日志文件失败: {str(e)}"]
        else:
            log_content = [f"日志文件 {log_file} 不存在"]
        
        return {
            "success": True,
            "data": {
                "log_type": log_type,
                "file": log_file,
                "lines_requested": lines,
                "lines_returned": len(log_content),
                "content": log_content,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统日志失败: {str(e)}")


@router.get("/config")
async def get_system_config(
    current_user: User = Depends(require_admin)
):
    """获取系统配置"""
    try:
        settings = get_settings()
        
        # 安全地展示配置（隐藏敏感信息）
        config_data = {
            "database": {
                "type": "sqlite" if "sqlite" in settings.database_url else "other",
                "url_pattern": settings.database_url.split("://")[0] + "://..." if settings.database_url else None
            },
            "upload": {
                "directory": getattr(settings, 'upload_dir', 'uploads'),
                "max_file_size": getattr(settings, 'max_file_size', 10485760),
                "max_file_size_mb": round(getattr(settings, 'max_file_size', 10485760) / (1024**2), 2)
            },
            "jwt": {
                "algorithm": settings.algorithm,
                "expire_minutes": settings.access_token_expire_minutes,
                "secret_key_configured": bool(settings.secret_key)
            },
            "ai": {
                "openai_configured": bool(getattr(settings, 'openai_api_key', None))
            },
            "application": {
                "environment": os.getenv("ENVIRONMENT", "development"),
                "debug": os.getenv("DEBUG", "False").lower() == "true",
                "version": "1.0.0"  # 可以从package.json或版本文件读取
            }
        }
        
        return {
            "success": True,
            "data": config_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统配置失败: {str(e)}")


@router.post("/backup")
async def create_backup(
    include_uploads: bool = Query(True, description="是否包含上传文件"),
    current_user: User = Depends(require_admin)
):
    """创建系统备份"""
    try:
        settings = get_settings()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        
        # 创建备份目录
        backup_dir = f"backups/{backup_name}"
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_info = {
            "name": backup_name,
            "timestamp": timestamp,
            "files": [],
            "size": 0
        }
        
        # 备份数据库
        try:
            db_url = settings.database_url
            if "sqlite" in db_url:
                db_path = db_url.replace("sqlite:///", "")
                if os.path.exists(db_path):
                    backup_db_path = os.path.join(backup_dir, "database.db")
                    shutil.copy2(db_path, backup_db_path)
                    db_size = os.path.getsize(backup_db_path)
                    backup_info["files"].append({
                        "name": "database.db",
                        "size": db_size,
                        "type": "database"
                    })
                    backup_info["size"] += db_size
        except Exception as e:
            backup_info["errors"] = backup_info.get("errors", [])
            backup_info["errors"].append(f"数据库备份失败: {str(e)}")
        
        # 备份上传文件
        if include_uploads:
            try:
                upload_dir = getattr(settings, 'upload_dir', 'uploads')
                if os.path.exists(upload_dir):
                    backup_uploads_dir = os.path.join(backup_dir, "uploads")
                    shutil.copytree(upload_dir, backup_uploads_dir)
                    
                    # 计算上传文件大小
                    uploads_size = sum(
                        os.path.getsize(os.path.join(dirpath, filename))
                        for dirpath, dirnames, filenames in os.walk(backup_uploads_dir)
                        for filename in filenames
                    )
                    
                    backup_info["files"].append({
                        "name": "uploads",
                        "size": uploads_size,
                        "type": "uploads"
                    })
                    backup_info["size"] += uploads_size
            except Exception as e:
                backup_info["errors"] = backup_info.get("errors", [])
                backup_info["errors"].append(f"上传文件备份失败: {str(e)}")
        
        # 备份配置文件
        try:
            config_files = [".env", "config.py"]
            for config_file in config_files:
                if os.path.exists(config_file):
                    backup_config_path = os.path.join(backup_dir, config_file)
                    shutil.copy2(config_file, backup_config_path)
                    config_size = os.path.getsize(backup_config_path)
                    backup_info["files"].append({
                        "name": config_file,
                        "size": config_size,
                        "type": "config"
                    })
                    backup_info["size"] += config_size
        except Exception as e:
            backup_info["errors"] = backup_info.get("errors", [])
            backup_info["errors"].append(f"配置文件备份失败: {str(e)}")
        
        # 创建备份信息文件
        backup_info_path = os.path.join(backup_dir, "backup_info.json")
        with open(backup_info_path, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "data": backup_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建备份失败: {str(e)}")


@router.get("/backups")
async def list_backups(
    current_user: User = Depends(require_admin)
):
    """列出所有备份"""
    try:
        backup_dir = "backups"
        backups = []
        
        if os.path.exists(backup_dir):
            for backup_name in os.listdir(backup_dir):
                backup_path = os.path.join(backup_dir, backup_name)
                if os.path.isdir(backup_path):
                    # 读取备份信息
                    info_file = os.path.join(backup_path, "backup_info.json")
                    if os.path.exists(info_file):
                        try:
                            with open(info_file, 'r', encoding='utf-8') as f:
                                backup_info = json.load(f)
                                backup_info["path"] = backup_path
                                backups.append(backup_info)
                        except:
                            # 如果信息文件损坏，创建基本信息
                            backup_size = sum(
                                os.path.getsize(os.path.join(dirpath, filename))
                                for dirpath, dirnames, filenames in os.walk(backup_path)
                                for filename in filenames
                            )
                            backups.append({
                                "name": backup_name,
                                "path": backup_path,
                                "size": backup_size,
                                "timestamp": "unknown",
                                "files": []
                            })
        
        # 按时间戳排序
        backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return {
            "success": True,
            "data": {
                "backups": backups,
                "count": len(backups),
                "total_size": sum(backup.get("size", 0) for backup in backups)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取备份列表失败: {str(e)}")