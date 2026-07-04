# Debug Session: task-start-timeout

Status: [OPEN]

## Symptom
任务创建后点击执行没有即时反馈，等待较久后任务显示失败。

## Hypotheses
1. 启动接口已经返回 RUNNING，但后台线程内部执行失败，前端只在最终 FAILED 快照才感知变化。
2. WebSocket 连接没有成功建立或没有收到 task.progress，导致前端看起来“没有反应”。
3. 后端流式快照构建或序列化报错，WebSocket 连接断开后前端重连但没有显示明确错误。
4. 攻击执行链路卡在 LLM/模型调用或目标执行阶段，直到超时后失败。
5. 每轮增量落库逻辑在某个字段或重复写入上异常，导致任务最终失败。

## Evidence Plan
- 为任务启动接口、后台执行入口、每轮落库、WebSocket 快照发送、前端点击开始和 WebSocket 收包添加临时调试上报。
- 复现一次完整链路后根据日志判断根因。

## Evidence
- pre-fix: start_task 正常收到请求并返回 RUNNING，后台线程进入 run_task。
- pre-fix: 任务卡在 planning attack chain，随后 JSONDecodeError: Expecting value，说明红方模型返回内容不是纯 JSON 数组。
- post-fix-1: 攻击链可完成规划，第一轮攻击可落库，但报告生成阶段调用 eval_model=external-api 走 Ollama 后返回 HTTP 404，任务最终 FAILED。
- post-fix-2: 评估报告生成对 LLMClientError 降级为本地摘要后，接口复验任务 task_16a7da9a352e 最终 COMPLETED，current_round=1，attack_cases=1，detection_results=1，report 存在，error=null。

## Fixes Applied
- RedBench 任务优先使用本地攻击模板生成攻击链，避免依赖红方模型必须返回 JSON 数组。
- 评估总结 LLM 调用失败时降级为本地 build_summary + build_recommendations，避免 external-api 未配置时任务失败。

## Timeline
- Initialized debugging session.
- Added temporary instrumentation to backend routes, orchestrator, websocket, and frontend store.
- Reproduced failure and collected runtime evidence.
- Applied evidence-based fixes and verified backend task chain completes successfully.

## Cleanup
- Pending user confirmation. Debug instrumentation and debug artifacts must be removed after user confirms the issue is fixed.
