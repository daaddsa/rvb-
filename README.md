# AI Agent 实战对抗平台：OWASP ASI 2026 红蓝演练系统

基于 LangGraph 构建的 AI Agent 红蓝对抗演练平台，用于评估大语言模型智能体在面对 OWASP ASI 威胁时的安全防护能力。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn |
| 工作流引擎 | LangGraph |
| 数据库 | SQLite + SQLAlchemy |
| 前端 | Vue 3 + TypeScript + Vite |
| LLM | Ollama 本地模型 + DeepSeek API |

## 功能概述

- **红队攻击生成**：基于 RedBench 数据集，自动生成对抗性攻击用例
- **蓝队检测防御**：规则引擎 + 模型检测双路径，实时监控输入/输出风险
- **目标智能体模拟**：模拟金融、客服等业务场景的 AI Agent
- **评估报告**：自动生成攻击成功率、检测率、阻断率等评估指标

## 前置条件

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com/)（需拉取模型：`dolphin-mistral`、`qwen3:1.7b`、`gemma2:2b`）
- DeepSeek API Key（用于评估模型）

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/daaddsa/rvb-.git
cd rvb-
```

### 2. 启动后端

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 4. 访问

- 前端：`http://localhost:5173`
- 后端 API：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`

## 配置

通过环境变量覆盖默认配置：

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./red_blue_platform.db` | 数据库连接 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 地址 |
| `RED_MODEL` | `dolphin-mistral:latest` | 红队模型 |
| `BLUE_MODEL` | `gemma2:2b` | 蓝队模型 |
| `TARGET_MODEL` | `qwen3:1.7b` | 目标模型 |
| `EVAL_MODEL` | `deepseek-v4-flash` | 评估模型 |
| `EXTERNAL_EVAL_API_KEY` | - | DeepSeek API Key |

## 项目结构

```
├── backend/
│   ├── api/            # REST API 和 WebSocket
│   ├── blueteam/       # 蓝队：检测器、审计器、策略执行
│   ├── redteam/        # 红队：攻击生成、攻击执行
│   ├── orchestrator/   # LangGraph 编排引擎
│   ├── targets/        # 目标智能体模拟
│   ├── storage/        # 数据库模型和 CRUD
│   ├── evaluation/     # 评估指标和报告生成
│   ├── eventbus/       # 事件总线（快/慢路径）
│   ├── llm/            # LLM 客户端和提示词
│   ├── observability/  # 日志、审计、追踪
│   └── config/         # 配置文件和攻击矩阵
├── frontend/           # Vue 3 前端
├── redbench/           # 攻击数据集（RedBench）
└── requirements.txt    # Python 依赖
```