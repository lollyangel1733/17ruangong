/**
 * 接口名称: 退出登录
 * 路径: POST /api/auth/logout -> POST {apiBase}/auth/logout
 * 认证: Required
 * 响应: { success: boolean; message?: string }
 */
import { defineEventHandler, getHeader, getCookie, createError } from 'h3'

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
  if (!token) return { success: false, message: '未登录' }

  if (apiBase) {
    try {
      const resp = await fetch(`${apiBase}/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!resp.ok) {
        // 即使后端失败，前端也应清除会话
        console.warn('Backend logout failed', resp.status)
      }
    } catch (e) {
      console.warn('Backend logout error', e)
    }
  }
  
  // 无论如何返回成功，前端清除 token
  return { success: true, message: '已退出登录' }
})
