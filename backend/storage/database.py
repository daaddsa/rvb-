"""数据库连接管理模块
负责SQLAlchemy引擎创建、会话工厂配置、数据库初始化以及请求级会话的依赖注入。
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import get_settings
from backend.storage.models import Base

# 获取配置实例
settings = get_settings()
# 创建SQLAlchemy引擎，SQLite需要check_same_thread=False以支持多线程访问
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
# 创建会话工厂，关闭自动提交和自动刷新（由业务代码显式控制）
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """初始化数据库，创建所有ORM模型对应的表。
    在应用启动时调用，仅在表不存在时创建（CREATE TABLE IF NOT EXISTS语义）。
    """
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI依赖注入函数：为每个请求提供独立的数据库会话。
    使用生成器模式确保请求结束后自动关闭会话。
    用法:
        @app.get("/something")
        def handler(db: Session = Depends(get_db)):
            ...
    返回:
        Generator[Session]: 数据库会话生成器
    """
    # 为当前请求创建新的会话
    db = SessionLocal()
    try:
        # 将会话yield给路由处理函数使用
        yield db
    finally:
        # 请求结束后关闭会话，归还连接
        db.close()