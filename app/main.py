"""
FastAPI主应用 - 添加用户认证支持
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import get_settings, create_directories
from app.database import create_tables, test_connection
from app.api import upload, search, admin, auth
from app.auth.dependencies import optional_user
from app.models.user import User

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
    description="为插画师、摄影师、设计师提供智能姿势参考图库，支持GPT-4o和用户系统",
    version="1.0.0",
    lifespan=lifespan
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 模板配置
templates = Jinja2Templates(directory="app/templates")

# 注册API路由 - 按照逻辑顺序注册
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(upload.router, prefix="/api", tags=["上传"])
app.include_router(search.router, prefix="/api", tags=["搜索"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理"])

# 导入并注册管理员专用路由
try:
    from app.api import admin_images
    app.include_router(admin_images.router, prefix="/api/admin/images", tags=["admin-images"])
    print("✅ 图片管理API路由注册成功")
except ImportError as e:
    print(f"⚠️ 图片管理API路由注册失败: {e}")

try:
    from app.api import admin_users
    app.include_router(admin_users.router, prefix="/api/admin/users", tags=["admin-users"])
    print("✅ 用户管理API路由注册成功")
except ImportError as e:
    print(f"⚠️ 用户管理API路由注册失败: {e}")

try:
    from app.api import admin_system
    app.include_router(admin_system.router, prefix="/api/admin/system", tags=["admin-system"])
    print("✅ 系统管理API路由注册成功")
except ImportError as e:
    print(f"⚠️ 系统管理API路由注册失败: {e}")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, current_user: User = Depends(optional_user)):
    """首页"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_user": current_user
    })


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, current_user: User = Depends(optional_user)):
    """上传页面"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "current_user": current_user
    })


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """注册页面"""
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, current_user: User = Depends(optional_user)):
    """管理页面"""
    # 检查用户是否登录
    if not current_user:
        return RedirectResponse(url="/login?redirect=/admin", status_code=302)
    
    # 检查是否有管理员权限
    if current_user.role.value not in ['admin', 'moderator']:
        # 普通用户访问管理页面，重定向到首页并提示
        return RedirectResponse(url="/?error=access_denied", status_code=302)
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "current_user": current_user
    })


@app.get("/admin/images", response_class=HTMLResponse)
async def admin_images_page(request: Request, current_user: User = Depends(optional_user)):
    """图片管理页面"""
    # 检查用户是否登录
    if not current_user:
        return RedirectResponse(url="/login?redirect=/admin/images", status_code=302)
    
    # 检查是否有管理员权限
    if current_user.role.value not in ['admin', 'moderator']:
        return RedirectResponse(url="/?error=access_denied", status_code=302)
    
    return templates.TemplateResponse("admin_images.html", {
        "request": request,
        "current_user": current_user
    })


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request, current_user: User = Depends(optional_user)):
    """用户管理页面"""
    # 检查用户是否登录
    if not current_user:
        return RedirectResponse(url="/login?redirect=/admin/users", status_code=302)
    
    # 检查是否有管理员权限
    if current_user.role.value not in ['admin', 'moderator']:
        return RedirectResponse(url="/?error=access_denied", status_code=302)
    
    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "current_user": current_user
    })


@app.get("/admin/system", response_class=HTMLResponse)
async def admin_system_page(request: Request, current_user: User = Depends(optional_user)):
    """系统设置页面"""
    # 检查用户是否登录
    if not current_user:
        return RedirectResponse(url="/login?redirect=/admin/system", status_code=302)
    
    # 检查是否有管理员权限（系统设置只允许管理员访问）
    if current_user.role.value != 'admin':
        return RedirectResponse(url="/?error=access_denied", status_code=302)
    
    return templates.TemplateResponse("admin_system.html", {
        "request": request,
        "current_user": current_user
    })


@app.get("/image/{image_id}", response_class=HTMLResponse)
async def image_detail(request: Request, image_id: int, current_user: User = Depends(optional_user)):
    """图片详情页"""
    return templates.TemplateResponse("detail.html", {
        "request": request, 
        "image_id": image_id,
        "current_user": current_user
    })


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, current_user: User = Depends(optional_user)):
    """用户资料页"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "current_user": current_user
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