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

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 180000,
})

export async function getRedbenchDatasets() {
  const { data } = await apiClient.get<RedBenchDatasetsResponse>('/api/tasks/redbench/datasets')
  return data
}

export async function createTask(payload: TaskCreateRequest) {
  const { data } = await apiClient.post<TaskCreateResponse>('/api/tasks', payload)
  return data
}

export async function startTask(taskId: string) {
  const { data } = await apiClient.post<TaskStartResponse>(`/api/tasks/${taskId}/start`)
  return data
}

export async function getTasks() {
  const { data } = await apiClient.get<TaskListResponse>('/api/tasks')
  return data
}

export async function getTaskDetail(taskId: string) {
  const { data } = await apiClient.get<TaskDetailResponse>(`/api/tasks/${taskId}`)
  return data
}

export async function getTaskEvents(taskId: string) {
  const { data } = await apiClient.get<TaskEventsResponse>(`/api/tasks/${taskId}/events`)
  return data
}

export async function getTaskReport(taskId: string) {
  const { data } = await apiClient.get<TaskReportResponse>(`/api/tasks/${taskId}/report`)
  return data
}

export function openTaskStream(taskId: string) {
  return new WebSocket(buildTaskStreamUrl(taskId))
}

function buildTaskStreamUrl(taskId: string) {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL
  if (configuredBaseUrl) {
    const url = new URL(configuredBaseUrl, window.location.origin)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${url.origin}/api/tasks/${taskId}/stream`
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/tasks/${taskId}/stream`
}
