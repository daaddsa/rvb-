/**
 * vite.config.ts — Vite 构建工具配置文件
 * 配置开发服务器代理、构建选项、插件和路径别名。
 * 开发环境下将 /api 和 /health 请求代理到后端 127.0.0.1:8000。
 */

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue' // Vue 3 单文件组件编译插件
import path from 'path' // Node.js 路径处理模块
import Inspector from 'unplugin-vue-dev-locator/vite' // Vue 开发调试定位插件
import traeBadgePlugin from 'vite-plugin-trae-solo-badge' // Trae 徽章插件

// Vite 配置文档：https://vite.dev/config/
export default defineConfig({
  // ==================== 开发服务器配置 ====================
  server: {
    proxy: {
      // 代理 /api 路径的请求到后端服务器
      '/api': {
        target: 'http://127.0.0.1:8000', // 后端地址
        ws: true,                          // 支持 WebSocket 代理
      },
      // 代理 /health 健康检查请求到后端服务器
      '/health': {
        target: 'http://127.0.0.1:8000',
      },
    },
  },
  // ==================== 构建配置 ====================
  build: {
    sourcemap: 'hidden', // 生成 sourcemap 但不在生产代码中引用（用于错误追踪）
  },
  // ==================== 插件列表 ====================
  plugins: [
    vue(),            // Vue 3 单文件组件编译
    Inspector(),      // Vue 开发调试定位（点击页面元素跳转到源码）
    traeBadgePlugin({ // Trae 徽章：生产环境右下角显示品牌标识
      variant: 'dark',                                     // 深色变体
      position: 'bottom-right',                            // 右下角位置
      prodOnly: true,                                      // 仅生产环境显示
      clickable: true,                                     // 可点击
      clickUrl: 'https://www.trae.ai/solo?showJoin=1',    // 点击跳转链接
      autoTheme: true,                                     // 自动跟随主题
      autoThemeTarget: '#app',                             // 主题跟随目标元素
    }),
  ],
  // ==================== 路径解析配置 ====================
  resolve: {
    alias: {
      // 定义 @ 别名指向 src 目录，方便模块导入（如 import X from '@/stores/task'）
      '@': path.resolve(__dirname, './src'),
    },
  },
})