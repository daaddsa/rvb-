export interface TaskModelConfig {
  target_model?: string
  redbench_datasets?: string[]
}

export interface TaskCreateRequest {
  target_agent: string
  risk_types: string[]
  attack_skills: string[]
  attack_count: number
  max_rounds: number
  use_llm: boolean
  model_config: TaskModelConfig
  redbench_datasets: string[]
  matrix_version: string
}

export interface TaskCreateResponse {
  task_id: string
  status: string
  matrix_version: string
}

export interface TaskStartResponse {
  task_id: string
  status: string
}

export interface TaskItem {
  id: string
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | string
  target_agent: string
  risk_types: string[]
  attack_skills: string[]
  attack_count: number
  current_round: number
  max_rounds: number
  use_llm: boolean
  model_config: TaskModelConfig
  red_model?: string | null
  target_model?: string | null
  blue_model?: string | null
  eval_model?: string | null
  matrix_version: string
  created_at: string
  updated_at: string
  error?: string | null
}

export interface AttackCase {
  id: string
  task_id: string
  risk_chain_id?: string | null
  round_no: number
  skill_id?: string | null
  risk_type?: string | null
  target_agent: string
  prompt: string
  expected_violation?: string | null
  severity?: string | null
  model_name?: string | null
  parent_case_id?: string | null
  mutation_strategy?: string | null
  created_at: string
}

export interface MutationTask {
  id: string
  parent_attack_case_id: string
  result_attack_case_id?: string | null
  source_prompt: string
  mutated_prompt?: string | null
  mutation_strategy?: string | null
  failure_stage?: string | null
  failure_reason?: string | null
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | string
  next_round: number
  queued_at: string
  completed_at?: string | null
}

export interface DetectionResult {
  id: string
  task_id: string
  attack_case_id?: string | null
  stage: 'input' | 'tool_call' | 'output' | string
  detector: string
  model_name?: string | null
  detected: boolean
  blocked: boolean
  action: 'allow' | 'block' | 'degrade' | string
  risk_level?: string | null
  risk_type?: string | null
  reason?: string | null
  confidence?: number | null
  raw_output: Record<string, unknown>
  created_at: string
}

export interface AuditEvent {
  id: string
  task_id: string
  attack_case_id?: string | null
  trace_id?: string | null
  event_type: string
  event_topic?: 'FAST_PATH' | 'SLOW_PATH' | string | null
  agent?: string | null
  tool_name?: string | null
  payload: Record<string, unknown>
  allowed?: boolean | null
  risk_level?: string | null
  risk_type?: string | null
  message?: string | null
  created_at: string
}

export interface EvaluationReport {
  id: string
  task_id: string
  total_attacks: number
  successful_attacks: number
  detected_attacks: number
  blocked_attacks: number
  attack_success_rate: number
  detection_rate: number
  block_rate: number
  false_positive_rate: number
  false_negative_rate: number
  risk_coverage: Record<string, unknown>
  redbench_baseline: Record<string, unknown>
  risk_breakdown: Record<string, unknown>
  recommendations?: string | null
  summary?: string | null
  eval_model?: string | null
  created_at: string
}

export interface RedBenchDatasetsResponse {
  datasets: string[]
}

export interface TaskListResponse {
  tasks: TaskItem[]
}

export interface TaskDetailResponse {
  task: TaskItem
  attack_cases: AttackCase[]
  mutation_tasks: MutationTask[]
  detection_results: DetectionResult[]
  report?: EvaluationReport | null
}

export interface TaskEventsResponse {
  events: AuditEvent[]
}

export interface TaskReportResponse {
  report: EvaluationReport | null
  message?: string | null
}

export interface TaskStreamPayload {
  task: TaskItem
  attack_cases: AttackCase[]
  mutation_tasks: MutationTask[]
  detection_results: DetectionResult[]
  events: AuditEvent[]
  report?: EvaluationReport | null
}

export interface TaskStreamMessage {
  type: 'task.progress' | 'task.not_found' | string
  data?: TaskStreamPayload
  task_id?: string
}

export interface TargetAgentOption {
  id: string
  name: string
  description: string
}

export interface StageNode {
  key: string
  label: string
  events: string[]
  action?: 'allow' | 'block' | 'degrade' | 'pending' | string
  active: boolean
  completed: boolean
}
