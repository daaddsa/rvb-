<!--
  组件名称：LeftSidebar.vue
  组件功能：左侧边栏组件，提供任务切换、快速选择、创建新任务以及当前任务参数展示功能。
  支持折叠/展开切换，折叠时仅显示图标提示。
-->
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Menu, Plus, RefreshCw, Cpu, Database, GitBranch } from 'lucide-vue-next'
import { useTaskStore } from '@/stores/task'
import type { TaskCreateRequest } from '@/types/task'

// 获取任务状态管理 store 实例
const store = useTaskStore()

// 控制创建任务对话框的显隐状态
const dialogVisible = ref(false)

// 目标智能体选项列表，用于创建任务时选择靶场智能体
const targetAgentOptions = [
  { label: '金融智能体', value: 'financial_agent' },
  { label: '客服智能体', value: 'customer_agent' },
]

// 创建任务的表单数据，使用 reactive 绑定以便双向绑定
const form = reactive<TaskCreateRequest>({
  target_agent: 'financial_agent',          // 默认选中金融智能体
  risk_types: [],                           // 风险类型列表（暂未使用）
  attack_skills: [],                        // 攻击技能列表（暂未使用）
  attack_count: 1,                          // 攻击次数
  max_rounds: 2,                            // 最大进化轮次
  use_llm: true,                            // 是否启用 LLM
  model_config: {
    target_model: 'qwen3:1.7b',             // 目标模型配置
  },
  redbench_datasets: [],                    // 选中的 RedBench 数据集列表
  matrix_version: 'ASI_2026',               // 风险矩阵版本
})

// 计算属性：获取当前选中的任务对象
const currentTask = computed(() => store.currentTask)

/**
 * 提交创建任务表单
 * 调用 store 的 submitTask 方法提交任务，关闭对话框并提示成功
 */
async function submit() {
  // 展开表单数据，深拷贝 model_config 和 redbench_datasets 避免引用污染
  await store.submitTask({
    ...form,
    model_config: { ...form.model_config },
    redbench_datasets: [...form.redbench_datasets],
  })
  dialogVisible.value = false
  ElMessage.success('任务已创建，请点击开始执行')
}
</script>

<template>
  <!-- 侧边栏根元素，根据 store 状态动态折叠 -->
  <aside class="sidebar" :class="{ collapsed: store.sidebarCollapsed }">
    <!-- 顶部区域：折叠按钮 + 品牌名称 -->
    <div class="sidebar-top">
      <button class="icon-button" aria-label="切换侧边栏" @click="store.toggleSidebar()">
        <Menu :size="18" />
      </button>
      <!-- 仅展开时显示品牌名称 -->
      <span v-if="!store.sidebarCollapsed" class="brand">红蓝对抗控制台</span>
    </div>

    <!-- 仅展开时显示任务快速切换区域 -->
    <div v-if="!store.sidebarCollapsed" class="sidebar-section">
      <div class="section-title">
        <span>任务快速切换</span>
        <!-- 刷新按钮：重新加载任务列表 -->
        <button class="ghost-button" @click="store.loadInitialData()">
          <RefreshCw :size="14" />
        </button>
      </div>
      <!-- 任务下拉选择器：可搜索，选中后切换当前任务 -->
      <el-select
        :model-value="store.currentTaskId"
        placeholder="选择任务"
        class="task-select"
        filterable
        @change="(id: string) => store.selectTask(id)"
      >
        <!-- 遍历任务列表渲染下拉选项 -->
        <el-option v-for="task in store.tasks" :key="task.id" :label="`${task.id} · ${task.status}`" :value="task.id">
          <span class="task-option">
            <!-- 状态指示点，根据任务状态动态 class -->
            <i class="status-dot" :class="task.status.toLowerCase()" />
            <span>{{ task.id }}</span>
            <small>{{ task.status }}</small>
          </span>
        </el-option>
      </el-select>
    </div>

    <!-- 折叠时显示图标提示，悬停展示 tooltip -->
    <div v-else class="collapsed-icons">
      <el-tooltip content="靶场智能体" placement="right"><Cpu :size="18" /></el-tooltip>
      <el-tooltip content="RedBench 数据集" placement="right"><Database :size="18" /></el-tooltip>
      <el-tooltip content="风险矩阵版本" placement="right"><GitBranch :size="18" /></el-tooltip>
    </div>

    <!-- 仅展开时显示当前任务参数区域 -->
    <div v-if="!store.sidebarCollapsed" class="sidebar-section params">
      <div class="section-title">当前任务参数</div>
      <!-- 有任务时展示参数详情 -->
      <template v-if="currentTask">
        <div class="param-row"><span>靶场智能体</span><strong>{{ currentTask.target_agent }}</strong></div>
        <div class="param-row"><span>最大轮次</span><strong>{{ currentTask.max_rounds }}</strong></div>
        <div class="param-row"><span>矩阵版本</span><code>{{ currentTask.matrix_version }}</code></div>
      </template>
      <!-- 无任务时显示空状态 -->
      <el-empty v-else description="暂无任务" :image-size="72" />
    </div>

    <!-- 仅展开时显示"创建新任务"按钮 -->
    <button v-if="!store.sidebarCollapsed" class="create-button" @click="dialogVisible = true">
      <Plus :size="16" /> 创建新任务
    </button>

    <!-- 创建任务对话框 -->
    <el-dialog v-model="dialogVisible" title="创建 RedBench 测试任务" width="520px">
      <el-form label-position="top">
        <!-- 目标智能体选择 -->
        <el-form-item label="目标智能体">
          <el-select v-model="form.target_agent" placeholder="请选择目标智能体">
            <!-- 遍历智能体选项 -->
            <el-option v-for="agent in targetAgentOptions" :key="agent.value" :label="agent.label" :value="agent.value" />
          </el-select>
        </el-form-item>
        <!-- 进化轮次上限输入 -->
        <el-form-item label="进化轮次上限">
          <el-input-number v-model="form.max_rounds" :min="1" :max="10" class="full-width" />
        </el-form-item>
        <!-- RedBench 数据集多选 -->
        <el-form-item label="RedBench 数据集">
          <el-select v-model="form.redbench_datasets" multiple filterable placeholder="请选择一个或多个数据集">
            <!-- 遍历 store 中的数据集列表 -->
            <el-option v-for="dataset in store.redbenchDatasets" :key="dataset" :label="dataset" :value="dataset" />
          </el-select>
        </el-form-item>
      </el-form>
      <!-- 对话框底部按钮 -->
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <!-- 创建按钮：提交时 loading 且未选数据集时禁用 -->
        <el-button type="primary" :loading="store.loading" :disabled="form.redbench_datasets.length === 0" @click="submit">创建任务</el-button>
      </template>
    </el-dialog>
  </aside>
</template>