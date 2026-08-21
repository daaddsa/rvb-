/**
 * router/index.ts — Vue Router 路由配置文件
 * 定义应用的前端路由规则，将 URL 路径映射到对应的页面组件。
 * 使用 HTML5 History 模式（无 # 号），支持动态路由参数。
 */

import { createRouter, createWebHistory } from 'vue-router'
import WorkspaceView from '@/views/WorkspaceView.vue' // 工作区主页面组件（唯一页面）

// 创建路由实例
const router = createRouter({
  // 使用 HTML5 History 模式，URL 中不含 # 号
  history: createWebHistory(),
  routes: [
    {
      // 路由路径：根路径 '/' → 跳转到工作区主页面
      path: '/',
      // 路由名称，用于编程式导航（如 router.push({ name: 'workspace' })）
      name: 'workspace',
      // 匹配该路由时渲染的组件
      component: WorkspaceView,
    },
    {
      // 路由路径：'/tasks/:taskId' → 带动态参数的任务详情页，:taskId 为任务 ID 占位符
      // 跳转目标：仍渲染 WorkspaceView，通过路由参数 taskId 加载对应任务数据
      path: '/tasks/:taskId',
      // 路由名称，用于编程式导航
      name: 'task-detail',
      // 匹配该路由时渲染的组件
      component: WorkspaceView,
      // 将路由参数（taskId）作为 props 传递给组件，组件中可直接通过 props.taskId 获取
      props: true,
    },
  ],
})

// 导出路由实例，供 main.ts 注册使用
export default router