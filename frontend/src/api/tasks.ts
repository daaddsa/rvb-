/**
 * api/tasks.ts — 任务相关 API 接口层
 * 封装所有与后端任务相关的 HTTP 请求和 WebSocket 连接。
 * 使用 axios 作为 HTTP 客户端，WebSocket 用于实时任务进度推送。
 * 所有接口返回类型明确的 TypeScript 响应数据。
 */

import axios from 'axios'
import type {
  RedBenchDatasetsResponse,
  TaskCreateRequest,
  TaskCreateResponse,
  TaskDetailResponse,
  TaskEventsResponse,
  TaskListResponse,
  TaskReportResponse,
  TaskStartResponse,
} from '@/types/task'

/**
 * 创建 axios 实例，配置全局默认参数
 * baseURL: 从环境变量 VITE_API_BASE_URL 读取，默认为空（使用相对路径，由 Vite proxy 转发）
 * timeout: 超时时间 180 秒（3 分钟），因为任务执行可能耗时较长
 */
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 180000,
})

/**
 * 获取红队基准数据集列表
 * 调用 GET /api/tasks/redbench/datasets 接口
 *
 * @returns 数据集名称列表的响应对象
 */
export async function getRedbenchDatasets() {
  const { data } = await apiClient.get<RedBenchDatasetsResponse>('/api/tasks/redbench/datasets')
  return data
}

/**
 * 创建新任务
 * 调用 POST /api/tasks 接口，传入任务创建参数
 *
 * @param payload - 任务创建请求参数（目标智能体、风险类型、攻击技能等）
 * @returns 创建成功的响应（包含任务 ID、状态、矩阵版本）
 */
export async function createTask(payload: TaskCreateRequest) {
  const { data } = await apiClient.post<TaskCreateResponse>('/api/tasks', payload)
  return data
}

/**
 * 启动指定任务
 * 调用 POST /api/tasks/{taskId}/start 接口
 *
 * @param taskId - 要启动的任务 ID
 * @returns 启动后的任务状态响应
 */
export async function startTask(taskId: string) {
  const { data } = await apiClient.post<TaskStartResponse>(`/api/tasks/${taskId}/start`)
  return data
}

/**
 * 获取所有任务列表
 * 调用 GET /api/tasks 接口
 *
 * @returns 任务列表响应
 */
export async function getTasks() {
  const { data } = await apiClient.get<TaskListResponse>('/api/tasks')
  return data
}

/**
 * 获取指定任务的详细信息
 * 调用 GET /api/tasks/{taskId} 接口
 *
 * @param taskId - 任务 ID
 * @returns 任务详情（含攻击案例、变异任务、检测结果、评估报告）
 */
export async function getTaskDetail(taskId: string) {
  const { data } = await apiClient.get<TaskDetailResponse>(`/api/tasks/${taskId}`)
  return data
}

/**
 * 获取任务的审计事件列表
 * 调用 GET /api/tasks/{taskId}/events 接口
 *
 * @param taskId - 任务 ID
 * @returns 审计事件列表响应
 */
export async function getTaskEvents(taskId: string) {
  const { data } = await apiClient.get<TaskEventsResponse>(`/api/tasks/${taskId}/events`)
  return data
}

/**
 * 获取任务的评估报告
 * 调用 GET /api/tasks/{taskId}/report 接口
 *
 * @param taskId - 任务 ID
 * @returns 评估报告响应（任务未完成时 report 为 null）
 */
export async function getTaskReport(taskId: string) {
  const { data } = await apiClient.get<TaskReportResponse>(`/api/tasks/${taskId}/report`)
  return data
}

/**
 * 打开任务实时推送 WebSocket 连接
 * 用于接收任务执行过程中的实时进度更新（task.progress 消息）
 *
 * @param taskId - 任务 ID
 * @returns WebSocket 实例
 */
export function openTaskStream(taskId: string) {
  return new WebSocket(buildTaskStreamUrl(taskId))
}

/**
 * 构建 WebSocket 连接 URL
 * 根据环境变量 VITE_API_BASE_URL 或当前页面协议自动推断 WebSocket 地址
 * 规则：
 *   - 如果配置了 VITE_API_BASE_URL → 解析其协议和主机，替换为 ws/wss
 *   - 否则 → 使用当前页面的协议和主机，拼接 /api/tasks/{taskId}/stream
 *
 * @param taskId - 任务 ID
 * @returns 完整的 WebSocket URL
 */
function buildTaskStreamUrl(taskId: string) {
  // 检查是否配置了自定义 API 基础 URL
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL
  if (configuredBaseUrl) {
    // 解析配置的 URL，将 http/https 协议替换为 ws/wss
    const url = new URL(configuredBaseUrl, window.location.origin)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${url.origin}/api/tasks/${taskId}/stream`
  }

  // 未配置自定义 URL：使用当前页面的协议和主机
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/tasks/${taskId}/stream`
}