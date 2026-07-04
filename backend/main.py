from fastapi import FastAPI

from backend.api.websocket import router as task_stream_router
from backend.api.routes import tasks_router
from backend.storage.database import init_db

app = FastAPI(title="Red Blue Agent Platform")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(tasks_router)
app.include_router(task_stream_router)
