<script setup lang="ts">
import { computed } from 'vue'
import { Check, Circle, X, AlertTriangle } from 'lucide-vue-next'
import type { AttackCase, AuditEvent, DetectionResult } from '@/types/task'

const props = defineProps<{
  attackCases: AttackCase[]
  events: AuditEvent[]
  detections: DetectionResult[]
}>()

const stages = [
  { key: 'attack', label: '红方攻击', events: ['ATTACK_REQUESTED'] },
  { key: 'input', label: '蓝方输入检测', events: ['INPUT_DETECTED'] },
  { key: 'target', label: '目标执行', events: ['TARGET_EXECUTED'] },
  { key: 'tool', label: '蓝方工具检测', events: ['TOOL_ALLOWED', 'TOOL_BLOCKED', 'TOOL_DEGRADED', 'TOOL_CALLED'] },
  { key: 'output', label: '蓝方输出检测', events: ['OUTPUT_ALLOWED', 'OUTPUT_BLOCKED'] },
  { key: 'report', label: '结果归档', events: ['REPORT_EVENT'] },
] as const

const latestAttackCase = computed(() => props.attackCases[props.attackCases.length - 1] ?? null)

const scopedEvents = computed(() => {
  const attackCaseId = latestAttackCase.value?.id
  if (attackCaseId) {
    const attackEvents = props.events.filter((event) => event.attack_case_id === attackCaseId)
    if (attackEvents.length > 0) return attackEvents
  }
  return props.events
})

const scopedDetections = computed(() => {
  const attackCaseId = latestAttackCase.value?.id
  if (attackCaseId) {
    const attackDetections = props.detections.filter((item) => item.attack_case_id === attackCaseId)
    if (attackDetections.length > 0) return attackDetections
  }
  return props.detections
})

const latestEvent = computed(() => scopedEvents.value[scopedEvents.value.length - 1] ?? null)
const latestEventType = computed(() => latestEvent.value?.event_type)
const latestDetection = computed(() => scopedDetections.value[scopedDetections.value.length - 1] ?? null)

const currentAttackTitle = computed(() => {
  if (!latestAttackCase.value) return '暂无攻击执行'
  return `第 ${props.attackCases.length} 次攻击 · ${latestAttackCase.value.risk_type || 'UNKNOWN'}`
})

const attackSummary = computed(() => {
  if (!latestAttackCase.value) return '等待红方发起攻击。'
  if (latestDetection.value) {
    return latestDetection.value.reason || '当前攻击已完成阶段判定。'
  }
  return latestEvent.value?.message || '当前攻击执行中。'
})

const nodes = computed(() => {
  const events = scopedEvents.value
  const detections = scopedDetections.value
  const latestIndex = latestEventType.value ? stages.findIndex((stage) => stage.events.includes(latestEventType.value as never)) : -1

  return stages.map((stage, index) => {
    const relatedEvents = events.filter((event) => stage.events.includes(event.event_type as never))
    const detection = detections.find((item) => item.stage === stage.key || (stage.key === 'tool' && item.stage === 'tool_call'))
    const lastEvent = relatedEvents[relatedEvents.length - 1]
    const completed = relatedEvents.length > 0
    const active = latestIndex === index && !isTerminalEvent(latestEventType.value)
    const action = completed ? detection?.action ?? actionFromEvent(lastEvent?.event_type) : active ? 'running' : 'pending'

    return {
      ...stage,
      completed,
      active,
      action,
      statusText: statusTextFor(stage.key, action, completed),
    }
  })
})

function isTerminalEvent(eventType?: string) {
  return eventType === 'OUTPUT_ALLOWED' || eventType === 'OUTPUT_BLOCKED' || eventType === 'TOOL_BLOCKED' || eventType === 'REPORT_EVENT'
}

function actionFromEvent(eventType?: string) {
  if (!eventType) return 'pending'
  if (eventType.includes('BLOCKED')) return 'block'
  if (eventType.includes('DEGRADED')) return 'degrade'
  return 'allow'
}

function statusTextFor(stageKey: string, action: string, completed: boolean) {
  if (action === 'running') return '进行中'
  if (!completed) return '待执行'
  if (action === 'block') return '已阻断'
  if (action === 'degrade') return '已降级'
  if (stageKey === 'report') return '已归档'
  return '已完成'
}

function iconFor(action: string) {
  if (action === 'block') return X
  if (action === 'degrade') return AlertTriangle
  if (action === 'allow') return Check
  return Circle
}
</script>

<template>
  <section class="panel action-graph">
    <div class="panel-title">
      <div>
        <h2>对抗态势</h2>
        <p>按单次攻击展示红方推进与蓝方检测过程，不再只停留在最终输出阶段。</p>
      </div>
      <div class="stage-overview">
        <strong>{{ currentAttackTitle }}</strong>
        <span>{{ attackSummary }}</span>
      </div>
    </div>
    <div class="stage-line">
      <div v-for="(node, index) in nodes" :key="node.key" class="stage-wrap">
        <div class="stage-node" :class="[node.action, { active: node.active, completed: node.completed }]">
          <component :is="iconFor(node.action)" :size="18" />
          <div class="stage-copy">
            <span>{{ node.label }}</span>
            <small>{{ node.statusText }}</small>
          </div>
        </div>
        <div v-if="index < nodes.length - 1" class="stage-connector" :class="node.completed ? node.action : 'pending'" />
      </div>
    </div>
  </section>
</template>
