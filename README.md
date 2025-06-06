# AI姿势参考图库

一个基于 FastAPI 和 GPT-4o 的智能姿势参考图库系统，为摄影师、艺术家和创作者提供高质量的姿势参考图片搜索和管理服务。

## 🌟 项目特色

### 🤖 GPT-4o 智能分析
- 自动识别图片中的姿势、表情、场景、光线和拍摄角度
- 生成精准的标签和描述信息
- 支持自定义分析提示词

### 🔍 自然语言搜索
- 支持中文自然语言描述搜索
- 智能理解搜索意图，精准匹配相关图片
- 多维度搜索：姿势、情绪、风格、场景等

### 📱 小红书数据源集成
- 从小红书导入高质量参考内容
- AI 智能筛选和评分
- 自动质量评估和相关性分析

### 👨‍💼 完整的管理系统
- 用户权限管理（普通用户/版主/管理员）
- 图片批量处理和分析
- 系统监控和性能优化
- 完整的后台管理界面

## 🚀 快速开始

### 环境要求

- Python 3.8+
- MySQL 5.7+ 或 PostgreSQL 12+
- Redis 6.0+（可选，用于缓存）

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/your-username/ai-pose-gallery.git
cd ai-pose-gallery
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库和 OpenAI API 密钥
```

4. **初始化数据库**
```bash
python init_database.py
```

5. **启动服务**
```bash
# 开发环境
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产环境
docker-compose up -d
```

### 环境变量配置

在 `.env` 文件中配置以下变量：

```env
# 数据库配置
DATABASE_URL=mysql+pymysql://username:password@localhost/ai_pose_gallery

# OpenAI 配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o

# JWT 配置
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 上传配置
UPLOAD_DIR=uploads
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=jpg,jpeg,png,webp

# 小红书 API 配置（可选）
XIAOHONGSHU_API_KEY=your_xiaohongshu_api_key
```

## 📁 项目结构

```
ai-pose-gallery/
├── app/                          # 主应用目录
│   ├── api/                      # API 路由
│   │   ├── admin.py             # 管理员接口
│   │   ├── auth.py              # 认证接口
│   │   ├── search.py            # 搜索接口
│   │   ├── upload.py            # 上传接口
│   │   └── xiaohongshu.py       # 小红书数据源接口
│   ├── models/                   # 数据模型
│   │   ├── user.py              # 用户模型
│   │   ├── image.py             # 图片模型
│   │   └── external_source.py   # 外部数据源模型
│   ├── services/                 # 业务逻辑
│   │   ├── ai_service.py        # AI 分析服务
│   │   ├── search_service.py    # 搜索服务
│   │   └── xiaohongshu_service.py # 小红书服务
│   ├── templates/                # 网页模板
│   │   ├── admin.html           # 管理后台
│   │   ├── admin_users.html     # 用户管理
│   │   ├── admin_system.html    # 系统设置
│   │   ├── admin_images.html    # 图片管理
│   │   ├── index.html           # 首页
│   │   ├── detail.html          # 图片详情
│   │   ├── login.html           # 登录页面
│   │   ├── register.html        # 注册页面
│   │   ├── base.html            # 基础模板
│   │   ├── base_admin.html      # 管理后台基础模板
│   │   └── xiaohongshu.html     # 小红书管理页面
│   ├── static/                   # 静态资源
│   ├── config.py                 # 配置文件
│   ├── database.py              # 数据库连接
│   └── main.py                  # 应用入口
├── uploads/                      # 上传文件目录
├── cache/                        # 缓存目录
├── tests/                        # 测试文件
├── data/                         # 数据目录
├── docker-compose.yml           # Docker 编排文件
├── Dockerfile                   # Docker 镜像文件
├── requirements.txt             # Python 依赖
├── init_database.py             # 数据库初始化脚本
├── create_user_tables.py        # 用户表创建脚本
├── create_external_tables.py    # 外部数据源表创建脚本
├── upgrade_user.py              # 用户权限升级脚本
├── test_db_connection.py        # 数据库连接测试
├── test_mysql.py               # MySQL 测试
├── test_openai.py              # OpenAI 测试
└── README.md                    # 项目说明
```

## 🎯 核心功能

### 1. 智能图片分析

使用 GPT-4o 对上传的图片进行深度分析：

```python
# 自动分析示例
from app.services.ai_service import AIService

ai_service = AIService()
result = await ai_service.analyze_image(
    image_path="uploads/example.jpg",
    prompt="分析这张图片中人物的姿势、表情和拍摄角度"
)
```

### 2. 自然语言搜索

支持中文自然语言搜索：

```python
# 搜索示例
from app.services.search_service import SearchService

search_service = SearchService()
results = await search_service.semantic_search(
    query="温柔微笑的女孩侧身坐着",
    limit=20
)
```

### 3. 小红书数据导入

批量导入小红书内容：

```python
# 导入示例
from app.services.xiaohongshu_service import XiaohongshuService

xhs_service = XiaohongshuService()
await xhs_service.batch_import_content(
    keywords=["姿势参考", "人物拍照"],
    limit_per_keyword=20
)
```

## 🔧 管理功能

### 用户管理
- 用户注册/登录系统
- 三级角色权限控制（用户/版主/管理员）
- 批量用户操作和管理
- 用户活动统计和分析
- 发送系统消息和通知

### 图片管理
- 批量上传和AI分析
- 图片编辑和标签管理
- 重新分析和质量评估
- 图片状态管理
- 高级筛选和搜索

### 系统监控
- 实时系统性能监控（CPU、内存、磁盘）
- 数据库状态监控
- 进程管理和系统优化
- 操作日志记录和查看
- 系统清理和维护工具

### 外部数据源管理
- 小红书内容批量导入
- AI智能筛选和评分
- 内容质量评估
- 关键词管理和统计

## 🌐 API 接口

### 认证接口
```
POST /api/auth/register    # 用户注册
POST /api/auth/login       # 用户登录
POST /api/auth/logout      # 用户登出
GET  /api/auth/check       # 检查登录状态
```

### 搜索接口
```
GET  /api/search           # 智能搜索
GET  /api/images/{id}      # 获取图片详情
POST /api/search/semantic  # 语义搜索
```

### 上传接口
```
POST /api/upload           # 上传图片
POST /api/batch-upload     # 批量上传
```

### 管理接口
```
GET  /api/admin/stats      # 系统统计
POST /api/admin/batch/analyze  # 批量分析
GET  /api/admin/users      # 用户管理
GET  /api/admin/images     # 图片管理
GET  /api/admin/system/info      # 系统信息
GET  /api/admin/system/performance # 性能监控
POST /api/admin/system/cleanup   # 系统清理
```

### 小红书数据源接口
```
POST /api/xiaohongshu/import     # 批量导入
GET  /api/xiaohongshu/search     # 实时搜索
GET  /api/xiaohongshu/content    # 获取内容
GET  /api/xiaohongshu/stats      # 统计信息
```

## 🎨 前端特性

### 响应式设计
- 支持桌面端和移动端
- Bootstrap 5.3 现代化界面
- 暗色/亮色主题适配

### 交互体验
- 实时搜索建议和自动完成
- 图片预览和详情展示
- 拖拽上传支持
- 进度条和加载状态提示

### 可视化图表
- 用户活动统计图表（Chart.js）
- 系统性能监控图表
- 数据分析仪表板
- 实时性能指标展示

### 管理界面
- 完整的后台管理系统
- 用户权限管理界面
- 图片批量操作工具
- 系统监控和维护工具

## 🚢 部署指南

### Docker 部署

1. **构建镜像**
```bash
docker build -t ai-pose-gallery .
```

2. **使用 Docker Compose**
```bash
docker-compose up -d
```

### 生产环境部署

1. **使用 Nginx 反向代理**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /static/ {
        alias /path/to/ai-pose-gallery/app/static/;
    }
    
    location /uploads/ {
        alias /path/to/ai-pose-gallery/uploads/;
    }
}
```

2. **使用 Supervisor 进程管理**
```ini
[program:ai-pose-gallery]
command=uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
directory=/path/to/ai-pose-gallery
autostart=true
autorestart=true
user=www-data
```

3. **数据库优化**
```sql
-- MySQL 优化配置
SET GLOBAL innodb_buffer_pool_size = 1G;
SET GLOBAL max_connections = 1000;
```

## 🔒 安全考虑

- JWT 令牌认证和权限控制
- 文件类型和大小限制
- SQL 注入防护（SQLAlchemy ORM）
- XSS 攻击防护
- CSRF 防护
- 跨域请求控制（CORS）
- 密码加密存储
- 上传文件安全检查

## 🧪 测试

运行测试：

```bash
# 测试数据库连接
python test_db_connection.py

# 测试 MySQL 连接
python test_mysql.py

# 测试 OpenAI API
python test_openai.py

# 运行所有测试
python -m pytest tests/ -v

# 测试覆盖率
python -m pytest --cov=app tests/
```

## 📊 性能优化

- 图片压缩和缩略图生成
- 数据库查询优化和索引
- Redis 缓存支持
- 静态资源 CDN 加速
- 异步任务处理
- 图片懒加载
- 分页加载优化

## 🛠️ 维护工具

### 数据库管理脚本
```bash
# 初始化数据库
python init_database.py

# 创建用户表
python create_user_tables.py

# 创建外部数据源表
python create_external_tables.py

# 更新数据库结构
python update_database.py

# 升级用户权限
python upgrade_user.py
```

### 系统检查脚本
```bash
# 检查和修复数据
python check_and_fix.py

# 调试配置
python debug_config.py

# 调试环境冲突
python debug_env_conflict.py
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发规范
- 遵循 PEP 8 Python 代码规范
- 添加必要的类型注解
- 编写单元测试
- 更新相关文档

## 📝 版本历史

- **v1.3.0** (当前) - 完整的管理系统和小红书集成
  - 新增系统性能监控
  - 完善用户权限管理
  - 优化AI分析算法
  - 新增批量操作功能

- **v1.2.0** - 小红书数据源集成
  - 支持小红书内容导入
  - AI智能筛选和评分
  - 实时搜索预览

- **v1.1.0** - 优化搜索算法和UI界面
  - 改进自然语言搜索
  - 响应式界面设计
  - 增强用户体验

- **v1.0.0** - 基础功能完成
  - 图片上传和AI分析
  - 基本搜索功能
  - 用户认证系统

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [OpenAI GPT-4o](https://openai.com/) - 强大的AI分析能力
- [Bootstrap](https://getbootstrap.com/) - 优秀的前端框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包
- [Chart.js](https://www.chartjs.org/) - 漂亮的图表库

## 🔮 未来计划

- [ ] 支持更多外部数据源（小红书、Pinterest等）
- [ ] 增加视频姿势分析功能
- [ ] 实现AI姿势生成功能
- [ ] 增加移动端APP
- [ ] 支持多语言国际化
- [ ] 增加社区分享功能

---

**AI姿势参考图库** - 让创作更智能，让灵感更丰富 🎨✨

> 🌟 如果这个项目对您有帮助，请给我们一个 Star！