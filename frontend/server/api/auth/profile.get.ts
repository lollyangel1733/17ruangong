/**
 * 接口名称: 获取当前用户
 * 路径: GET /api/auth/profile -> GET {apiBase}/auth/profile
 * 请求头: Authorization: Bearer <token> 或 Cookie auth_token
 * 响应体: { success: boolean; user?: object; message?: string }
 */
import { defineEventHandler, getCookie, getHeader, createError } from 'h3'
import { findByToken } from './_store'

const readToken = (event: any) => {
  const auth = getHeader(event, 'authorization') || ''
  if (auth.toLowerCase().startsWith('bearer ')) return auth.slice(7)
  const cookieToken = getCookie(event, 'auth_token')
  return cookieToken || ''
}

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase || ''
  const token = readToken(event)
  if (!token) return { success: false, message: '未登录或 token 缺失' }

  if (apiBase) {
    const resp = await fetch(`${apiBase}/auth/profile`, {
      headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' }
    })
    if (!resp.ok) {
      throw createError({ statusCode: resp.status, statusMessage: '获取用户信息失败' })
    }
    return await resp.json()
  }

  const user = findByToken(token)
  if (!user) {
    return { success: false, message: '未登录或 token 失效' }
  }
  return { success: true, user }
})
