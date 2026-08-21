/**
 * main.ts — Vue 应用入口文件
 * 负责创建 Vue 应用实例、注册全局插件（Pinia 状态管理、Vue Router 路由、Element Plus UI 组件库）、
 * 引入全局样式，并将应用挂载到 DOM 中的 #app 节点。
 */

import { createApp } from 'vue' // Vue 3 应用创建函数
import { createPinia } from 'pinia' // Pinia 状态管理库
import ElementPlus from 'element-plus' // Element Plus UI 组件库
import 'element-plus/dist/index.css' // Element Plus 全局样式
import 'highlight.js/styles/github-dark.css' // 代码高亮主题样式（GitHub Dark 风格）
import './style.css' // 项目自定义全局样式（含 Tailwind CSS）
import App from './App.vue' // 根组件
import router from './router' // 路由配置

// 创建 Vue 应用实例，传入根组件
const app = createApp(App)

// 注册 Pinia 状态管理插件（全局状态管理）
app.use(createPinia())
// 注册 Vue Router 路由插件（页面导航）
app.use(router)
// 注册 Element Plus 组件库（UI 组件）
app.use(ElementPlus)

// 将应用挂载到 index.html 中 id="app" 的 DOM 元素上
app.mount('#app')