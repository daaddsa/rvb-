<script setup lang="ts">
import { computed } from 'vue'
import { Play } from 'lucide-vue-next'
import type { TaskItem } from '@/types/task'

const props = defineProps<{
  task: TaskItem | null
  canStart: boolean
  loading: boolean
}>()

const emit = defineEmits<{
  start: []
}>()

const statusClass = computed(() => props.task?.status.toLowerCase() ?? 'empty')
</script>

<template>
  <header class="task-header panel">
    <div>
      <p class="eyebrow">ASI-2026 Agent Security Evaluation</p>
      <h1 v-if="task">[Task] ASI-2026 红蓝对抗演练 #{{ task.id }}</h1>
      <h1 v-else>[Task] ASI-2026 红蓝对抗演练</h1>
      <div v-if="task" class="meta-line">
        <span class="status-badge" :class="statusClass">{{ task.status }}</span>
        <span>创建：{{ new Date(task.created_at).toLocaleString() }}</span>
        <span>更新：{{ new Date(task.updated_at).toLocaleString() }}</span>
        <code>{{ task.matrix_version }}</code>
      </div>
      <p v-else class="muted">请选择历史任务或创建一个新任务。</p>
    </div>
    <el-button v-if="task && canStart" type="primary" :loading="loading" @click="emit('start')">
      <Play :size="16" />
      开始执行
    </el-button>
  </header>
</template>
