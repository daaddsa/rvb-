import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  createTask,
  getRedbenchDatasets,
  getTaskDetail,
  getTaskEvents,
  getTaskReport,
  getTasks,
  openTaskStream,
  startTask,
} from '@/api/tasks'
import type {
  AuditEvent,
  EvaluationReport,
  MutationTask,
  TaskCreateRequest,
  TaskDetailResponse,
  TaskItem,
  TaskStreamMessage,
  TaskStreamPayload,
} from '@/types/task'

const FINISHED_STATUS = new Set(['COMPLETED', 'FAILED'])
const STREAMABLE_STATUS = new Set(['PENDING', 'RUNNING'])

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<TaskItem[]>([])
  const currentTaskId = ref<string | null>(null)
  const taskDetail = ref<TaskDetailResponse | null>(null)
  const auditEvents = ref<AuditEvent[]>([])
  const taskReport = ref<EvaluationReport | null>(null)
  const redbenchDatasets = ref<string[]>([])
  const sidebarCollapsed = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const streamSocket = ref<WebSocket | null>(null)
  const reconnectTimer = ref<number | null>(null)

  const currentTask = computed(() => taskDetail.value?.task ?? tasks.value.find((task) => task.id === currentTaskId.value) ?? null)
  const attackCases = computed(() => taskDetail.value?.attack_cases ?? [])
  const mutationTasks = computed<MutationTask[]>(() => taskDetail.value?.mutation_tasks ?? [])
  const detectionResults = computed(() => taskDetail.value?.detection_results ?? [])
  const latestEvent = computed(() => auditEvents.value[auditEvents.value.length - 1] ?? null)
  const canStartCurrentTask = computed(() => currentTask.value?.status === 'PENDING')

  async function loadInitialData() {
    loading.value = true
    error.value = null
    try {
      const [taskList, datasets] = await Promise.all([getTasks(), getRedbenchDatasets()])
      tasks.value = taskList.tasks
      redbenchDatasets.value = datasets.datasets
      if (!currentTaskId.value && tasks.value.length > 0) {
        await selectTask(tasks.value[0].id)
      }
    } catch (err) {
      error.value = normalizeError(err)
    } finally {
      loading.value = false
    }
  }

  async function selectTask(taskId: string) {
    closeTaskStream()
    currentTaskId.value = taskId
    const knownTask = tasks.value.find((task) => task.id === taskId)
    if (knownTask && STREAMABLE_STATUS.has(knownTask.status)) {
      connectTaskStream(taskId)
    }
    await refreshCurrentTask()
    if (currentTask.value && STREAMABLE_STATUS.has(currentTask.value.status) && !streamSocket.value) {
      connectTaskStream(taskId)
    }
  }

  async function refreshTaskList() {
    const taskList = await getTasks()
    tasks.value = taskList.tasks
  }

  async function refreshCurrentTask() {
    if (!currentTaskId.value) return
    try {
      const [detail, events, report] = await Promise.all([
        getTaskDetail(currentTaskId.value),
        getTaskEvents(currentTaskId.value),
        getTaskReport(currentTaskId.value),
      ])
      applyTaskSnapshot({
        task: detail.task,
        attack_cases: detail.attack_cases,
        mutation_tasks: detail.mutation_tasks,
        detection_results: detail.detection_results,
        events: events.events,
        report: report.report ?? detail.report ?? null,
      })
    } catch (err) {
      error.value = normalizeError(err)
    }
  }

  async function submitTask(payload: TaskCreateRequest) {
    loading.value = true
    error.value = null
    try {
      const response = await createTask(payload)
      await refreshTaskList()
      currentTaskId.value = response.task_id
      await refreshCurrentTask()
      if (currentTask.value && STREAMABLE_STATUS.has(currentTask.value.status)) {
        connectTaskStream(response.task_id)
      }
      return response
    } catch (err) {
      error.value = normalizeError(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function runCurrentTask() {
    if (!currentTaskId.value) return
    loading.value = true
    error.value = null
    try {
      const response = await startTask(currentTaskId.value)
      if (STREAMABLE_STATUS.has(response.status)) {
        connectTaskStream(response.task_id)
      }
      await refreshCurrentTask()
      if (STREAMABLE_STATUS.has(response.status) && !streamSocket.value) {
        connectTaskStream(response.task_id)
      }
      return response
    } catch (err) {
      error.value = normalizeError(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  function connectTaskStream(taskId = currentTaskId.value) {
    if (!taskId) return
    if (
      streamSocket.value &&
      currentTaskId.value === taskId &&
      (streamSocket.value.readyState === WebSocket.CONNECTING || streamSocket.value.readyState === WebSocket.OPEN)
    ) {
      return
    }

    closeTaskStream()
    const socket = openTaskStream(taskId)
    streamSocket.value = socket

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data) as TaskStreamMessage
      if (message.type === 'task.progress' && message.data) {
        applyTaskSnapshot(message.data)
      }
      if (message.type === 'task.not_found') {
        error.value = '任务流不存在'
        closeTaskStream()
      }
    }

    socket.onerror = () => {
      socket.close()
    }

    socket.onclose = () => {
      if (streamSocket.value === socket) {
        streamSocket.value = null
      }
      if (currentTaskId.value === taskId && currentTask.value && !FINISHED_STATUS.has(currentTask.value.status)) {
        scheduleReconnect(taskId)
      }
    }
  }

  function closeTaskStream() {
    if (reconnectTimer.value !== null) {
      window.clearTimeout(reconnectTimer.value)
      reconnectTimer.value = null
    }
    if (streamSocket.value) {
      const socket = streamSocket.value
      streamSocket.value = null
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close()
      }
    }
  }

  function scheduleReconnect(taskId: string) {
    if (reconnectTimer.value !== null) {
      window.clearTimeout(reconnectTimer.value)
    }
    reconnectTimer.value = window.setTimeout(() => {
      reconnectTimer.value = null
      connectTaskStream(taskId)
    }, 1500)
  }

  function applyTaskSnapshot(snapshot: TaskStreamPayload) {
    taskDetail.value = {
      task: snapshot.task,
      attack_cases: snapshot.attack_cases,
      mutation_tasks: snapshot.mutation_tasks,
      detection_results: snapshot.detection_results,
      report: snapshot.report ?? null,
    }
    auditEvents.value = snapshot.events
    taskReport.value = snapshot.report ?? null
    upsertTask(snapshot.task)

    if (FINISHED_STATUS.has(snapshot.task.status)) {
      closeTaskStream()
    }
  }

  function upsertTask(task: TaskItem) {
    const index = tasks.value.findIndex((item) => item.id === task.id)
    if (index === -1) {
      tasks.value = [task, ...tasks.value]
      return
    }
    tasks.value[index] = task
    tasks.value = [...tasks.value]
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return {
    tasks,
    currentTaskId,
    taskDetail,
    auditEvents,
    taskReport,
    redbenchDatasets,
    sidebarCollapsed,
    loading,
    error,
    streamSocket,
    currentTask,
    attackCases,
    mutationTasks,
    detectionResults,
    latestEvent,
    canStartCurrentTask,
    loadInitialData,
    selectTask,
    refreshCurrentTask,
    submitTask,
    runCurrentTask,
    connectTaskStream,
    closeTaskStream,
    toggleSidebar,
  }
})

function normalizeError(err: unknown) {
  if (err instanceof Error) return err.message
  return '请求失败，请检查后端服务是否启动。'
}
