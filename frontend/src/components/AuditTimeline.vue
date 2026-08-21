<!--
  组件名称：AuditTimeline.vue
  组件功能：审计时间线组件，按时间顺序展示审计事件流（Fast Path 与 Slow Path
  证据链），每个事件显示事件类型、消息、代理、工具、风险和时间等元信息。
  事件根据类型自动着色（危险/警告/成功/中性）。
-->
<script setup lang="ts">
import type { AuditEvent } from '@/types/task'

/**
 * 根据事件类型返回对应的 CSS 样式类
 * BLOCKED → danger（危险/阻断）
 * DEGRADED → warning（警告/降级）
 * allowed → success（成功/放行）
 * 其他 → neutral（中性）
 * @param event 审计事件对象
 * @returns CSS 类名
 */
function eventClass(event: AuditEvent) {
  if (event.event_type.includes('BLOCKED')) return 'danger'
  if (event.event_type.includes('DEGRADED')) return 'warning'
  if (event.allowed === true) return 'success'
  return 'neutral'
}

/**
 * 提取事件消息文本
 * 优先取 event.message，其次取 event.payload.message 字符串，兜底为"无消息"
 * @param event 审计事件对象
 * @returns 事件消息文本
 */
function eventMessage(event: AuditEvent) {
  const payloadMessage = event.payload?.message
  return event.message || (typeof payloadMessage === 'string' ? payloadMessage : '无消息')
}

/**
 * 格式化时间戳为本地时间字符串
 * @param value ISO 时间字符串
 * @returns 格式化后的时间字符串，如 "14:30:25"
 */
function formatTime(value: string) {
  return value ? new Date(value).toLocaleTimeString() : '--'
}

/**
 * 格式化事件主题，兜底返回 'UNKNOWN'
 * @param value 事件主题字符串
 * @returns 格式化后的主题
 */
function formatTopic(value?: string | null) {
  return value || 'UNKNOWN'
}

/**
 * 格式化代理名称，兜底返回 'unknown'
 * @param value 代理名称
 * @returns 格式化后的代理名称
 */
function formatAgent(value?: string | null) {
  return value || 'unknown'
}

/**
 * 判断事件列表是否非空
 * @param events 审计事件数组
 * @returns 是否有事件
 */
function hasEvents(events: AuditEvent[]) {
  return events.length > 0
}

/**
 * 提取风险标签（风险类型或风险等级）
 * @param event 审计事件对象
 * @returns 风险标签字符串
 */
function riskLabel(event: AuditEvent) {
  return event.risk_type || event.risk_level || ''
}

/**
 * 提取工具标签（如 "tool: search"）
 * @param event 审计事件对象
 * @returns 工具标签字符串，无工具时返回空串
 */
function toolLabel(event: AuditEvent) {
  return event.tool_name ? `tool: ${event.tool_name}` : ''
}

/**
 * 生成事件唯一 key，用于 v-for 绑定
 * 优先使用 event.id，否则使用 event_type + created_at 拼接
 * @param event 审计事件对象
 * @returns 唯一标识字符串
 */
function eventKey(event: AuditEvent) {
  return event.id || `${event.event_type}-${event.created_at}`
}

/**
 * 返回事件列表（当前直接透传，预留后续过滤/排序扩展）
 * @param events 审计事件数组
 * @returns 原样返回事件数组
 */
function displayEvents(events: AuditEvent[]) {
  return events
}

/**
 * Props 定义
 * events: 审计事件数组，按时间顺序排列
 */
const props = defineProps<{
  events: AuditEvent[]
}>()
</script>

<template>
  <aside class="panel audit-timeline">
    <div class="panel-title">
      <div>
        <h2>审计日志 / 事件流</h2>
        <p>按时间顺序展示 Fast Path 与 Slow Path 证据链。</p>
      </div>
    </div>
    <!-- 时间线滚动区域 -->
    <div class="timeline-scroll">
      <!-- 遍历事件列表，渲染时间线条目；每个条目根据事件类型着色 -->
      <div v-for="event in displayEvents(props.events)" :key="eventKey(event)" class="timeline-item" :class="eventClass(event)">
        <!-- 时间线圆点 -->
        <div class="timeline-dot" />
        <div class="timeline-content">
          <!-- 事件头部：事件类型代码 + 事件主题 -->
          <div class="timeline-head">
            <code>{{ event.event_type }}</code>
            <span>{{ formatTopic(event.event_topic) }}</span>
          </div>
          <!-- 事件消息正文 -->
          <p>{{ eventMessage(event) }}</p>
          <!-- 事件元信息：代理、工具、风险、时间 -->
          <div class="timeline-meta">
            <span>{{ formatAgent(event.agent) }}</span>
            <!-- 仅当有工具标签时显示 -->
            <span v-if="toolLabel(event)">{{ toolLabel(event) }}</span>
            <!-- 仅当有风险标签时显示 -->
            <span v-if="riskLabel(event)">{{ riskLabel(event) }}</span>
            <span>{{ formatTime(event.created_at) }}</span>
          </div>
        </div>
      </div>
      <!-- 无事件时显示空状态 -->
      <el-empty v-if="!hasEvents(props.events)" description="暂无审计事件" :image-size="88" />
    </div>
  </aside>
</template>