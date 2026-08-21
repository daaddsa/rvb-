<!--
  组件名称：TaskHeader.vue
  组件功能：任务头部组件，展示当前任务的标题、状态、时间戳等元信息，
  并提供"开始执行"按钮触发红蓝对抗演练。
-->
<script setup lang="ts">
import { computed } from 'vue'
import { Play } from 'lucide-vue-next'
import type { TaskItem } from '@/types/task'

/**
 * Props 定义
 * task: 当前任务对象，可为 null（无任务时）
 * canStart: 任务是否可开始（如状态为 pending 等）
 * loading: 任务是否正在执行中的加载状态
 */
const props = defineProps<{
  task: TaskItem | null
  canStart: boolean
  loading: boolean
}>()

/**
 * 事件定义
 * start: 点击"开始执行"按钮时触发，通知父组件启动任务
 */
const emit = defineEmits<{
  start: []
}>()

// 计算属性：根据任务状态生成 CSS 类名，用于样式差异化展示
const statusClass = computed(() => props.task?.status.toLowerCase() ?? 'empty')
</script>

<template>
  <header class="task-header panel">
    <div>
      <!-- 副标题/引导语 -->
      <p class="eyebrow">ASI-2026 Agent Security Evaluation</p>
      <!-- 有任务时展示任务 ID，无任务时仅展示标题 -->
      <h1 v-if="task">[Task] ASI-2026 红蓝对抗演练 #{{ task.id }}</h1>
      <h1 v-else>[Task] ASI-2026 红蓝对抗演练</h1>
      <!-- 有任务时展示元信息行：状态、创建时间、更新时间、矩阵版本 -->
      <div v-if="task" class="meta-line">
        <!-- 状态徽章，class 由 statusClass 计算属性决定 -->
        <span class="status-badge" :class="statusClass">{{ task.status }}</span>
        <span>创建：{{ new Date(task.created_at).toLocaleString() }}</span>
        <span>更新：{{ new Date(task.updated_at).toLocaleString() }}</span>
        <code>{{ task.matrix_version }}</code>
      </div>
      <!-- 无任务时显示提示文字 -->
      <p v-else class="muted">请选择历史任务或创建一个新任务。</p>
    </div>
    <!-- "开始执行"按钮：仅在有任务且可开始且非加载中时显示 -->
    <el-button v-if="task && canStart" type="primary" :loading="loading" @click="emit('start')">
      <Play :size="16" />
      开始执行
    </el-button>
  </header>
</template>