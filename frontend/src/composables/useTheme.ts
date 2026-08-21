/**
 * composables/useTheme.ts — 主题切换组合式函数（Composable）
 * 提供浅色/深色主题切换功能，支持：
 *   1. 读取 localStorage 中保存的主题偏好
 *   2. 回退到系统配色方案偏好（prefers-color-scheme）
 *   3. 通过 CSS 类名切换主题样式
 * 导出 theme（当前主题 ref）、toggleTheme（切换函数）、isDark（是否深色 computed）
 */

import { ref, watchEffect, onMounted, computed } from 'vue'

/** 主题类型：'light'（浅色）| 'dark'（深色） */
type Theme = 'light' | 'dark'

/**
 * 主题管理组合式函数
 * 使用方式：在 Vue 组件 setup 中调用 const { theme, toggleTheme, isDark } = useTheme()
 *
 * @returns { theme, toggleTheme, isDark } 主题状态与操作方法
 */
export function useTheme() {
  /** 当前主题，响应式 ref，初始值为 'light'（挂载后会被覆盖为实际偏好） */
  const theme = ref<Theme>('light')

  /**
   * 获取用户偏好的主题
   * 优先级：localStorage 存储 > 系统配色方案
   *
   * @returns 用户偏好的主题类型
   */
  const getPreferredTheme = (): Theme => {
    // 尝试从 localStorage 读取已保存的主题设置
    const saved = localStorage.getItem('theme') as Theme | null
    // 如果已保存且为有效值，直接返回
    if (saved === 'light' || saved === 'dark') return saved
    // 否则检测系统配色方案偏好：深色 → dark，浅色 → light
    return window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light'
  }

  /**
   * 应用主题到 DOM
   * 移除旧主题类名，添加新主题类名，并保存到 localStorage
   *
   * @param t - 要应用的主题类型
   */
  const applyTheme = (t: Theme) => {
    // 移除 html 元素上的旧主题类名
    document.documentElement.classList.remove('light', 'dark')
    // 添加新主题类名
    document.documentElement.classList.add(t)
    // 将主题偏好保存到 localStorage，下次访问时恢复
    localStorage.setItem('theme', t)
  }

  /**
   * 切换主题
   * 当前为浅色 → 切换为深色；当前为深色 → 切换为浅色
   */
  const toggleTheme = () => {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  // 组件挂载后，读取用户偏好并应用主题
  onMounted(() => {
    theme.value = getPreferredTheme()
    applyTheme(theme.value)
  })

  // 监听 theme 变化，自动应用新主题
  watchEffect(() => {
    applyTheme(theme.value)
  })

  // 导出响应式数据和方法
  return {
    /** 当前主题 ref */
    theme,
    /** 切换主题的方法 */
    toggleTheme,
    /** 是否为深色主题（computed 计算属性） */
    isDark: computed(() => theme.value === 'dark'),
  }
}