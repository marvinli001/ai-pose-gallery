"""
更新main.py，修复管理员权限检查
"""
import os

# 读取原文件
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复管理员页面路由
new_admin_route = '''@app.get("/admin", response_class=HTMLResponse)
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
    })'''

# 查找并替换管理员路由
if '@app.get("/admin"' in content:
    # 找到管理员路由的开始和结束
    start = content.find('@app.get("/admin"')
    end = content.find('\n\n@app.get', start + 1)
    if end == -1:
        end = content.find('\n\n\nif __name__', start)
    
    old_route = content[start:end]
    content = content.replace(old_route, new_admin_route)

# 写回文件
with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 已修复管理员权限检查")