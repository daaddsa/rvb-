<script setup lang="ts">
import { computed, ref } from 'vue'
import hljs from 'highlight.js/lib/core'
import json from 'highlight.js/lib/languages/json'
import type { AttackCase, AuditEvent, DetectionResult, MutationTask } from '@/types/task'

hljs.registerLanguage('json', json)

const props = defineProps<{
  attackCases: AttackCase[]
  mutationTasks: MutationTask[]
  auditEvents: AuditEvent[]
  detectionResults: DetectionResult[]
}>()

const currentAttackRun = computed(() => {
  const attackCase = props.attackCases[props.attackCases.length - 1]
  if (!attackCase) return null

  const events = props.auditEvents.filter((event) => event.attack_case_id === attackCase.id)
  const detections = props.detectionResults.filter((item) => item.attack_case_id === attackCase.id)
  const targetEvents = events.filter((event) => ['TARGET_EXECUTED', 'TOOL_CALLED'].includes(event.event_type))
  const targetOutputs = detections.map((item) => item.raw_output?.target_output).filter(Boolean)
  const latestDetection = detections[detections.length - 1]

  return {
    title: `第 ${props.attackCases.length} 次攻击`,
    completed: detections.length > 0,
    action: latestDetection?.action ?? 'running',
    red: {
      id: attackCase.id,
      risk_type: attackCase.risk_type,
      prompt: attackCase.prompt,
      expected_violation: attackCase.expected_violation,
      severity: attackCase.severity,
    },
    target: {
      target_events: targetEvents,
      target_output: targetOutputs,
    },
    blue: detections,
  }
})

const activeMutationIndex = ref(0)

const mutationTaskView = computed(() =>
  props.mutationTasks.map((task, index) => ({
    ...task,
    title: `突变任务 ${index + 1}`,
    sourcePreview: task.source_prompt,
    mutatedPreview: task.mutated_prompt ?? '',
  })),
)

const activeMutationTask = computed(() => mutationTaskView.value[activeMutationIndex.value] ?? null)

const mutationProgressLabel = computed(() => {
  if (!mutationTaskView.value.length) return ''
  return `${activeMutationIndex.value + 1} / ${mutationTaskView.value.length}`
})

function setActiveMutation(index: number) {
  activeMutationIndex.value = index
}

function highlight(value: unknown) {
  const code = JSON.stringify(value, null, 2)
  return hljs.highlight(code, { language: 'json' }).value
}
</script>

<template>
  <section class="panel data-viewer">
    <div class="panel-title">
      <div>
        <h2>三方输出</h2>
        <p>展示当前攻击结果，并补充红方突变任务状态。</p>
      </div>
    </div>

    <div class="attack-run-list">
      <article v-if="currentAttackRun" class="attack-run-card">
        <div class="attack-run-head">
          <h3>{{ currentAttackRun.title }}</h3>
          <span class="run-status" :class="currentAttackRun.action">{{ currentAttackRun.completed ? currentAttackRun.action : '等待结果' }}</span>
        </div>
        <div class="three-output-grid">
          <div class="output-column">
            <h4>红方攻击载荷</h4>
            <pre class="code-block"><code v-html="highlight(currentAttackRun.red)" /></pre>
          </div>
          <div class="output-column">
            <h4>被测智能体输出</h4>
            <pre class="code-block"><code v-html="highlight(currentAttackRun.target)" /></pre>
          </div>
          <div class="output-column">
            <h4>蓝方审计判定</h4>
            <pre class="code-block"><code v-html="highlight(currentAttackRun.blue)" /></pre>
          </div>
        </div>
      </article>
      <el-empty v-else description="暂无攻击输出" :image-size="88" />
    </div>

    <div class="mutation-task-panel">
      <div class="panel-title compact-title mutation-title-row">
        <div>
          <h3>突变任务</h3>
          <p>按卡片滑动查看每次 payload 的进化结果。</p>
        </div>
        <span v-if="mutationTaskView.length" class="mutation-progress">{{ mutationProgressLabel }}</span>
      </div>
      <div v-if="mutationTaskView.length" class="mutation-carousel">
        <div class="mutation-tab-strip">
          <button
            v-for="(task, index) in mutationTaskView"
            :key="task.id"
            type="button"
            class="mutation-tab"
            :class="{ active: index === activeMutationIndex }"
            @click="setActiveMutation(index)"
          >
            <span>{{ task.title }}</span>
            <small>{{ task.status }}</small>
          </button>
        </div>

        <article v-if="activeMutationTask" class="mutation-task-card featured">
          <div class="attack-run-head">
            <div>
              <strong>{{ activeMutationTask.title }}</strong>
              <p class="mutation-subtitle">查看当前突变的策略、轮次和结果摘要</p>
            </div>
            <span class="run-status" :class="activeMutationTask.status.toLowerCase()">{{ activeMutationTask.status }}</span>
          </div>

          <div class="summary-fields compact-grid">
            <span>策略：{{ activeMutationTask.mutation_strategy || '未记录' }}</span>
            <span>下一轮：{{ activeMutationTask.next_round }}</span>
            <span>父用例：{{ activeMutationTask.parent_attack_case_id }}</span>
            <span>失败阶段：{{ activeMutationTask.failure_stage || '—' }}</span>
          </div>

          <div class="mutation-preview-grid">
            <section class="mutation-preview-card">
              <h4>原始 Payload</h4>
              <p>{{ activeMutationTask.sourcePreview || '无' }}</p>
            </section>
            <section class="mutation-preview-card emphasis">
              <h4>突变结果</h4>
              <p>{{ activeMutationTask.mutatedPreview || '处理中' }}</p>
            </section>
          </div>
        </article>
      </div>
      <el-empty v-else description="暂无突变任务" :image-size="72" />
    </div>
  </section>
</template>

<style scoped>
.data-viewer {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.mutation-task-panel {
  margin: 0 16px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #f6f8fa;
  overflow: hidden;
}

.mutation-title-row {
  align-items: center;
  justify-content: space-between;
}

.mutation-progress {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-panel);
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 700;
}

.mutation-carousel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}

.mutation-tab-strip {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(150px, 180px);
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-width: thin;
}

.mutation-tab {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-panel);
  color: var(--color-text);
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.mutation-tab:hover {
  border-color: #b6c2cf;
  background: #fbfcfd;
}

.mutation-tab small {
  color: var(--color-muted);
}

.mutation-tab.active {
  border-color: var(--color-accent);
  background: #eff6ff;
  box-shadow: 0 0 0 3px rgba(9, 105, 218, 0.12);
}

.mutation-task-card.featured {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-panel);
  overflow: hidden;
}

.mutation-subtitle {
  margin: 6px 0 0;
  color: var(--color-muted);
  font-size: 13px;
}

.compact-grid {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.compact-grid span {
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #f6f8fa;
  color: var(--color-muted);
}

.mutation-preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 0 12px 12px;
}

.mutation-preview-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #f6f8fa;
  overflow: hidden;
}

.mutation-preview-card h4 {
  margin: 0;
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-panel);
  color: var(--color-muted);
  font-size: 13px;
}

.mutation-preview-card p {
  margin: 0;
  padding: 12px;
  color: var(--color-text);
  line-height: 1.7;
  max-height: 220px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.mutation-preview-card.emphasis h4 {
  color: var(--color-accent);
}

@media (max-width: 900px) {
  .mutation-preview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
