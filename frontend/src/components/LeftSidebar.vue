<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Menu, Plus, RefreshCw, Cpu, Database, GitBranch } from 'lucide-vue-next'
import { useTaskStore } from '@/stores/task'
import type { TaskCreateRequest } from '@/types/task'

const store = useTaskStore()
const dialogVisible = ref(false)
const targetAgentOptions = [
  { label: '金融智能体', value: 'financial_agent' },
  { label: '客服智能体', value: 'customer_agent' },
]

const form = reactive<TaskCreateRequest>({
  target_agent: 'financial_agent',
  risk_types: [],
  attack_skills: [],
  attack_count: 1,
  max_rounds: 2,
  use_llm: true,
  model_config: {
    target_model: 'qwen3:1.7b',
  },
  redbench_datasets: [],
  matrix_version: 'ASI_2026',
})

const currentTask = computed(() => store.currentTask)

async function submit() {
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
  <aside class="sidebar" :class="{ collapsed: store.sidebarCollapsed }">
    <div class="sidebar-top">
      <button class="icon-button" aria-label="切换侧边栏" @click="store.toggleSidebar()">
        <Menu :size="18" />
      </button>
      <span v-if="!store.sidebarCollapsed" class="brand">红蓝对抗控制台</span>
    </div>

    <div v-if="!store.sidebarCollapsed" class="sidebar-section">
      <div class="section-title">
        <span>任务快速切换</span>
        <button class="ghost-button" @click="store.loadInitialData()">
          <RefreshCw :size="14" />
        </button>
      </div>
      <el-select
        :model-value="store.currentTaskId"
        placeholder="选择任务"
        class="task-select"
        filterable
        @change="(id: string) => store.selectTask(id)"
      >
        <el-option v-for="task in store.tasks" :key="task.id" :label="`${task.id} · ${task.status}`" :value="task.id">
          <span class="task-option">
            <i class="status-dot" :class="task.status.toLowerCase()" />
            <span>{{ task.id }}</span>
            <small>{{ task.status }}</small>
          </span>
        </el-option>
      </el-select>
    </div>

    <div v-else class="collapsed-icons">
      <el-tooltip content="靶场智能体" placement="right"><Cpu :size="18" /></el-tooltip>
      <el-tooltip content="RedBench 数据集" placement="right"><Database :size="18" /></el-tooltip>
      <el-tooltip content="风险矩阵版本" placement="right"><GitBranch :size="18" /></el-tooltip>
    </div>

    <div v-if="!store.sidebarCollapsed" class="sidebar-section params">
      <div class="section-title">当前任务参数</div>
      <template v-if="currentTask">
        <div class="param-row"><span>靶场智能体</span><strong>{{ currentTask.target_agent }}</strong></div>
        <div class="param-row"><span>最大轮次</span><strong>{{ currentTask.max_rounds }}</strong></div>
        <div class="param-row"><span>矩阵版本</span><code>{{ currentTask.matrix_version }}</code></div>
      </template>
      <el-empty v-else description="暂无任务" :image-size="72" />
    </div>

    <button v-if="!store.sidebarCollapsed" class="create-button" @click="dialogVisible = true">
      <Plus :size="16" /> 创建新任务
    </button>

    <el-dialog v-model="dialogVisible" title="创建 RedBench 测试任务" width="520px">
      <el-form label-position="top">
        <el-form-item label="目标智能体">
          <el-select v-model="form.target_agent" placeholder="请选择目标智能体">
            <el-option v-for="agent in targetAgentOptions" :key="agent.value" :label="agent.label" :value="agent.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="进化轮次上限">
          <el-input-number v-model="form.max_rounds" :min="1" :max="10" class="full-width" />
        </el-form-item>
        <el-form-item label="RedBench 数据集">
          <el-select v-model="form.redbench_datasets" multiple filterable placeholder="请选择一个或多个数据集">
            <el-option v-for="dataset in store.redbenchDatasets" :key="dataset" :label="dataset" :value="dataset" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="store.loading" :disabled="form.redbench_datasets.length === 0" @click="submit">创建任务</el-button>
      </template>
    </el-dialog>
  </aside>
</template>
