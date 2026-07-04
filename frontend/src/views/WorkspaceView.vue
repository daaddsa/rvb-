<script setup lang="ts">
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import LeftSidebar from '@/components/LeftSidebar.vue'
import TaskHeader from '@/components/TaskHeader.vue'
import ActionGraph from '@/components/ActionGraph.vue'
import DataViewer from '@/components/DataViewer.vue'
import SecurityInsights from '@/components/SecurityInsights.vue'
import AuditTimeline from '@/components/AuditTimeline.vue'
import { useTaskStore } from '@/stores/task'

const store = useTaskStore()
const route = useRoute()

async function handleStartTask() {
  await store.runCurrentTask()
}

onMounted(async () => {
  await store.loadInitialData()
  const routeTaskId = route.params.taskId
  if (typeof routeTaskId === 'string') {
    await store.selectTask(routeTaskId)
  }
})

watch(
  () => route.params.taskId,
  async (taskId) => {
    if (typeof taskId === 'string' && taskId !== store.currentTaskId) {
      await store.selectTask(taskId)
    }
  },
)

onBeforeUnmount(() => store.closeTaskStream())
</script>

<template>
  <div class="workspace-shell">
    <LeftSidebar />
    <main class="main-content">
      <el-alert v-if="store.error" class="error-alert" type="error" :title="store.error" show-icon />
      <TaskHeader
        :task="store.currentTask"
        :can-start="store.canStartCurrentTask"
        :loading="store.loading"
        @start="handleStartTask"
      />
      <ActionGraph :attack-cases="store.attackCases" :events="store.auditEvents" :detections="store.detectionResults" />
      <DataViewer
        :attack-cases="store.attackCases"
        :mutation-tasks="store.mutationTasks"
        :audit-events="store.auditEvents"
        :detection-results="store.detectionResults"
      />
      <section class="insights-layout">
        <SecurityInsights :report="store.taskReport" :attack-cases="store.attackCases" :detection-results="store.detectionResults" />
        <AuditTimeline :events="store.auditEvents" />
      </section>
    </main>
  </div>
</template>
