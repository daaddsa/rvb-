"""红蓝对抗平台后端主入口模块
负责FastAPI应用的创建、启动事件注册、健康检查端点以及路由挂载。
"""

from fastapi import FastAPI

# 导入WebSocket路由（用于任务流推送）和REST API路由（用于任务CRUD）
from backend.api.websocket import router as task_stream_router
from backend.api.routes import tasks_router
# 导入数据库初始化函数
from backend.storage.database import init_db

# 创建FastAPI应用实例，设置API文档标题
app = FastAPI(title="Red Blue Agent Platform")


@app.on_event("startup")
def on_startup() -> None:
    """应用启动时的初始化钩子，调用数据库初始化创建所有表。"""
    init_db()


@app.get("/health")
def health_check() -> dict[str, str]:
    """健康检查端点，用于监控服务是否正常运行。
    返回:
        dict[str, str]: 包含状态字段的JSON字典
    """
    return {"status": "ok"}


# 挂载任务REST API路由（包含/api/tasks前缀下的所有端点）
app.include_router(tasks_router)
# 挂载任务WebSocket实时流路由
app.include_router(task_stream_router)