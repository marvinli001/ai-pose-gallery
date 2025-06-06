"""
管理员API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter()


@router.get("/stats")
async def get_admin_stats(db: Session = Depends(get_db)):
    """获取管理员统计信息"""
    from app.models.image import Image, Tag, ImageTag
    
    try:
        stats = {
            "total_images": db.query(Image).count(),
            "active_images": db.query(Image).filter(Image.is_active == True).count(),
            "total_tags": db.query(Tag).count(),
            "active_tags": db.query(Tag).filter(Tag.is_active == True).count(),
            "total_connections": db.query(ImageTag).count()
        }
        
        return {"success": True, "data": stats}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")