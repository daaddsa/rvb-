/**
 * lib/utils.ts — 通用工具函数
 * 提供项目中复用的工具函数，目前包含 CSS 类名合并工具。
 */

import { clsx, type ClassValue } from "clsx" // 条件类名拼接库
import { twMerge } from "tailwind-merge" // Tailwind CSS 类名智能合并库（解决冲突）

/**
 * 合并 CSS 类名
 * 将多个类名参数（支持条件类名、数组等）合并为单个字符串，并自动处理 Tailwind CSS 类名冲突。
 * 例如：cn('px-4', false && 'hidden', 'py-2') → 'px-4 py-2'
 *
 * @param inputs - 可变参数，每个参数可以是字符串、对象、数组等 ClassValue 类型
 * @returns 合并后的 CSS 类名字符串
 */
export function cn(...inputs: ClassValue[]) {
  // 先用 clsx 拼接类名，再用 twMerge 处理 Tailwind 冲突
  return twMerge(clsx(inputs))
}