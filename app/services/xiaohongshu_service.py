"""
小红书API - 简化版本
"""
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/test")
async def test_xiaohongshu():
    """测试小红书API"""
    return {
        "success": True,
        "message": "小红书API模块工作正常",
        "features": [
            "内容搜索",
            "批量导入", 
            "智能分析"
        ]
    }

@router.get("/search")
async def search_xiaohongshu(keyword: str = "姿势参考"):
    """搜索小红书内容（模拟）"""
    return {
        "success": True,
        "keyword": keyword,
        "results": [
            {
                "id": "xhs_001",
                "title": f"{keyword}教程分享",
                "description": f"关于{keyword}的详细教程",
                "author": "示例用户",
                "like_count": 100,
                "comment_count": 20
            }
        ]
    }