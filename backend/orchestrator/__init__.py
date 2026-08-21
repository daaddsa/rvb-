"""LangGraph orchestration package.
LangGraph 编排引擎包，作为红蓝对抗平台的核心调度入口。
"""

from __future__ import annotations


def run_task(*args, **kwargs):
    """执行红蓝对抗任务的总入口函数，委托给 main_graph 中的 run_task 实现。
    参数透传到底层任务执行器。
    """
    # 延迟导入避免循环依赖
    from backend.orchestrator.main_graph import run_task as _run_task

    return _run_task(*args, **kwargs)


__all__ = ["run_task"]