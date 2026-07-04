<script setup lang="ts">
import type { AuditEvent } from '@/types/task'

function eventClass(event: AuditEvent) {
  if (event.event_type.includes('BLOCKED')) return 'danger'
  if (event.event_type.includes('DEGRADED')) return 'warning'
  if (event.allowed === true) return 'success'
  return 'neutral'
}

function eventMessage(event: AuditEvent) {
  const payloadMessage = event.payload?.message
  return event.message || (typeof payloadMessage === 'string' ? payloadMessage : '无消息')
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleTimeString() : '--'
}

function formatTopic(value?: string | null) {
  return value || 'UNKNOWN'
}

function formatAgent(value?: string | null) {
  return value || 'unknown'
}

function hasEvents(events: AuditEvent[]) {
  return events.length > 0
}

function riskLabel(event: AuditEvent) {
  return event.risk_type || event.risk_level || ''
}

function toolLabel(event: AuditEvent) {
  return event.tool_name ? `tool: ${event.tool_name}` : ''
}

function eventKey(event: AuditEvent) {
  return event.id || `${event.event_type}-${event.created_at}`
}

function displayEvents(events: AuditEvent[]) {
  return events
}

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
    <div class="timeline-scroll">
      <div v-for="event in displayEvents(props.events)" :key="eventKey(event)" class="timeline-item" :class="eventClass(event)">
        <div class="timeline-dot" />
        <div class="timeline-content">
          <div class="timeline-head">
            <code>{{ event.event_type }}</code>
            <span>{{ formatTopic(event.event_topic) }}</span>
          </div>
          <p>{{ eventMessage(event) }}</p>
          <div class="timeline-meta">
            <span>{{ formatAgent(event.agent) }}</span>
            <span v-if="toolLabel(event)">{{ toolLabel(event) }}</span>
            <span v-if="riskLabel(event)">{{ riskLabel(event) }}</span>
            <span>{{ formatTime(event.created_at) }}</span>
          </div>
        </div>
      </div>
      <el-empty v-if="!hasEvents(props.events)" description="暂无审计事件" :image-size="88" />
    </div>
  </aside>
</template>
