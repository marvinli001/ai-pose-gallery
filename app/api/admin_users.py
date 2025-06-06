"""
管理员用户管理API - 独立模块
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text, desc, asc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import io
import csv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.database import get_db
from app.auth.dependencies import require_admin
from app.models.user import User, UserRole
from app.models.image import ImageTag, Image

router = APIRouter()


@router.get("/list")
async def get_users_list(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(20, ge=1, le=100, description="每页数量"),
    role: Optional[str] = Query(None, description="角色筛选: user, moderator, admin"),
    status: Optional[str] = Query(None, description="状态筛选: active, inactive"),
    verified: Optional[bool] = Query(None, description="邮箱验证状态"),
    search: Optional[str] = Query(None, description="搜索用户名或邮箱"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向: asc, desc"),
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
                role_enum = UserRole(role)
                query = query.filter(User.role == role_enum)
            except ValueError:
                pass
        
        # 状态筛选
        if status == "active":
            query = query.filter(User.is_active == True)
        elif status == "inactive":
            query = query.filter(User.is_active == False)
        
        # 邮箱验证筛选
        if verified is not None:
            query = query.filter(User.is_verified == verified)
        
        # 搜索
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.username.like(search_term),
                    User.email.like(search_term),
                    User.full_name.like(search_term)
                )
            )
        
        # 排序
        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # 总数
        total = query.count()
        
        # 分页查询
        users = query.offset(offset).limit(per_page).all()
        
        # 获取每个用户的上传统计
        result_users = []
        for user in users:
            # 获取用户上传统计
            upload_stats = db.query(
                func.count(Image.id).label('total_uploads'),
                func.count(func.nullif(Image.is_active, False)).label('active_uploads'),
                func.sum(Image.file_size).label('total_size'),
                func.avg(Image.ai_confidence).label('avg_confidence')
            ).filter(Image.uploader == user.username).first()
            
            # 最近活动
            recent_uploads = db.query(func.count(Image.id)).filter(
                and_(
                    Image.uploader == user.username,
                    Image.upload_time >= datetime.now() - timedelta(days=30)
                )
            ).scalar()
            
            result_users.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "upload_count": user.upload_count,
                "stats": {
                    "total_uploads": upload_stats.total_uploads or 0,
                    "active_uploads": upload_stats.active_uploads or 0,
                    "total_size": upload_stats.total_size or 0,
                    "avg_confidence": round(upload_stats.avg_confidence or 0, 2),
                    "recent_uploads": recent_uploads or 0
                }
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


@router.get("/{user_id}/details")
async def get_user_details(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取用户详细信息"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 获取用户上传的图片统计
        image_stats = db.query(
            func.count(Image.id).label('total_count'),
            func.count(func.nullif(Image.is_active, False)).label('active_count'),
            func.sum(Image.file_size).label('total_size'),
            func.avg(Image.ai_confidence).label('avg_confidence'),
            func.max(Image.upload_time).label('last_upload')
        ).filter(Image.uploader == user.username).first()
        
        # 按AI状态分组统计
        ai_stats = db.query(
            Image.ai_analysis_status,
            func.count(Image.id).label('count')
        ).filter(Image.uploader == user.username).group_by(Image.ai_analysis_status).all()
        
        # 最近30天活动
        recent_activity = db.query(
            func.date(Image.upload_time).label('date'),
            func.count(Image.id).label('count')
        ).filter(
            and_(
                Image.uploader == user.username,
                Image.upload_time >= datetime.now() - timedelta(days=30)
            )
        ).group_by(func.date(Image.upload_time)).order_by('date').all()
        
        # 最近上传的图片
        recent_images = db.query(Image).filter(
            Image.uploader == user.username
        ).order_by(desc(Image.upload_time)).limit(10).all()
        
        return {
            "success": True,
            "data": {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role.value,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "created_at": user.created_at.isoformat(),
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "upload_count": user.upload_count
                },
                "image_stats": {
                    "total_count": image_stats.total_count or 0,
                    "active_count": image_stats.active_count or 0,
                    "total_size": image_stats.total_size or 0,
                    "avg_confidence": round(image_stats.avg_confidence or 0, 2),
                    "last_upload": image_stats.last_upload.isoformat() if image_stats.last_upload else None
                },
                "ai_stats": [
                    {
                        "status": stat.ai_analysis_status,
                        "count": stat.count
                    }
                    for stat in ai_stats
                ],
                "recent_activity": [
                    {
                        "date": activity.date.isoformat(),
                        "count": activity.count
                    }
                    for activity in recent_activity
                ],
                "recent_images": [
                    {
                        "id": img.id,
                        "filename": img.filename,
                        "upload_time": img.upload_time.isoformat(),
                        "ai_analysis_status": img.ai_analysis_status,
                        "is_active": img.is_active
                    }
                    for img in recent_images
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户详情失败: {str(e)}")


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    full_name: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 防止修改自己的状态
        if user_id == current_user.id:
            if is_active is False:
                raise HTTPException(status_code=400, detail="不能禁用自己的账号")
            if role and role != current_user.role.value:
                raise HTTPException(status_code=400, detail="不能修改自己的角色")
        
        # 更新字段
        if role is not None:
            try:
                user.role = UserRole(role)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的角色")
        
        if is_active is not None:
            user.is_active = is_active
        
        if is_verified is not None:
            user.is_verified = is_verified
        
        if full_name is not None:
            user.full_name = full_name
        
        db.commit()
        
        return {
            "success": True,
            "message": "用户信息更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新用户信息失败: {str(e)}")


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    transfer_images: bool = Query(False, description="是否转移图片到管理员"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """删除用户"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 防止删除自己
        if user_id == current_user.id:
            raise HTTPException(status_code=400, detail="不能删除自己的账号")
        
        # 防止删除其他管理员（除非是超级管理员）
        if user.role == UserRole.ADMIN and current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="无权删除管理员账号")
        
        # 处理用户的图片
        user_images = db.query(Image).filter(Image.uploader == user.username).all()
        
        if transfer_images:
            # 转移图片到当前管理员
            for image in user_images:
                image.uploader = current_user.username
        else:
            # 标记图片为已删除
            for image in user_images:
                image.is_active = False
        
        # 删除用户
        db.delete(user)
        db.commit()
        
        action = "转移" if transfer_images else "禁用"
        return {
            "success": True,
            "message": f"用户删除成功，相关图片已{action}",
            "affected_images": len(user_images)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除用户失败: {str(e)}")


# 在需要发送邮件的地方，修改为：
@router.post("/{user_id}/send-message")
async def send_message_to_user(
    user_id: int,
    subject: str,
    message: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """向用户发送消息/邮件"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 暂时模拟邮件发送（实际项目中可以集成真实的邮件服务）
        print(f"发送邮件到 {user.email}")
        print(f"主题: {subject}")
        print(f"内容: {message}")
        print(f"发送者: {current_user.username}")
        
        return {
            "success": True,
            "message": "消息发送成功（模拟）"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")

# 类似地修改重置密码函数：
@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    new_password: str,
    send_notification: bool = Query(True, description="是否发送通知邮件"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """重置用户密码"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 重置密码
        from app.auth.password import get_password_hash
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        
        # 模拟发送通知邮件
        if send_notification:
            print(f"密码重置通知邮件发送到 {user.email}")
            print(f"新密码: {new_password}")
        
        return {
            "success": True,
            "message": "密码重置成功" + ("，通知邮件已发送（模拟）" if send_notification else "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"重置密码失败: {str(e)}")


@router.get("/analytics")
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
        
        # 用户活跃度分布
        now = datetime.now()
        activity_distribution = db.query(
            func.case([
                (User.last_login >= now - timedelta(days=1), 'today'),
                (User.last_login >= now - timedelta(days=7), 'week'),
                (User.last_login >= now - timedelta(days=30), 'month'),
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
        
        # 验证状态分布
        verification_stats = db.query(
            User.is_verified,
            func.count(User.id).label('count')
        ).group_by(User.is_verified).all()
        
        # 最活跃用户
        top_uploaders = db.query(
            User.username,
            User.upload_count,
            func.sum(Image.file_size).label('total_size'),
            func.avg(Image.ai_confidence).label('avg_confidence')
        ).join(Image, User.username == Image.uploader).group_by(
            User.username, User.upload_count
        ).order_by(desc(User.upload_count)).limit(10).all()
        
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
                ],
                "verification_stats": [
                    {
                        "verified": bool(stat.is_verified),
                        "count": stat.count
                    }
                    for stat in verification_stats
                ],
                "top_uploaders": [
                    {
                        "username": uploader.username,
                        "upload_count": uploader.upload_count,
                        "total_size": uploader.total_size or 0,
                        "avg_confidence": round(uploader.avg_confidence or 0, 2)
                    }
                    for uploader in top_uploaders
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户分析数据失败: {str(e)}")


@router.get("/export")
async def export_users_data(
    format: str = Query("csv", description="导出格式: csv, json"),
    include_stats: bool = Query(True, description="是否包含统计数据"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """导出用户数据"""
    try:
        users = db.query(User).order_by(desc(User.created_at)).all()
        
        export_data = []
        for user in users:
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name or "",
                "role": user.role.value,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "upload_count": user.upload_count,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else ""
            }
            
            if include_stats:
                # 获取详细统计
                stats = db.query(
                    func.count(Image.id).label('total_uploads'),
                    func.sum(Image.file_size).label('total_size'),
                    func.avg(Image.ai_confidence).label('avg_confidence')
                ).filter(Image.uploader == user.username).first()
                
                user_data.update({
                    "actual_uploads": stats.total_uploads or 0,
                    "total_file_size": stats.total_size or 0,
                    "avg_ai_confidence": round(stats.avg_confidence or 0, 2)
                })
            
            export_data.append(user_data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == "csv":
            output = io.StringIO()
            if export_data:
                writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
                writer.writeheader()
                writer.writerows(export_data)
            
            response = StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8-sig')),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=users_export_{timestamp}.csv"}
            )
            return response
        
        else:  # JSON格式
            response_data = json.dumps(export_data, ensure_ascii=False, indent=2)
            response = StreamingResponse(
                io.BytesIO(response_data.encode()),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=users_export_{timestamp}.json"}
            )
            return response
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出用户数据失败: {str(e)}")


@router.post("/{user_id}/send-message")
async def send_message_to_user(
    user_id: int,
    subject: str,
    message: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """向用户发送消息/邮件"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 发送邮件（如果配置了邮件服务）
        try:
            email_content = f"""
            尊敬的 {user.full_name or user.username}，

            {message}

            ---
            此邮件由管理员 {current_user.username} 发送
            AI姿势参考图库 管理团队
            """
            
            await email_service.send_email(
                to_email=user.email,
                subject=f"[AI姿势参考图库] {subject}",
                content=email_content
            )
            
            return {
                "success": True,
                "message": "消息发送成功"
            }
        except Exception as e:
            # 如果邮件发送失败，可以记录到数据库或日志
            return {
                "success": False,
                "message": f"消息发送失败: {str(e)}"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")


@router.post("/create")
async def create_user(
    username: str,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    role: str = "user",
    is_active: bool = True,
    is_verified: bool = False,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """创建新用户"""
    try:
        # 检查用户名和邮箱是否已存在
        existing_user = db.query(User).filter(
            or_(User.username == username, User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                raise HTTPException(status_code=400, detail="用户名已存在")
            else:
                raise HTTPException(status_code=400, detail="邮箱已存在")
        
        # 验证角色
        try:
            user_role = UserRole(role)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的角色")
        
        # 创建新用户
        from app.auth.password import get_password_hash
        
        new_user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=user_role,
            is_active=is_active,
            is_verified=is_verified,
            created_at=datetime.now()
        )
        
        db.add(new_user)
        db.commit()
        
        return {
            "success": True,
            "message": "用户创建成功",
            "user_id": new_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建用户失败: {str(e)}")


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    new_password: str,
    send_notification: bool = Query(True, description="是否发送通知邮件"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """重置用户密码"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 重置密码
        from app.auth.password import get_password_hash
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        
        # 发送通知邮件
        if send_notification:
            try:
                email_content = f"""
                尊敬的 {user.full_name or user.username}，

                您的账户密码已被管理员重置。

                新密码: {new_password}

                为了您的账户安全，请登录后立即修改密码。

                ---
                AI姿势参考图库 管理团队
                """
                
                await email_service.send_email(
                    to_email=user.email,
                    subject="[AI姿势参考图库] 密码重置通知",
                    content=email_content
                )
            except:
                pass  # 邮件发送失败不影响密码重置
        
        return {
            "success": True,
            "message": "密码重置成功" + ("，通知邮件已发送" if send_notification else "")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"重置密码失败: {str(e)}")