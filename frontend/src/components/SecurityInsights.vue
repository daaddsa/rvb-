<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import MarkdownIt from 'markdown-it'
import type { AttackCase, DetectionResult, EvaluationReport } from '@/types/task'

const props = defineProps<{
  report: EvaluationReport | null
  attackCases: AttackCase[]
  detectionResults: DetectionResult[]
}>()

const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
const md = new MarkdownIt({ html: false, breaks: true })

const attackSummaries = computed(() =>
  props.attackCases.map((attackCase, index) => {
    const detections = props.detectionResults.filter((item) => item.attack_case_id === attackCase.id)
    const latest = detections[detections.length - 1]
    return {
      id: attackCase.id,
      title: `第 ${index + 1} 次攻击`,
      risk_type: attackCase.risk_type || 'UNKNOWN',
      action: latest?.action ?? 'pending',
      blocked: latest?.blocked ?? false,
      detected: latest?.detected ?? false,
      stage: latest?.stage ?? '等待计算',
      confidence: percent(latest?.confidence),
      reason: latest?.reason || '本次攻击尚未完成检测计算。',
    }
  }),
)

const finalMetrics = computed(() => [
  { label: '攻击总数', value: props.report?.total_attacks ?? 0 },
  { label: '攻击成功率', value: percent(props.report?.attack_success_rate) },
  { label: '检测率', value: percent(props.report?.detection_rate) },
  { label: '阻断率', value: percent(props.report?.block_rate) },
  { label: '误报率', value: percent(props.report?.false_positive_rate) },
  { label: '漏报率', value: percent(props.report?.false_negative_rate) },
])

const markdown = computed(() => {
  if (!props.report) return '所有攻击结束后生成最终总结报告。'
  return `# 本次测试整体结论\n\n${props.report.summary || '暂无总结。'}\n\n## 整改建议\n\n${props.report.recommendations || '暂无整改建议。'}`
})

const renderedMarkdown = computed(() => md.render(markdown.value))

watch(() => props.report, renderChart, { deep: true })

onMounted(renderChart)
onBeforeUnmount(() => chart?.dispose())

function percent(value?: number | null) {
  if (typeof value !== 'number') return '0.00%'
  return `${(value * 100).toFixed(2)}%`
}

function renderChart() {
  if (!chartRef.value) return
  chart = chart ?? echarts.init(chartRef.value)
  const report = props.report
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 32, right: 16, top: 24, bottom: 28 },
    xAxis: { type: 'category', data: ['攻击成功率', '检测率', '阻断率', '误报率', '漏报率'] },
    yAxis: { type: 'value', min: 0, max: 1 },
    series: [
      {
        type: 'bar',
        data: [
          report?.attack_success_rate ?? 0,
          report?.detection_rate ?? 0,
          report?.block_rate ?? 0,
          report?.false_positive_rate ?? 0,
          report?.false_negative_rate ?? 0,
        ],
        itemStyle: { color: '#0969da' },
      },
    ],
  })
}
</script>

<template>
  <section class="insights-left">
    <div class="panel compact-panel">
      <div class="panel-title">
        <div>
          <h2>单次攻击计算结果</h2>
          <p>每完成一次攻击，就展示该次攻击的检测阶段、动作和原因。</p>
        </div>
      </div>
      <div class="attack-summary-list">
        <article v-for="item in attackSummaries" :key="item.id" class="attack-summary-card">
          <div class="attack-summary-head">
            <strong>{{ item.title }}</strong>
            <span class="run-status" :class="item.action">{{ item.action }}</span>
          </div>
          <div class="summary-fields">
            <span>风险：{{ item.risk_type }}</span>
            <span>阶段：{{ item.stage }}</span>
            <span>置信度：{{ item.confidence }}</span>
            <span>阻断：{{ item.blocked ? '是' : '否' }}</span>
          </div>
          <p>{{ item.reason }}</p>
        </article>
        <el-empty v-if="attackSummaries.length === 0" description="暂无单次攻击结果" :image-size="88" />
      </div>
    </div>

    <div class="panel compact-panel final-report-panel">
      <div class="panel-title">
        <div>
          <h2>最终总结报告</h2>
          <p>所有攻击结束后再汇总生成整体指标和 AI 总结。</p>
        </div>
      </div>
      <template v-if="report">
        <div class="metric-grid final-metrics">
          <div v-for="metric in finalMetrics" :key="metric.label" class="metric-card">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
          </div>
        </div>
        <div ref="chartRef" class="chart" />
        <div class="json-grid">
          <pre>{{ JSON.stringify(report.risk_coverage ?? {}, null, 2) }}</pre>
          <pre>{{ JSON.stringify(report.risk_breakdown ?? {}, null, 2) }}</pre>
        </div>
      </template>
      <el-empty v-else description="等待全部攻击结束后生成报告" :image-size="88" />
    </div>

    <div class="panel compact-panel">
      <div class="panel-title"><h2>AI 总结报告</h2></div>
      <article class="markdown-body" v-html="renderedMarkdown" />
    </div>
  </section>
</template>
