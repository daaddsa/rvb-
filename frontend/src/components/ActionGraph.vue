<!--
  组件名称：ActionGraph.vue
  组件功能：对抗态势图组件，以阶段流水线的方式可视化展示单次攻击中
  红方攻击推进与蓝方检测防御的完整过程，包括攻击、输入检测、目标执行、
  工具检测、输出检测、结果归档六个阶段。
-->
<script setup lang="ts">
import { computed } from 'vue'
import { Check, Circle, X, AlertTriangle } from 'lucide-vue-next'
import type { AttackCase, AuditEvent, DetectionResult } from '@/types/task'

/**
 * Props 定义
 * attackCases: 攻击用例列表，每次攻击一个 AttackCase
 * events: 审计事件列表，包含各阶段事件
 * detections: 检测结果列表，包含各阶段的判定结果
 */
const props = defineProps<{
  attackCases: AttackCase[]
  events: AuditEvent[]
  detections: DetectionResult[]
}>()

// 定义六个对抗阶段，每个阶段包含 key、中文标签和对应的审计事件类型
const stages = [
  { key: 'attack', label: '红方攻击', events: ['ATTACK_REQUESTED'] },
  { key: 'input', label: '蓝方输入检测', events: ['INPUT_DETECTED'] },
  { key: 'target', label: '目标执行', events: ['TARGET_EXECUTED'] },
  { key: 'tool', label: '蓝方工具检测', events: ['TOOL_ALLOWED', 'TOOL_BLOCKED', 'TOOL_DEGRADED', 'TOOL_CALLED'] },
  { key: 'output', label: '蓝方输出检测', events: ['OUTPUT_ALLOWED', 'OUTPUT_BLOCKED'] },
  { key: 'report', label: '结果归档', events: ['REPORT_EVENT'] },
] as const

// 计算属性：获取最新的攻击用例（最后一个元素）
const latestAttackCase = computed(() => props.attackCases[props.attackCases.length - 1] ?? null)

/**
 * 计算属性：筛选与最新攻击用例关联的审计事件
 * 如果最新攻击用例有对应事件则返回，否则回退到全部事件
 */
const scopedEvents = computed(() => {
  const attackCaseId = latestAttackCase.value?.id
  if (attackCaseId) {
    const attackEvents = props.events.filter((event) => event.attack_case_id === attackCaseId)
    if (attackEvents.length > 0) return attackEvents
  }
  return props.events
})

/**
 * 计算属性：筛选与最新攻击用例关联的检测结果
 * 如果最新攻击用例有对应检测结果则返回，否则回退到全部检测结果
 */
const scopedDetections = computed(() => {
  const attackCaseId = latestAttackCase.value?.id
  if (attackCaseId) {
    const attackDetections = props.detections.filter((item) => item.attack_case_id === attackCaseId)
    if (attackDetections.length > 0) return attackDetections
  }
  return props.detections
})

// 计算属性：获取最新一条审计事件
const latestEvent = computed(() => scopedEvents.value[scopedEvents.value.length - 1] ?? null)
// 计算属性：获取最新审计事件的事件类型
const latestEventType = computed(() => latestEvent.value?.event_type)
// 计算属性：获取最新一条检测结果
const latestDetection = computed(() => scopedDetections.value[scopedDetections.value.length - 1] ?? null)

// 计算属性：当前攻击的标题文本
const currentAttackTitle = computed(() => {
  if (!latestAttackCase.value) return '暂无攻击执行'
  return `第 ${props.attackCases.length} 次攻击 · ${latestAttackCase.value.risk_type || 'UNKNOWN'}`
})

/**
 * 计算属性：攻击摘要描述
 * 优先级：检测结果原因 > 最新事件消息 > 默认文本
 */
const attackSummary = computed(() => {
  if (!latestAttackCase.value) return '等待红方发起攻击。'
  if (latestDetection.value) {
    return latestDetection.value.reason || '当前攻击已完成阶段判定。'
  }
  return latestEvent.value?.message || '当前攻击执行中。'
})

/**
 * 计算属性：构建阶段节点列表
 * 遍历 stages 数组，为每个阶段计算完成状态、激活状态、动作类型和状态文本
 */
const nodes = computed(() => {
  const events = scopedEvents.value
  const detections = scopedDetections.value
  // 找到最新事件类型在 stages 中的索引，确定当前激活阶段
  const latestIndex = latestEventType.value ? stages.findIndex((stage) => stage.events.includes(latestEventType.value as never)) : -1

  return stages.map((stage, index) => {
    // 筛选与该阶段关联的审计事件
    const relatedEvents = events.filter((event) => stage.events.includes(event.event_type as never))
    // 查找该阶段的检测结果
    const detection = detections.find((item) => item.stage === stage.key || (stage.key === 'tool' && item.stage === 'tool_call'))
    const lastEvent = relatedEvents[relatedEvents.length - 1]
    // 有相关事件则该阶段已完成
    const completed = relatedEvents.length > 0
    // 当前索引等于最新事件索引且不是终态事件时，标记为 active（进行中）
    const active = latestIndex === index && !isTerminalEvent(latestEventType.value)
    // 动作类型：优先取检测结果中的 action，否则根据事件类型推断
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

/**
 * 判断事件类型是否为终态事件
 * 终态事件包括：输出放行/阻断、工具阻断、报告归档
 * @param eventType 事件类型字符串
 * @returns 是否为终态事件
 */
function isTerminalEvent(eventType?: string) {
  return eventType === 'OUTPUT_ALLOWED' || eventType === 'OUTPUT_BLOCKED' || eventType === 'TOOL_BLOCKED' || eventType === 'REPORT_EVENT'
}

/**
 * 根据事件类型推断动作：block（阻断）、degrade（降级）、allow（放行）、pending（待定）
 * @param eventType 事件类型字符串
 * @returns 动作标识字符串
 */
function actionFromEvent(eventType?: string) {
  if (!eventType) return 'pending'
  if (eventType.includes('BLOCKED')) return 'block'
  if (eventType.includes('DEGRADED')) return 'degrade'
  return 'allow'
}

/**
 * 根据阶段 key、动作和完成状态，返回中文状态文本
 * @param stageKey 阶段标识
 * @param action 动作类型
 * @param completed 是否已完成
 * @returns 中文状态文本
 */
function statusTextFor(stageKey: string, action: string, completed: boolean) {
  if (action === 'running') return '进行中'
  if (!completed) return '待执行'
  if (action === 'block') return '已阻断'
  if (action === 'degrade') return '已降级'
  if (stageKey === 'report') return '已归档'
  return '已完成'
}

/**
 * 根据动作类型返回对应的图标组件
 * @param action 动作类型
 * @returns 对应的 Lucide 图标组件
 */
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
      <!-- 右侧阶段概览：当前攻击标题 + 摘要 -->
      <div class="stage-overview">
        <strong>{{ currentAttackTitle }}</strong>
        <span>{{ attackSummary }}</span>
      </div>
    </div>
    <!-- 阶段流水线 -->
    <div class="stage-line">
      <!-- 遍历阶段节点渲染 -->
      <div v-for="(node, index) in nodes" :key="node.key" class="stage-wrap">
        <!-- 阶段节点：根据 action/completed/active 动态 class -->
        <div class="stage-node" :class="[node.action, { active: node.active, completed: node.completed }]">
          <!-- 动态渲染图标组件 -->
          <component :is="iconFor(node.action)" :size="18" />
          <div class="stage-copy">
            <span>{{ node.label }}</span>
            <small>{{ node.statusText }}</small>
          </div>
        </div>
        <!-- 阶段连接线：最后一个节点不渲染连接线 -->
        <div v-if="index < nodes.length - 1" class="stage-connector" :class="node.completed ? node.action : 'pending'" />
      </div>
    </div>
  </section>
</template>