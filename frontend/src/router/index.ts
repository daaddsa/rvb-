import { createRouter, createWebHistory } from 'vue-router'
import WorkspaceView from '@/views/WorkspaceView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'workspace',
      component: WorkspaceView,
    },
    {
      path: '/tasks/:taskId',
      name: 'task-detail',
      component: WorkspaceView,
      props: true,
    },
  ],
})

export default router
