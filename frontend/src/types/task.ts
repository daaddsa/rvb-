/**
 * types/task.ts — 任务相关 TypeScript 类型定义文件
 * 定义红蓝对抗平台中任务创建、执行、攻击案例、变异任务、检测结果、审计事件、
 * 评估报告等核心数据结构的接口类型，确保前后端数据交互的类型安全。
 */

// ---------- 任务模型配置 ----------

/** 任务模型配置 */
export interface TaskModelConfig {
  /** 目标模型名称（可选） */
  target_model?: string
  /** 红队基准数据集列表（可选） */
  redbench_datasets?: string[]
}

// ---------- 任务创建与启动 ----------

/** 创建任务的请求参数 */
export interface TaskCreateRequest {
  /** 目标智能体名称 */
  target_agent: string
  /** 风险类型列表（如 prompt_injection, jailbreak 等） */
  risk_types: string[]
  /** 攻击技能列表 */
  attack_skills: string[]
  /** 攻击次数 */
  attack_count: number
  /** 最大攻击轮数 */
  max_rounds: number
  /** 是否使用 LLM（大语言模型） */
  use_llm: boolean
  /** 模型配置 */
  model_config: TaskModelConfig
  /** 红队基准数据集列表 */
  redbench_datasets: string[]
  /** 矩阵版本号 */
  matrix_version: string
}

/** 创建任务的响应数据 */
export interface TaskCreateResponse {
  /** 创建成功后返回的任务 ID */
  task_id: string
  /** 任务状态 */
  status: string
  /** 矩阵版本号 */
  matrix_version: string
}

/** 启动任务的响应数据 */
export interface TaskStartResponse {
  /** 任务 ID */
  task_id: string
  /** 任务启动后的状态 */
  status: string
}

// ---------- 任务列表项 ----------

/** 任务列表中的单个任务项 */
export interface TaskItem {
  /** 任务唯一标识 */
  id: string
  /** 任务状态：PENDING（待执行）| RUNNING（运行中）| COMPLETED（已完成）| FAILED（失败） */
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | string
  /** 目标智能体名称 */
  target_agent: string
  /** 风险类型列表 */
  risk_types: string[]
  /** 攻击技能列表 */
  attack_skills: string[]
  /** 攻击次数 */
  attack_count: number
  /** 当前执行轮数 */
  current_round: number
  /** 最大执行轮数 */
  max_rounds: number
  /** 是否使用 LLM */
  use_llm: boolean
  /** 模型配置 */
  model_config: TaskModelConfig
  /** 红队模型名称（可选） */
  red_model?: string | null
  /** 目标模型名称（可选） */
  target_model?: string | null
  /** 蓝队模型名称（可选） */
  blue_model?: string | null
  /** 评估模型名称（可选） */
  eval_model?: string | null
  /** 矩阵版本号 */
  matrix_version: string
  /** 任务创建时间 */
  created_at: string
  /** 任务最后更新时间 */
  updated_at: string
  /** 任务错误信息（可选，失败时填充） */
  error?: string | null
}

// ---------- 攻击案例 ----------

/** 攻击案例（Attack Case） */
export interface AttackCase {
  /** 案例唯一标识 */
  id: string
  /** 所属任务 ID */
  task_id: string
  /** 风险链路 ID（可选） */
  risk_chain_id?: string | null
  /** 轮次编号 */
  round_no: number
  /** 攻击技能 ID（可选） */
  skill_id?: string | null
  /** 风险类型（可选） */
  risk_type?: string | null
  /** 目标智能体名称 */
  target_agent: string
  /** 攻击提示词（prompt） */
  prompt: string
  /** 预期违规行为描述（可选） */
  expected_violation?: string | null
  /** 严重程度（可选） */
  severity?: string | null
  /** 模型名称（可选） */
  model_name?: string | null
  /** 父案例 ID（可选，用于变异链追踪） */
  parent_case_id?: string | null
  /** 变异策略（可选） */
  mutation_strategy?: string | null
  /** 创建时间 */
  created_at: string
}

// ---------- 变异任务 ----------

/** 变异任务（Mutation Task）—— 对攻击提示词进行变异优化 */
export interface MutationTask {
  /** 变异任务唯一标识 */
  id: string
  /** 父攻击案例 ID */
  parent_attack_case_id: string
  /** 变异后生成的攻击案例 ID（可选，变异完成后填充） */
  result_attack_case_id?: string | null
  /** 原始提示词 */
  source_prompt: string
  /** 变异后的提示词（可选） */
  mutated_prompt?: string | null
  /** 使用的变异策略（可选） */
  mutation_strategy?: string | null
  /** 失败阶段（可选，如失败时记录失败发生的阶段） */
  failure_stage?: string | null
  /** 失败原因（可选） */
  failure_reason?: string | null
  /** 变异任务状态 */
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | string
  /** 下一轮编号 */
  next_round: number
  /** 入队时间 */
  queued_at: string
  /** 完成时间（可选） */
  completed_at?: string | null
}

// ---------- 检测结果 ----------

/** 检测结果（Detection Result）—— 蓝队检测的输出 */
export interface DetectionResult {
  /** 检测结果唯一标识 */
  id: string
  /** 所属任务 ID */
  task_id: string
  /** 关联的攻击案例 ID（可选） */
  attack_case_id?: string | null
  /** 检测阶段：input（输入）| tool_call（工具调用）| output（输出） */
  stage: 'input' | 'tool_call' | 'output' | string
  /** 检测器名称 */
  detector: string
  /** 检测模型名称（可选） */
  model_name?: string | null
  /** 是否检测到攻击 */
  detected: boolean
  /** 是否被拦截 */
  blocked: boolean
  /** 处理动作：allow（放行）| block（拦截）| degrade（降级） */
  action: 'allow' | 'block' | 'degrade' | string
  /** 风险等级（可选） */
  risk_level?: string | null
  /** 风险类型（可选） */
  risk_type?: string | null
  /** 检测原因说明（可选） */
  reason?: string | null
  /** 置信度（可选，0~1） */
  confidence?: number | null
  /** 检测器原始输出（JSON 对象） */
  raw_output: Record<string, unknown>
  /** 创建时间 */
  created_at: string
}

// ---------- 审计事件 ----------

/** 审计事件（Audit Event）—— 记录攻击过程中的每一步操作 */
export interface AuditEvent {
  /** 事件唯一标识 */
  id: string
  /** 所属任务 ID */
  task_id: string
  /** 关联的攻击案例 ID（可选） */
  attack_case_id?: string | null
  /** 追踪 ID（可选，用于链路追踪） */
  trace_id?: string | null
  /** 事件类型 */
  event_type: string
  /** 事件通道：FAST_PATH（快速通道）| SLOW_PATH（慢速通道） */
  event_topic?: 'FAST_PATH' | 'SLOW_PATH' | string | null
  /** 智能体名称（可选） */
  agent?: string | null
  /** 工具名称（可选） */
  tool_name?: string | null
  /** 事件负载数据（JSON 对象） */
  payload: Record<string, unknown>
  /** 是否被允许（可选） */
  allowed?: boolean | null
  /** 风险等级（可选） */
  risk_level?: string | null
  /** 风险类型（可选） */
  risk_type?: string | null
  /** 附加消息（可选） */
  message?: string | null
  /** 创建时间 */
  created_at: string
}

// ---------- 评估报告 ----------

/** 评估报告（Evaluation Report）—— 任务完成后的综合评估结果 */
export interface EvaluationReport {
  /** 报告唯一标识 */
  id: string
  /** 所属任务 ID */
  task_id: string
  /** 总攻击次数 */
  total_attacks: number
  /** 成功攻击次数 */
  successful_attacks: number
  /** 检测到的攻击次数 */
  detected_attacks: number
  /** 被拦截的攻击次数 */
  blocked_attacks: number
  /** 攻击成功率（百分比） */
  attack_success_rate: number
  /** 检测率（百分比） */
  detection_rate: number
  /** 拦截率（百分比） */
  block_rate: number
  /** 误报率（百分比） */
  false_positive_rate: number
  /** 漏报率（百分比） */
  false_negative_rate: number
  /** 风险覆盖率（JSON 对象） */
  risk_coverage: Record<string, unknown>
  /** 红队基准基线数据（JSON 对象） */
  redbench_baseline: Record<string, unknown>
  /** 风险分类明细（JSON 对象） */
  risk_breakdown: Record<string, unknown>
  /** 改进建议（可选，Markdown 格式） */
  recommendations?: string | null
  /** 摘要（可选，Markdown 格式） */
  summary?: string | null
  /** 评估模型名称（可选） */
  eval_model?: string | null
  /** 创建时间 */
  created_at: string
}

// ---------- API 响应类型 ----------

/** 红队基准数据集列表响应 */
export interface RedBenchDatasetsResponse {
  /** 数据集名称列表 */
  datasets: string[]
}

/** 任务列表响应 */
export interface TaskListResponse {
  /** 任务列表 */
  tasks: TaskItem[]
}

/** 任务详情响应 */
export interface TaskDetailResponse {
  /** 任务基本信息 */
  task: TaskItem
  /** 攻击案例列表 */
  attack_cases: AttackCase[]
  /** 变异任务列表 */
  mutation_tasks: MutationTask[]
  /** 检测结果列表 */
  detection_results: DetectionResult[]
  /** 评估报告（可选，任务完成后生成） */
  report?: EvaluationReport | null
}

/** 任务事件列表响应 */
export interface TaskEventsResponse {
  /** 审计事件列表 */
  events: AuditEvent[]
}

/** 任务报告响应 */
export interface TaskReportResponse {
  /** 评估报告（可选，任务未完成时为 null） */
  report: EvaluationReport | null
  /** 附加消息（可选） */
  message?: string | null
}

// ---------- WebSocket 实时推送类型 ----------

/** WebSocket 流推送的任务快照数据 */
export interface TaskStreamPayload {
  /** 任务基本信息 */
  task: TaskItem
  /** 攻击案例列表 */
  attack_cases: AttackCase[]
  /** 变异任务列表 */
  mutation_tasks: MutationTask[]
  /** 检测结果列表 */
  detection_results: DetectionResult[]
  /** 审计事件列表 */
  events: AuditEvent[]
  /** 评估报告（可选） */
  report?: EvaluationReport | null
}

/** WebSocket 流推送的消息结构 */
export interface TaskStreamMessage {
  /** 消息类型：task.progress（任务进度更新）| task.not_found（任务不存在） */
  type: 'task.progress' | 'task.not_found' | string
  /** 消息负载数据（进度更新时包含任务快照） */
  data?: TaskStreamPayload
  /** 任务 ID（可选） */
  task_id?: string
}

// ---------- 前端 UI 辅助类型 ----------

/** 目标智能体选项（下拉选择） */
export interface TargetAgentOption {
  /** 智能体唯一标识 */
  id: string
  /** 智能体显示名称 */
  name: string
  /** 智能体描述 */
  description: string
}

/** 阶段节点（用于攻击流程可视化） */
export interface StageNode {
  /** 节点唯一标识 */
  key: string
  /** 节点显示标签 */
  label: string
  /** 关联的事件类型列表 */
  events: string[]
  /** 处理动作：allow（放行）| block（拦截）| degrade（降级）| pending（等待中） */
  action?: 'allow' | 'block' | 'degrade' | 'pending' | string
  /** 是否为当前活跃节点 */
  active: boolean
  /** 是否已完成 */
  completed: boolean
}