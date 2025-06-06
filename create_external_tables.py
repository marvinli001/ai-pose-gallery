"""
创建外部数据源相关表
"""
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models.external_source import ExternalContent, ExternalImage

def create_external_tables():
    """创建外部数据源表"""
    print("🔄 创建外部数据源表...")
    
    try:
        # 创建表
        from app.database import Base
        Base.metadata.create_all(bind=engine, tables=[
            ExternalContent.__table__,
            ExternalImage.__table__
        ])
        
        print("✅ 外部数据源表创建成功")
        
        # 显示表信息
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT TABLE_NAME, TABLE_COMMENT 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME IN ('external_contents', 'external_images')
            """))
            
            print("\n📋 已创建的表:")
            for row in result:
                print(f"   {row[0]}: {row[1]}")
                
    except Exception as e:
        print(f"❌ 创建表失败: {e}")

if __name__ == "__main__":
    create_external_tables()