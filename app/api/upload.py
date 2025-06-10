"""
图片上传API - 需要用户登录
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import json
import logging

from app.database import get_db
from app.services.storage_service import storage_manager
from app.services.gpt4o_service import gpt4o_analyzer
from app.services.database_service import DatabaseService
from app.models.image import Image
from app.models.user import User
from app.auth.dependencies import require_user
from app.services.storage_service import StorageManager

# 配置日志记录器
logger = logging.getLogger(__name__)

router = APIRouter()


async def process_image_with_gpt4o(image_id: int, file_path: str, is_cloud_storage: bool = False):
    """后台任务：使用GPT-4o分析图片"""
    try:
        print(f"🤖 开始GPT-4o分析图片 ID: {image_id}")
        
        # 对于云存储，需要下载图片进行分析
        analysis_file_path = file_path
        if is_cloud_storage:
            # 这里可以实现临时下载逻辑，或者直接使用URL分析
            # 目前使用file_path作为分析路径
            pass
        
        # 使用GPT-4o进行专门的搜索优化分析
        analysis_result = await gpt4o_analyzer.analyze_for_search(analysis_file_path)
        
        if not analysis_result.get("success"):
            error_msg = analysis_result.get("error", "Unknown error")
            print(f"❌ GPT-4o分析失败: {error_msg}")
            
            # 使用fallback分析
            if "fallback_analysis" in analysis_result:
                analysis = analysis_result["fallback_analysis"]
            else:
                analysis = {
                    "description": "图片分析待处理",
                    "tags": {"general": ["图片", "参考"]},
                    "confidence": 0.5
                }
        else:
            analysis = analysis_result["analysis"]
        
        # 更新数据库
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            db_service = DatabaseService(db)
            image = db_service.get_image_by_id(image_id)
            
            if image:
                # 更新AI分析结果
                image.ai_description = analysis.get('description', '')
                image.ai_confidence = analysis.get('confidence', 0.0)
                image.ai_analysis_status = 'completed'
                image.ai_model = 'gpt-4o'
                
                # 存储完整的GPT-4o分析结果
                image.ai_analysis_raw = json.dumps(analysis, ensure_ascii=False)
                image.ai_mood = analysis.get('mood', '')
                image.ai_style = analysis.get('style', '')
                image.ai_searchable_keywords = json.dumps(
                    analysis.get('searchable_keywords', []), 
                    ensure_ascii=False
                )
                
                # 处理标签
                await _process_gpt4o_tags(db_service, image_id, analysis)
                
                db.commit()
                print(f"✅ GPT-4o分析完成 ID: {image_id}")
            
        except Exception as e:
            print(f"❌ 更新分析结果失败: {e}")
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ GPT-4o分析失败: {e}")
        
        # 标记分析失败
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            image = db.query(Image).filter(Image.id == image_id).first()
            if image:
                image.ai_analysis_status = 'failed'
                image.ai_model = 'gpt-4o'
                db.commit()
        except Exception:
            pass
        finally:
            db.close()


async def _process_gpt4o_tags(db_service: DatabaseService, image_id: int, analysis: dict):
    """处理GPT-4o生成的标签"""
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
    
    # 添加氛围和风格作为标签
    mood = analysis.get('mood', '')
    style = analysis.get('style', '')
    
    if mood and mood not in all_tags:
        all_tags.append(mood)
        confidences.append(analysis.get('confidence', 0.7))
    
    if style and style not in all_tags:
        all_tags.append(style)
        confidences.append(analysis.get('confidence', 0.7))
    
    # 添加到数据库
    if all_tags:
        db_service.add_tags_to_image(image_id, all_tags, 'gpt4o', confidences)


@router.post("/upload")
async def upload_image(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_user),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    上传图片到云存储并进行GPT-4o分析（需要登录）
    """
    try:
        # 确保使用云存储管理器
        storage_manager = StorageManager()
        
        # 保存文件到OSS
        file_path, original_filename = await storage_manager.save_upload_file(file, "ai-pose-gallery")
        
        # 获取文件信息
        file_info = storage_manager.get_file_info(file_path)
        
        # 确保URL使用正确的OSS路径
        oss_url = storage_manager.get_oss_url(file_path)
        
        upload_result = {
            "filename": file_info.get("filename", original_filename),
            "original_filename": original_filename,
            "file_path": file_path,
            "file_size": file_info.get("file_size", 0),
            "width": file_info.get("width", 0),
            "height": file_info.get("height", 0),
            "url": oss_url,  # 确保使用OSS URL
            "storage_type": "oss"
        }
        
        # 创建数据库记录
        db_service = DatabaseService(db)
        image = db_service.create_image(
            filename=upload_result["filename"],
            original_filename=upload_result["original_filename"],
            file_path=upload_result["file_path"],
            file_size=upload_result["file_size"],
            url=upload_result["url"],  # 使用OSS URL
            width=upload_result["width"],
            height=upload_result["height"],
            uploader=current_user.username,
            ai_analysis_status="pending",
            ai_model="gpt-4o"
        )
        
        # 更新用户上传统计
        current_user.upload_count += 1
        db.commit()
        
        # 启动GPT-4o分析任务
        background_tasks.add_task(
            process_image_with_gpt4o, 
            image.id, 
            upload_result["file_path"],
            True  # 使用云存储
        )
        
        return JSONResponse({
            "success": True,
            "message": "图片上传成功，GPT-4o正在分析中...",
            "data": {
                "id": image.id,
                "filename": upload_result["filename"],
                "original_filename": upload_result["original_filename"],
                "file_size": upload_result["file_size"],
                "width": upload_result["width"],
                "height": upload_result["height"],
                "url": upload_result["url"],
                "upload_time": image.upload_time.isoformat(),
                "uploader": current_user.username,
                "ai_analysis_status": image.ai_analysis_status,
                "analyzer": "gpt-4o",
                "storage_type": upload_result["storage_type"]
            }
        })
        
    except Exception as e:
        logger.error(f"上传图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("/upload/status/{image_id}")
async def get_upload_status(
    image_id: int, 
    current_user: User = Depends(require_user),  # 要求用户登录
    db: Session = Depends(get_db)
):
    """获取图片GPT-4o分析状态"""
    db_service = DatabaseService(db)
    image = db_service.get_image_by_id(image_id)
    
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    # 检查用户权限（只能查看自己上传的图片状态，管理员可以查看所有）
    if image.uploader != current_user.username and current_user.role.value not in ['admin', 'moderator']:
        raise HTTPException(status_code=403, detail="没有权限查看此图片状态")
    
    # 获取标签
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
        "id": image.id,
        "ai_analysis_status": image.ai_analysis_status,
        "ai_description": image.ai_description,
        "ai_confidence": image.ai_confidence,
        "ai_model": getattr(image, 'ai_model', 'gpt-4o'),
        "ai_mood": getattr(image, 'ai_mood', ''),
        "ai_style": getattr(image, 'ai_style', ''),
        "tags": [{"name": tag.name, "category": tag.category} for tag in tags],
        "searchable_keywords": searchable_keywords,
        "url": storage_manager.get_image_url(image.file_path),
        "raw_analysis": raw_analysis
    }


@router.delete("/upload/{image_id}")
async def delete_image(
    image_id: int, 
    current_user: User = Depends(require_user),  # 要求用户登录
    db: Session = Depends(get_db)
):
    """删除图片（包括云存储文件）"""
    db_service = DatabaseService(db)
    image = db_service.get_image_by_id(image_id)
    
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    # 检查用户权限（只能删除自己上传的图片，管理员可以删除所有）
    if image.uploader != current_user.username and current_user.role.value not in ['admin', 'moderator']:
        raise HTTPException(status_code=403, detail="没有权限删除此图片")
    
    try:
        # 删除云存储文件
        await storage_manager.delete_image(image.file_path)
        
        # 软删除数据库记录
        image.is_active = False
        db.commit()
        
        # 更新用户上传统计
        if current_user.username == image.uploader:
            current_user.upload_count = max(0, current_user.upload_count - 1)
            db.commit()
        
        return {"success": True, "message": "图片删除成功"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")