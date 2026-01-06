/**
 * 接口名称: 注册
 * 路径: POST /api/auth/register -> POST {apiBase}/auth/register
 * 请求体: { username: string; password: string; confirm?: string }
 * 响应体: { success: boolean; token?: string; user?: object; message?: string }
 * 说明: 优先转发到后端，未配置 apiBase 时使用本地 mock 存储。
 */
import { defineEventHandler, readBody, createError } from 'h3'
import { registerUser } from './_store'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase || ''
  const body = await readBody<{ username?: string; password?: string; confirm?: string }>(event)
  const username = body?.username?.trim() || ''
  const password = body?.password || ''
  const confirm = body?.confirm || password
  if (!username || !password) {
    return { success: false, message: '用户名或密码缺失' }
  }
  if (password !== confirm) {
    return { success: false, message: '两次密码不一致' }
  }

  if (apiBase) {
    const resp = await fetch(`${apiBase}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ username, password, confirm })
    })
    if (!resp.ok) {
      throw createError({ statusCode: resp.status, statusMessage: '注册接口调用失败' })
    }
    return await resp.json()
  }

  const res = registerUser(username, password)
  if ('error' in res) {
    return { success: false, message: res.error }
  }
  return { success: true, token: res.token, user: res.user }
})
