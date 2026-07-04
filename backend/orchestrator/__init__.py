"""LangGraph orchestration package."""

from __future__ import annotations


def run_task(*args, **kwargs):
    from backend.orchestrator.main_graph import run_task as _run_task

    return _run_task(*args, **kwargs)


__all__ = ["run_task"]

