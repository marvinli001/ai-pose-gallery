"""
数据库连接和会话管理
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import get_settings

settings = get_settings()

print(f"🔗 准备连接数据库: {settings.mysql_host}:{settings.mysql_port}")
print(f"🔗 数据库URL: {settings.database_url}")

# 创建数据库引擎 - MySQL配置
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """创建所有数据表"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功")
    except Exception as e:
        print(f"❌ 数据库表创建失败: {e}")
        raise


def test_connection():
    """测试数据库连接"""
    try:
        with engine.connect() as connection:
            # 使用 text() 包装SQL语句 - SQLAlchemy 2.0 要求
            result = connection.execute(text("SELECT 1"))
            print("✅ 数据库连接成功")
            return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False