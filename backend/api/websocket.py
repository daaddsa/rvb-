"""WebSocket事件流推送端点
通过WebSocket向前端实时推送任务执行进度，包括攻击用例、变异任务、检测结果和审计事件。
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

# 导入变异任务构建函数，用于在流负载中计算变异任务
from backend.api.routes.tasks import _build_mutation_tasks
from backend.api.schemas import TaskDetailResponse
from backend.storage import crud
from backend.storage.database import SessionLocal
from backend.storage.schemas import AuditEventSchema

router = APIRouter()


@router.websocket("/api/tasks/{task_id}/stream")
async def stream_task(task_id: str, websocket: WebSocket) -> None:
    """WebSocket端点：实时推送任务执行进度。
    每0.5秒轮询一次数据库，仅当数据版本变化时才推送更新。
    任务完成或失败后自动断开连接。
    参数:
        task_id: 要监听的任务ID
        websocket: WebSocket连接对象
    """
    # 接受WebSocket连接
    await websocket.accept()
    # 记录上次推送的数据版本，用于检测变化
    last_version: tuple | None = None

    try:
        # 持续轮询直到任务结束或客户端断开
        while True:
            # 构建当前任务的数据负载
            payload = _build_stream_payload(task_id)
            # 如果任务不存在，通知客户端并退出循环
            if payload is None:
                await websocket.send_json({"type": "task.not_found", "task_id": task_id})
                break

            # 计算当前数据版本，与上次版本比较
            version = _payload_version(payload)
            # 仅当数据有变化时才推送，避免无意义的网络传输
            if version != last_version:
                await websocket.send_json({"type": "task.progress", "data": payload})
                last_version = version
                # 如果任务已完成或失败，退出循环
                if payload["task"]["status"] in {"COMPLETED", "FAILED"}:
                    break

            # 等待0.5秒后再次轮询
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        # 客户端主动断开连接，正常退出
        return
    finally:
        # 如果连接尚未断开，主动关闭WebSocket
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close()


def _build_stream_payload(task_id: str) -> dict | None:
    """构建WebSocket推送的数据负载。
    从数据库查询任务及其关联数据，组装为完整字典。
    参数:
        task_id: 任务ID
    返回:
        dict | None: 包含任务详情的字典，若任务不存在则返回None
    """
    # 创建独立的数据库会话（WebSocket协程不在请求上下文中）
    db = SessionLocal()
    try:
        task = crud.get_task(db, task_id)
        # 任务不存在时返回None
        if task is None:
            return None

        # 构建任务详情响应，并序列化为字典
        detail = TaskDetailResponse(
            task=task,
            attack_cases=task.attack_cases,
            mutation_tasks=_build_mutation_tasks(task),
            detection_results=task.detection_results,
            report=task.evaluation_report,
        ).model_dump(mode="json")
        # 附加审计事件列表
        detail["events"] = [
            AuditEventSchema.model_validate(event).model_dump(mode="json")
            for event in crud.list_task_events(db, task_id)
        ]
        return detail
    finally:
        # 确保数据库会话被关闭
        db.close()


def _payload_version(payload: dict) -> tuple:
    """计算数据负载的版本元组，用于检测数据变化。
    包含任务状态、轮次、更新时间、各列表长度、报告ID和错误信息。
    参数:
        payload: 数据负载字典
    返回:
        tuple: 可哈希的版本元组
    """
    task = payload["task"]
    return (
        task["status"],           # 任务状态
        task["current_round"],    # 当前轮次
        task["updated_at"],       # 最后更新时间
        len(payload["attack_cases"]),      # 攻击用例数量
        len(payload["mutation_tasks"]),    # 变异任务数量
        len(payload["detection_results"]), # 检测结果数量
        len(payload["events"]),            # 审计事件数量
        payload["report"]["id"] if payload["report"] else None,  # 报告ID（若存在）
        task.get("error"),                 # 错误信息
    )