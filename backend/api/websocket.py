"""WebSocket event streaming endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from backend.api.routes.tasks import _build_mutation_tasks
from backend.api.schemas import TaskDetailResponse
from backend.storage import crud
from backend.storage.database import SessionLocal
from backend.storage.schemas import AuditEventSchema

router = APIRouter()


@router.websocket("/api/tasks/{task_id}/stream")
async def stream_task(task_id: str, websocket: WebSocket) -> None:
    await websocket.accept()
    last_version: tuple | None = None

    try:
        while True:
            payload = _build_stream_payload(task_id)
            if payload is None:
                await websocket.send_json({"type": "task.not_found", "task_id": task_id})
                break

            version = _payload_version(payload)
            if version != last_version:
                await websocket.send_json({"type": "task.progress", "data": payload})
                last_version = version
                if payload["task"]["status"] in {"COMPLETED", "FAILED"}:
                    break

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return
    finally:
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close()


def _build_stream_payload(task_id: str) -> dict | None:
    db = SessionLocal()
    try:
        task = crud.get_task(db, task_id)
        if task is None:
            return None

        detail = TaskDetailResponse(
            task=task,
            attack_cases=task.attack_cases,
            mutation_tasks=_build_mutation_tasks(task),
            detection_results=task.detection_results,
            report=task.evaluation_report,
        ).model_dump(mode="json")
        detail["events"] = [
            AuditEventSchema.model_validate(event).model_dump(mode="json")
            for event in crud.list_task_events(db, task_id)
        ]
        return detail
    finally:
        db.close()


def _payload_version(payload: dict) -> tuple:
    task = payload["task"]
    return (
        task["status"],
        task["current_round"],
        task["updated_at"],
        len(payload["attack_cases"]),
        len(payload["mutation_tasks"]),
        len(payload["detection_results"]),
        len(payload["events"]),
        payload["report"]["id"] if payload["report"] else None,
        task.get("error"),
    )
