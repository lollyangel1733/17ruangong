/**
 * 接口名称: 登录
 * 路径: POST /api/auth/login -> POST {apiBase}/auth/login
 * 请求体: { username: string; password: string }
 * 响应体: { success: boolean; token?: string; user?: object; message?: string }
 * 说明: 优先转发到后端，若未配置 apiBase 则使用本地 mock store。
 */
import { defineEventHandler, readBody, createError } from 'h3'
import { loginUser } from './_store'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase || ''
  const body = await readBody<{ username?: string; password?: string }>(event)
  const username = body?.username?.trim() || ''
  const password = body?.password || ''
  if (!username || !password) {
    return { success: false, message: '用户名或密码缺失' }
  }

  // 若配置了后端地址，转发保持与金属检测接口一致的路径风格
  if (apiBase) {
    const resp = await fetch(`${apiBase}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ username, password })
    })
    if (!resp.ok) {
      throw createError({ statusCode: resp.status, statusMessage: '登录接口调用失败' })
    }
    return await resp.json()
  }

  // fallback: 本地 mock
  const res = loginUser(username, password)
  if ('error' in res) {
    return { success: false, message: res.error }
  }
  return { success: true, token: res.token, user: res.user }
})
