<!--
  views/WorkspaceView.vue — 工作区主页面视图
  作为平台的核心页面，整合了左侧边栏、任务头部、攻击流程图、数据查看器、
  安全洞察面板和审计时间线等子组件，是用户与平台交互的主要界面。
-->

<!-- ==================== 脚本区域 ==================== -->
<script setup lang="ts">
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import LeftSidebar from '@/components/LeftSidebar.vue'           // 左侧边栏（任务列表、创建任务等）
import TaskHeader from '@/components/TaskHeader.vue'             // 任务头部信息栏
import ActionGraph from '@/components/ActionGraph.vue'           // 攻击流程可视化图
import DataViewer from '@/components/DataViewer.vue'             // 数据查看器（攻击案例、变异任务等）
import SecurityInsights from '@/components/SecurityInsights.vue' // 安全洞察面板（评估报告、指标卡片）
import AuditTimeline from '@/components/AuditTimeline.vue'       // 审计事件时间线
import { useTaskStore } from '@/stores/task'                     // 任务状态管理 Store

/** 任务 Store 实例（全局状态管理） */
const store = useTaskStore()
/** 当前路由信息（用于获取路由参数 taskId） */
const route = useRoute()

/**
 * 处理启动任务事件
 * 由 TaskHeader 子组件通过 @start 事件触发
 * 调用 Store 的 runCurrentTask 方法向后台发起启动请求
 */
async function handleStartTask() {
  await store.runCurrentTask()
}

/**
 * 组件挂载时的初始化逻辑
 * 1. 加载初始数据（任务列表、数据集列表）
 * 2. 如果 URL 中包含 taskId 路由参数，自动选中对应任务
 *    → 跳转到 /tasks/:taskId 路由时，页面加载后自动切换到指定任务
 */
onMounted(async () => {
  await store.loadInitialData()
  // 从路由参数中读取 taskId
  const routeTaskId = route.params.taskId
  // 如果 taskId 存在且为有效字符串，选中该任务
  if (typeof routeTaskId === 'string') {
    await store.selectTask(routeTaskId)
  }
})

/**
 * 监听路由参数 taskId 的变化
 * 当用户在同一个 WorkspaceView 中导航到不同的 /tasks/:taskId 时，
 * 自动切换任务（无需重新加载页面）
 */
watch(
  // 监听路由参数 taskId
  () => route.params.taskId,
  async (taskId) => {
    // 仅当 taskId 为有效字符串且与当前选中任务不同时，才切换任务
    if (typeof taskId === 'string' && taskId !== store.currentTaskId) {
      await store.selectTask(taskId)
    }
  },
)

/**
 * 组件卸载前清理
 * 关闭 WebSocket 流连接，释放资源
 */
onBeforeUnmount(() => store.closeTaskStream())
</script>

<!-- ==================== 模板区域 ==================== -->
<template>
  <!-- 工作区外壳：flex 布局，左侧边栏 + 右侧主内容区 -->
  <div class="workspace-shell">
    <!-- 左侧边栏组件（任务列表、创建任务表单、任务参数显示） -->
    <LeftSidebar />

    <!-- 主内容区：自适应宽度，可滚动 -->
    <main class="main-content">
      <!-- 错误提示：当 store.error 存在时显示 Element Plus 的 Alert 警告组件 -->
      <el-alert v-if="store.error" class="error-alert" type="error" :title="store.error" show-icon />

      <!-- 任务头部组件：显示任务名称、状态、启动按钮等 -->
      <TaskHeader
        :task="store.currentTask"           <!-- 当前任务对象 -->
        :can-start="store.canStartCurrentTask" <!-- 是否可启动（仅 PENDING 状态） -->
        :loading="store.loading"            <!-- 加载状态（启动中显示 loading） -->
        @start="handleStartTask"            <!-- 监听启动按钮点击事件 -->
      />

      <!-- 攻击流程图组件：展示攻击过程的阶段节点和检测动作 -->
      <ActionGraph
        :attack-cases="store.attackCases"   <!-- 攻击案例列表 -->
        :events="store.auditEvents"         <!-- 审计事件列表 -->
        :detections="store.detectionResults" <!-- 检测结果列表 -->
      />

      <!-- 数据查看器组件：以卡片形式展示攻击案例、变异任务、审计事件、检测结果 -->
      <DataViewer
        :attack-cases="store.attackCases"       <!-- 攻击案例列表 -->
        :mutation-tasks="store.mutationTasks"   <!-- 变异任务列表 -->
        :audit-events="store.auditEvents"       <!-- 审计事件列表 -->
        :detection-results="store.detectionResults" <!-- 检测结果列表 -->
      />

      <!-- 洞察布局：左侧安全洞察面板 + 右侧审计时间线（双栏布局） -->
      <section class="insights-layout">
        <!-- 安全洞察面板：评估报告、指标卡片、攻击摘要 -->
        <SecurityInsights
          :report="store.taskReport"             <!-- 评估报告 -->
          :attack-cases="store.attackCases"      <!-- 攻击案例列表 -->
          :detection-results="store.detectionResults" <!-- 检测结果列表 -->
        />
        <!-- 审计时间线：实时展示审计事件的时间线视图 -->
        <AuditTimeline :events="store.auditEvents" />
      </section>
    </main>
  </div>
</template>