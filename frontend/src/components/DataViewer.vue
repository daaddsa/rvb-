<!--
  组件名称：DataViewer.vue
  组件功能：三方数据展示组件，展示当前攻击的三方输出数据（红方攻击载荷、被
  测智能体输出、蓝方审计判定），以及突变任务（payload 进化）的卡片滑动浏览。
  使用 highlight.js 对 JSON 数据进行语法高亮。
-->
<script setup lang="ts">
import { computed, ref } from 'vue'
import hljs from 'highlight.js/lib/core'
import json from 'highlight.js/lib/languages/json'
import type { AttackCase, AuditEvent, DetectionResult, MutationTask } from '@/types/task'

// 注册 JSON 语言高亮支持
hljs.registerLanguage('json', json)

/**
 * Props 定义
 * attackCases: 攻击用例列表
 * mutationTasks: 突变任务列表（payload 进化结果）
 * auditEvents: 审计事件列表
 * detectionResults: 检测结果列表
 */
const props = defineProps<{
  attackCases: AttackCase[]
  mutationTasks: MutationTask[]
  auditEvents: AuditEvent[]
  detectionResults: DetectionResult[]
}>()

/**
 * 计算属性：构建当前攻击回合的数据视图
 * 取最后一个攻击用例，关联其审计事件和检测结果，整理为红方/目标/蓝方三部分
 * 返回 null 表示无攻击用例
 */
const currentAttackRun = computed(() => {
  const attackCase = props.attackCases[props.attackCases.length - 1]
  if (!attackCase) return null

  // 筛选与该攻击用例关联的审计事件
  const events = props.auditEvents.filter((event) => event.attack_case_id === attackCase.id)
  // 筛选与该攻击用例关联的检测结果
  const detections = props.detectionResults.filter((item) => item.attack_case_id === attackCase.id)
  // 筛选目标执行类和工具调用类事件
  const targetEvents = events.filter((event) => ['TARGET_EXECUTED', 'TOOL_CALLED'].includes(event.event_type))
  // 提取检测结果中的目标输出
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

// 当前激活的突变任务索引，用于卡片切换
const activeMutationIndex = ref(0)

/**
 * 计算属性：将突变任务列表转换为带标题和预览的视图对象
 * 每个突变任务附加标题、源 payload 预览和突变结果预览
 */
const mutationTaskView = computed(() =>
  props.mutationTasks.map((task, index) => ({
    ...task,
    title: `突变任务 ${index + 1}`,
    sourcePreview: task.source_prompt,
    mutatedPreview: task.mutated_prompt ?? '',
  })),
)

// 计算属性：获取当前激活的突变任务视图对象
const activeMutationTask = computed(() => mutationTaskView.value[activeMutationIndex.value] ?? null)

// 计算属性：突变任务进度标签，如 "1 / 3"
const mutationProgressLabel = computed(() => {
  if (!mutationTaskView.value.length) return ''
  return `${activeMutationIndex.value + 1} / ${mutationTaskView.value.length}`
})

/**
 * 设置当前激活的突变任务索引
 * @param index 突变任务在列表中的索引
 */
function setActiveMutation(index: number) {
  activeMutationIndex.value = index
}

/**
 * 将任意值格式化为 JSON 字符串并高亮
 * @param value 要高亮的值
 * @returns 高亮后的 HTML 字符串
 */
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

    <!-- 攻击回合列表 -->
    <div class="attack-run-list">
      <!-- 有攻击数据时展示三方输出卡片 -->
      <article v-if="currentAttackRun" class="attack-run-card">
        <div class="attack-run-head">
          <h3>{{ currentAttackRun.title }}</h3>
          <!-- 运行状态标签：完成时显示动作类型，否则显示"等待结果" -->
          <span class="run-status" :class="currentAttackRun.action">{{ currentAttackRun.completed ? currentAttackRun.action : '等待结果' }}</span>
        </div>
        <!-- 三列输出网格：红方 / 目标 / 蓝方 -->
        <div class="three-output-grid">
          <!-- 红方攻击载荷列 -->
          <div class="output-column">
            <h4>红方攻击载荷</h4>
            <pre class="code-block"><code v-html="highlight(currentAttackRun.red)" /></pre>
          </div>
          <!-- 被测智能体输出列 -->
          <div class="output-column">
            <h4>被测智能体输出</h4>
            <pre class="code-block"><code v-html="highlight(currentAttackRun.target)" /></pre>
          </div>
          <!-- 蓝方审计判定列 -->
          <div class="output-column">
            <h4>蓝方审计判定</h4>
            <pre class="code-block"><code v-html="highlight(currentAttackRun.blue)" /></pre>
          </div>
        </div>
      </article>
      <!-- 无攻击数据时显示空状态 -->
      <el-empty v-else description="暂无攻击输出" :image-size="88" />
    </div>

    <!-- 突变任务面板 -->
    <div class="mutation-task-panel">
      <div class="panel-title compact-title mutation-title-row">
        <div>
          <h3>突变任务</h3>
          <p>按卡片滑动查看每次 payload 的进化结果。</p>
        </div>
        <!-- 显示突变任务进度 -->
        <span v-if="mutationTaskView.length" class="mutation-progress">{{ mutationProgressLabel }}</span>
      </div>
      <!-- 有突变任务时展示轮播卡片 -->
      <div v-if="mutationTaskView.length" class="mutation-carousel">
        <!-- 突变任务标签切换条 -->
        <div class="mutation-tab-strip">
          <!-- 遍历突变任务视图，渲染可点击的标签按钮 -->
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

        <!-- 当前激活的突变任务详情卡片 -->
        <article v-if="activeMutationTask" class="mutation-task-card featured">
          <div class="attack-run-head">
            <div>
              <strong>{{ activeMutationTask.title }}</strong>
              <p class="mutation-subtitle">查看当前突变的策略、轮次和结果摘要</p>
            </div>
            <!-- 突变任务状态标签 -->
            <span class="run-status" :class="activeMutationTask.status.toLowerCase()">{{ activeMutationTask.status }}</span>
          </div>

          <!-- 摘要字段：策略、下一轮、父用例、失败阶段 -->
          <div class="summary-fields compact-grid">
            <span>策略：{{ activeMutationTask.mutation_strategy || '未记录' }}</span>
            <span>下一轮：{{ activeMutationTask.next_round }}</span>
            <span>父用例：{{ activeMutationTask.parent_attack_case_id }}</span>
            <span>失败阶段：{{ activeMutationTask.failure_stage || '—' }}</span>
          </div>

          <!-- 突变预览网格：原始 Payload vs 突变结果 -->
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
      <!-- 无突变任务时显示空状态 -->
      <el-empty v-else description="暂无突变任务" :image-size="72" />
    </div>
  </section>
</template>

<style scoped>
/* 数据查看器整体布局：纵向 flex 排列，间距 24px */
.data-viewer {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 突变任务面板样式 */
.mutation-task-panel {
  margin: 0 16px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #f6f8fa;
  overflow: hidden;
}

/* 突变任务标题行：弹性布局，两端对齐 */
.mutation-title-row {
  align-items: center;
  justify-content: space-between;
}

/* 突变进度标签：药丸样式 */
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

/* 突变轮播容器 */
.mutation-carousel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}

/* 突变标签条：横向 grid 布局，自动列宽，支持横向滚动 */
.mutation-tab-strip {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(150px, 180px);
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-width: thin;
}

/* 突变标签按钮 */
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

/* 突变标签悬停状态 */
.mutation-tab:hover {
  border-color: #b6c2cf;
  background: #fbfcfd;
}

/* 突变标签中状态文字颜色 */
.mutation-tab small {
  color: var(--color-muted);
}

/* 突变标签激活状态：蓝色边框 + 背景 + 阴影 */
.mutation-tab.active {
  border-color: var(--color-accent);
  background: #eff6ff;
  box-shadow: 0 0 0 3px rgba(9, 105, 218, 0.12);
}

/* 突变任务详情卡片 */
.mutation-task-card.featured {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-panel);
  overflow: hidden;
}

/* 突变子标题 */
.mutation-subtitle {
  margin: 6px 0 0;
  color: var(--color-muted);
  font-size: 13px;
}

/* 紧凑网格：用于摘要字段，自适应列数 */
.compact-grid {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

/* 紧凑网格中的 span 字段样式 */
.compact-grid span {
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #f6f8fa;
  color: var(--color-muted);
}

/* 突变预览网格：两列布局 */
.mutation-preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 0 12px 12px;
}

/* 突变预览卡片 */
.mutation-preview-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #f6f8fa;
  overflow: hidden;
}

/* 突变预览卡片标题 */
.mutation-preview-card h4 {
  margin: 0;
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-panel);
  color: var(--color-muted);
  font-size: 13px;
}

/* 突变预览卡片正文：限制最大高度，支持滚动和换行 */
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

/* 强调卡片（突变结果）标题使用主题色 */
.mutation-preview-card.emphasis h4 {
  color: var(--color-accent);
}

/* 响应式：窄屏时突变预览网格变为单列 */
@media (max-width: 900px) {
  .mutation-preview-grid {
    grid-template-columns: 1fr;
  }
}
</style>