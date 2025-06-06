"""
FastAPI主应用 - 添加小红书数据源支持
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import get_settings, create_directories
from app.database import create_tables, test_connection
from app.api import upload, search, admin, xiaohongshu


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("🚀 启动AI姿势参考图库...")
    create_directories()
    
    if test_connection():
        create_tables()
        print("✅ 应用启动完成")
    else:
        print("❌ 数据库连接失败，请检查配置")
    
    yield
    
    # 关闭时执行
    print("👋 应用关闭")


# 创建FastAPI应用
app = FastAPI(
    title="AI姿势参考图库",
    description="为插画师、摄影师、设计师提供智能姿势参考图库，支持小红书数据源",
    version="1.0.0",
    lifespan=lifespan
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 模板配置
templates = Jinja2Templates(directory="app/templates")

# 注册API路由
app.include_router(upload.router, prefix="/api", tags=["上传"])
app.include_router(search.router, prefix="/api", tags=["搜索"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理"])
app.include_router(xiaohongshu.router, prefix="/api/xiaohongshu", tags=["小红书"])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """上传页面"""
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """管理页面"""
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/xiaohongshu", response_class=HTMLResponse)
async def xiaohongshu_page(request: Request):
    """小红书数据源管理页面"""
    return templates.TemplateResponse("xiaohongshu.html", {"request": request})


@app.get("/image/{image_id}", response_class=HTMLResponse)
async def image_detail(request: Request, image_id: int):
    """图片详情页"""
    return templates.TemplateResponse("detail.html", {
        "request": request, 
        "image_id": image_id
    })


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "database": test_connection()}


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )