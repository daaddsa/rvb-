/**
 * stores/task.ts — 任务状态管理仓库（Pinia Store）
 * 管理红蓝对抗平台中所有与任务相关的全局状态，包括：
 *   1. 任务列表、任务详情、审计事件、评估报告等数据
 *   2. 任务创建、启动、选择、轮询刷新等操作
 *   3. WebSocket 实时流连接管理与自动重连
 *   4. 侧边栏折叠状态
 * 使用 Pinia 组合式 API（setup store）风格编写。
 */

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

// ==================== 常量定义 ====================

/** 任务已结束的状态集合（COMPLETED 已完成 | FAILED 失败） */
const FINISHED_STATUS = new Set(['COMPLETED', 'FAILED'])
/** 可建立 WebSocket 流连接的状态集合（PENDING 待执行 | RUNNING 运行中） */
const STREAMABLE_STATUS = new Set(['PENDING', 'RUNNING'])

// ==================== Store 定义 ====================

export const useTaskStore = defineStore('task', () => {
  // ==================== 响应式状态（State） ====================

  /** 任务列表（所有已创建的任务） */
  const tasks = ref<TaskItem[]>([])
  /** 当前选中的任务 ID */
  const currentTaskId = ref<string | null>(null)
  /** 当前任务的详细信息（含攻击案例、变异任务、检测结果、报告） */
  const taskDetail = ref<TaskDetailResponse | null>(null)
  /** 当前任务的审计事件列表 */
  const auditEvents = ref<AuditEvent[]>([])
  /** 当前任务的评估报告 */
  const taskReport = ref<EvaluationReport | null>(null)
  /** 红队基准数据集名称列表 */
  const redbenchDatasets = ref<string[]>([])
  /** 侧边栏是否折叠 */
  const sidebarCollapsed = ref(false)
  /** 全局加载状态（创建任务、启动任务时使用） */
  const loading = ref(false)
  /** 全局错误信息 */
  const error = ref<string | null>(null)
  /** WebSocket 流连接实例 */
  const streamSocket = ref<WebSocket | null>(null)
  /** 重连定时器 ID（用于 WebSocket 断开后自动重连） */
  const reconnectTimer = ref<number | null>(null)

  // ==================== 计算属性（Getters） ====================

  /**
   * 当前任务对象
   * 计算逻辑：优先从 taskDetail 中获取，否则从 tasks 列表中按 currentTaskId 查找
   */
  const currentTask = computed(() => taskDetail.value?.task ?? tasks.value.find((task) => task.id === currentTaskId.value) ?? null)

  /** 攻击案例列表（从 taskDetail 中提取，无数据时返回空数组） */
  const attackCases = computed(() => taskDetail.value?.attack_cases ?? [])

  /** 变异任务列表（从 taskDetail 中提取，无数据时返回空数组） */
  const mutationTasks = computed<MutationTask[]>(() => taskDetail.value?.mutation_tasks ?? [])

  /** 检测结果列表（从 taskDetail 中提取，无数据时返回空数组） */
  const detectionResults = computed(() => taskDetail.value?.detection_results ?? [])

  /** 最新一条审计事件（取事件列表末尾，无事件时返回 null） */
  const latestEvent = computed(() => auditEvents.value[auditEvents.value.length - 1] ?? null)

  /** 当前任务是否可以启动（仅当状态为 PENDING 时返回 true） */
  const canStartCurrentTask = computed(() => currentTask.value?.status === 'PENDING')

  // ==================== 操作方法（Actions） ====================

  /**
   * 加载初始数据（页面首次加载时调用）
   * 并行获取任务列表和红队基准数据集，如果尚未选中任务则自动选中第一个
   */
  async function loadInitialData() {
    loading.value = true
    error.value = null
    try {
      // 并行请求：同时获取任务列表和数据集列表
      const [taskList, datasets] = await Promise.all([getTasks(), getRedbenchDatasets()])
      tasks.value = taskList.tasks
      redbenchDatasets.value = datasets.datasets
      // 如果没有选中任务且任务列表不为空，自动选中第一个任务
      if (!currentTaskId.value && tasks.value.length > 0) {
        await selectTask(tasks.value[0].id)
      }
    } catch (err) {
      error.value = normalizeError(err)
    } finally {
      loading.value = false
    }
  }

  /**
   * 选中（切换）任务
   * 关闭旧的 WebSocket 连接，更新 currentTaskId，如果任务处于可流式推送状态则建立 WebSocket 连接，
   * 然后刷新任务详情。
   *
   * @param taskId - 要选中的任务 ID
   */
  async function selectTask(taskId: string) {
    // 先关闭旧任务的 WebSocket 流连接
    closeTaskStream()
    // 更新当前选中的任务 ID
    currentTaskId.value = taskId
    // 如果已知任务状态为可流式推送，立即建立 WebSocket 连接
    const knownTask = tasks.value.find((task) => task.id === taskId)
    if (knownTask && STREAMABLE_STATUS.has(knownTask.status)) {
      connectTaskStream(taskId)
    }
    // 刷新任务详情（从后端获取最新数据）
    await refreshCurrentTask()
    // 刷新后如果任务仍处于可流式推送状态且未建立连接，补建 WebSocket 连接
    if (currentTask.value && STREAMABLE_STATUS.has(currentTask.value.status) && !streamSocket.value) {
      connectTaskStream(taskId)
    }
  }

  /**
   * 刷新任务列表（仅更新任务列表，不刷新详情）
   * 调用 GET /api/tasks 接口获取最新任务列表
   */
  async function refreshTaskList() {
    const taskList = await getTasks()
    tasks.value = taskList.tasks
  }

  /**
   * 刷新当前任务的详细信息
   * 并行请求任务详情、事件列表、评估报告，然后调用 applyTaskSnapshot 更新本地状态
   */
  async function refreshCurrentTask() {
    if (!currentTaskId.value) return
    try {
      // 并行请求：同时获取详情、事件、报告
      const [detail, events, report] = await Promise.all([
        getTaskDetail(currentTaskId.value),
        getTaskEvents(currentTaskId.value),
        getTaskReport(currentTaskId.value),
      ])
      // 将后端返回的数据统一应用到本地状态
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

  /**
   * 提交（创建）新任务
   * 调用 createTask API 创建任务，刷新任务列表，选中新任务并建立 WebSocket 连接。
   *
   * @param payload - 任务创建请求参数
   * @returns 创建任务的响应数据
   */
  async function submitTask(payload: TaskCreateRequest) {
    loading.value = true
    error.value = null
    try {
      // 调用后端接口创建任务
      const response = await createTask(payload)
      // 刷新任务列表（包含新创建的任务）
      await refreshTaskList()
      // 自动选中新创建的任务
      currentTaskId.value = response.task_id
      // 刷新新任务的详情
      await refreshCurrentTask()
      // 如果新任务处于可流式推送状态，建立 WebSocket 连接
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

  /**
   * 启动当前选中的任务
   * 调用 startTask API，若任务进入可流式推送状态则建立 WebSocket 连接，然后刷新详情。
   *
   * @returns 启动任务的响应数据
   */
  async function runCurrentTask() {
    if (!currentTaskId.value) return
    loading.value = true
    error.value = null
    try {
      // 调用后端接口启动任务
      const response = await startTask(currentTaskId.value)
      // 如果启动后任务处于可流式推送状态，建立 WebSocket 连接
      if (STREAMABLE_STATUS.has(response.status)) {
        connectTaskStream(response.task_id)
      }
      // 刷新任务详情
      await refreshCurrentTask()
      // 刷新后再次检查，确保 WebSocket 连接已建立
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

  /**
   * 建立 WebSocket 流连接，监听任务实时进度
   * 如果已有相同 taskId 的连接（正在连接或已打开），则跳过；否则先关闭旧连接再新建。
   *
   * @param taskId - 要监听的任务 ID，默认为当前选中的任务 ID
   */
  function connectTaskStream(taskId = currentTaskId.value) {
    // 无效 taskId 直接返回
    if (!taskId) return
    // 如果已存在对同一任务的活跃连接（正在连接或已打开），跳过重复连接
    if (
      streamSocket.value &&
      currentTaskId.value === taskId &&
      (streamSocket.value.readyState === WebSocket.CONNECTING || streamSocket.value.readyState === WebSocket.OPEN)
    ) {
      return
    }

    // 关闭旧连接，创建新 WebSocket 连接
    closeTaskStream()
    const socket = openTaskStream(taskId)
    streamSocket.value = socket

    /**
     * 处理 WebSocket 消息
     * 当收到 task.progress 类型消息时，将任务快照数据应用到本地状态
     * 当收到 task.not_found 类型消息时，设置错误信息并关闭连接
     */
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data) as TaskStreamMessage
      // 任务进度更新：将后端推送的快照数据合并到本地状态
      if (message.type === 'task.progress' && message.data) {
        applyTaskSnapshot(message.data)
      }
      // 任务不存在：提示错误并关闭连接
      if (message.type === 'task.not_found') {
        error.value = '任务流不存在'
        closeTaskStream()
      }
    }

    /** WebSocket 连接出错时：关闭连接（触发 onclose 进行重连） */
    socket.onerror = () => {
      socket.close()
    }

    /**
     * WebSocket 连接关闭时：
     *   1. 清理 streamSocket 引用
     *   2. 如果当前任务未结束，调度自动重连（1.5 秒后重试）
     */
    socket.onclose = () => {
      if (streamSocket.value === socket) {
        streamSocket.value = null
      }
      // 如果当前任务未完成/失败，自动重连
      if (currentTaskId.value === taskId && currentTask.value && !FINISHED_STATUS.has(currentTask.value.status)) {
        scheduleReconnect(taskId)
      }
    }
  }

  /**
   * 关闭 WebSocket 流连接
   * 清除重连定时器，关闭 WebSocket 连接并清理引用
   */
  function closeTaskStream() {
    // 清除重连定时器
    if (reconnectTimer.value !== null) {
      window.clearTimeout(reconnectTimer.value)
      reconnectTimer.value = null
    }
    // 关闭 WebSocket 连接
    if (streamSocket.value) {
      const socket = streamSocket.value
      streamSocket.value = null
      // 仅当连接处于打开或连接中状态时才关闭
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close()
      }
    }
  }

  /**
   * 调度 WebSocket 自动重连
   * 在延迟 1.5 秒后尝试重新建立 WebSocket 连接
   *
   * @param taskId - 需要重连的任务 ID
   */
  function scheduleReconnect(taskId: string) {
    // 清除已有的重连定时器
    if (reconnectTimer.value !== null) {
      window.clearTimeout(reconnectTimer.value)
    }
    // 设置新的重连定时器（1.5 秒后执行）
    reconnectTimer.value = window.setTimeout(() => {
      reconnectTimer.value = null
      connectTaskStream(taskId)
    }, 1500)
  }

  /**
   * 将任务快照数据应用到本地响应式状态
   * 更新 taskDetail、auditEvents、taskReport，并同步更新 tasks 列表中的对应项。
   * 如果任务状态为已结束（COMPLETED/FAILED），则关闭 WebSocket 连接。
   *
   * @param snapshot - 任务快照数据（来自 WebSocket 推送或 HTTP 轮询）
   */
  function applyTaskSnapshot(snapshot: TaskStreamPayload) {
    // 更新任务详情
    taskDetail.value = {
      task: snapshot.task,
      attack_cases: snapshot.attack_cases,
      mutation_tasks: snapshot.mutation_tasks,
      detection_results: snapshot.detection_results,
      report: snapshot.report ?? null,
    }
    // 更新审计事件列表
    auditEvents.value = snapshot.events
    // 更新评估报告
    taskReport.value = snapshot.report ?? null
    // 更新或插入 tasks 列表中的对应任务项
    upsertTask(snapshot.task)

    // 如果任务已结束，关闭 WebSocket 连接（不再需要实时推送）
    if (FINISHED_STATUS.has(snapshot.task.status)) {
      closeTaskStream()
    }
  }

  /**
   * 更新或插入任务列表中的任务项
   * 如果该任务已存在于列表中，则更新其数据；否则插入到列表头部。
   *
   * @param task - 要更新或插入的任务对象
   */
  function upsertTask(task: TaskItem) {
    const index = tasks.value.findIndex((item) => item.id === task.id)
    // 未找到 → 插入到列表头部
    if (index === -1) {
      tasks.value = [task, ...tasks.value]
      return
    }
    // 已找到 → 原地更新
    tasks.value[index] = task
    tasks.value = [...tasks.value] // 触发响应式更新
  }

  /**
   * 切换侧边栏折叠状态
   * 折叠 ↔ 展开
   */
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  // ==================== 导出 ====================

  // 导出所有状态、计算属性和方法，供组件使用
  return {
    // 状态
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
    // 计算属性
    currentTask,
    attackCases,
    mutationTasks,
    detectionResults,
    latestEvent,
    canStartCurrentTask,
    // 方法
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

/**
 * 标准化错误信息
 * 将未知类型的错误对象转换为可读的字符串消息
 *
 * @param err - 捕获到的错误对象（类型未知）
 * @returns 标准化的错误消息字符串
 */
function normalizeError(err: unknown) {
  // 如果已经是 Error 实例，直接返回其 message
  if (err instanceof Error) return err.message
  // 否则返回通用错误提示
  return '请求失败，请检查后端服务是否启动。'
}