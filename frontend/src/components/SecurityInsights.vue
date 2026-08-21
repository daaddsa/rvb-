<!--
  组件名称：SecurityInsights.vue
  组件功能：安全洞察组件，展示单次攻击计算结果（检测阶段、动作、原因）、
  最终总结报告（整体指标柱状图 + 风险覆盖/拆解 JSON），以及 AI 生成的
  Markdown 总结报告。使用 ECharts 渲染柱状图和 MarkdownIt 渲染报告。
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import MarkdownIt from 'markdown-it'
import type { AttackCase, DetectionResult, EvaluationReport } from '@/types/task'

/**
 * Props 定义
 * report: 最终评估报告，包含整体指标和总结
 * attackCases: 攻击用例列表
 * detectionResults: 检测结果列表
 */
const props = defineProps<{
  report: EvaluationReport | null
  attackCases: AttackCase[]
  detectionResults: DetectionResult[]
}>()

// ECharts 图表容器的 DOM 引用
const chartRef = ref<HTMLDivElement | null>(null)
// ECharts 实例，用于图表渲染和销毁
let chart: echarts.ECharts | null = null
// MarkdownIt 实例，用于渲染 AI 总结报告为 HTML
const md = new MarkdownIt({ html: false, breaks: true })

/**
 * 计算属性：构建攻击摘要列表
 * 遍历每个攻击用例，关联其检测结果，提取关键信息
 */
const attackSummaries = computed(() =>
  props.attackCases.map((attackCase, index) => {
    // 筛选与该攻击用例关联的检测结果
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

/**
 * 计算属性：最终评估指标列表
 * 从报告对象中提取各项指标并格式化为百分比
 */
const finalMetrics = computed(() => [
  { label: '攻击总数', value: props.report?.total_attacks ?? 0 },
  { label: '攻击成功率', value: percent(props.report?.attack_success_rate) },
  { label: '检测率', value: percent(props.report?.detection_rate) },
  { label: '阻断率', value: percent(props.report?.block_rate) },
  { label: '误报率', value: percent(props.report?.false_positive_rate) },
  { label: '漏报率', value: percent(props.report?.false_negative_rate) },
])

// 计算属性：生成 Markdown 格式的总结报告文本
const markdown = computed(() => {
  if (!props.report) return '所有攻击结束后生成最终总结报告。'
  return `# 本次测试整体结论\n\n${props.report.summary || '暂无总结。'}\n\n## 整改建议\n\n${props.report.recommendations || '暂无整改建议。'}`
})

// 计算属性：将 Markdown 文本渲染为 HTML
const renderedMarkdown = computed(() => md.render(markdown.value))

// 监听 report 变化，重新渲染图表（深度监听）
watch(() => props.report, renderChart, { deep: true })

// 组件挂载时渲染图表
onMounted(renderChart)
// 组件卸载前销毁 ECharts 实例，释放内存
onBeforeUnmount(() => chart?.dispose())

/**
 * 将数值格式化为百分比字符串
 * @param value 小数值（如 0.85 表示 85%）
 * @returns 格式化后的百分比字符串，如 "85.00%"
 */
function percent(value?: number | null) {
  if (typeof value !== 'number') return '0.00%'
  return `${(value * 100).toFixed(2)}%`
}

/**
 * 渲染 ECharts 柱状图
 * 展示攻击成功率、检测率、阻断率、误报率、漏报率五项指标
 * 如果 chartRef 不存在则直接返回
 */
function renderChart() {
  if (!chartRef.value) return
  // 惰性初始化 ECharts 实例
  chart = chart ?? echarts.init(chartRef.value)
  const report = props.report
  chart.setOption({
    tooltip: { trigger: 'axis' },                     // 坐标轴触发提示框
    grid: { left: 32, right: 16, top: 24, bottom: 28 }, // 图表内边距
    xAxis: { type: 'category', data: ['攻击成功率', '检测率', '阻断率', '误报率', '漏报率'] }, // X 轴类别
    yAxis: { type: 'value', min: 0, max: 1 },         // Y 轴范围 0~1
    series: [
      {
        type: 'bar',                                  // 柱状图类型
        data: [
          report?.attack_success_rate ?? 0,
          report?.detection_rate ?? 0,
          report?.block_rate ?? 0,
          report?.false_positive_rate ?? 0,
          report?.false_negative_rate ?? 0,
        ],
        itemStyle: { color: '#0969da' },              // 柱状图颜色
      },
    ],
  })
}
</script>

<template>
  <section class="insights-left">
    <!-- 单次攻击计算结果面板 -->
    <div class="panel compact-panel">
      <div class="panel-title">
        <div>
          <h2>单次攻击计算结果</h2>
          <p>每完成一次攻击，就展示该次攻击的检测阶段、动作和原因。</p>
        </div>
      </div>
      <!-- 攻击摘要卡片列表 -->
      <div class="attack-summary-list">
        <!-- 遍历攻击摘要列表渲染 -->
        <article v-for="item in attackSummaries" :key="item.id" class="attack-summary-card">
          <div class="attack-summary-head">
            <strong>{{ item.title }}</strong>
            <!-- 动作状态标签 -->
            <span class="run-status" :class="item.action">{{ item.action }}</span>
          </div>
          <!-- 摘要字段 -->
          <div class="summary-fields">
            <span>风险：{{ item.risk_type }}</span>
            <span>阶段：{{ item.stage }}</span>
            <span>置信度：{{ item.confidence }}</span>
            <span>阻断：{{ item.blocked ? '是' : '否' }}</span>
          </div>
          <!-- 检测原因描述 -->
          <p>{{ item.reason }}</p>
        </article>
        <!-- 无攻击摘要时显示空状态 -->
        <el-empty v-if="attackSummaries.length === 0" description="暂无单次攻击结果" :image-size="88" />
      </div>
    </div>

    <!-- 最终总结报告面板 -->
    <div class="panel compact-panel final-report-panel">
      <div class="panel-title">
        <div>
          <h2>最终总结报告</h2>
          <p>所有攻击结束后再汇总生成整体指标和 AI 总结。</p>
        </div>
      </div>
      <!-- 有报告时展示指标和图表 -->
      <template v-if="report">
        <!-- 指标卡片网格 -->
        <div class="metric-grid final-metrics">
          <!-- 遍历 finalMetrics 渲染指标卡片 -->
          <div v-for="metric in finalMetrics" :key="metric.label" class="metric-card">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
          </div>
        </div>
        <!-- ECharts 柱状图容器 -->
        <div ref="chartRef" class="chart" />
        <!-- JSON 数据网格：风险覆盖 + 风险拆解 -->
        <div class="json-grid">
          <pre>{{ JSON.stringify(report.risk_coverage ?? {}, null, 2) }}</pre>
          <pre>{{ JSON.stringify(report.risk_breakdown ?? {}, null, 2) }}</pre>
        </div>
      </template>
      <!-- 无报告时显示空状态 -->
      <el-empty v-else description="等待全部攻击结束后生成报告" :image-size="88" />
    </div>

    <!-- AI 总结报告面板 -->
    <div class="panel compact-panel">
      <div class="panel-title"><h2>AI 总结报告</h2></div>
      <!-- 使用 v-html 渲染 Markdown 内容 -->
      <article class="markdown-body" v-html="renderedMarkdown" />
    </div>
  </section>
</template>