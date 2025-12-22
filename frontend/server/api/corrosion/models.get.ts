/**
 * 接口名称: 获取模型列表
 * 接口定义: GET /api/corrosion/models -> GET {apiBase}/models
 * 输入内容: 无
 * 输出内容: JSON { success: boolean; models?: Array<{ key: string; name: string }> }
 * 备注: 通过 Nuxt 服务器转发以避免跨域。
 */
import { defineEventHandler, createError } from 'h3'

export default defineEventHandler(async () => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase || 'http://127.0.0.1:8000'
  const resp = await fetch(`${apiBase}/models`)
  if (!resp.ok) {
    throw createError({ statusCode: resp.status, statusMessage: '获取模型列表失败' })
  }
  return await resp.json()
})
