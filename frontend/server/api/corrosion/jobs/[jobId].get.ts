/**
 * 接口名称: 查询锈蚀检测队列任务
 * 路径: GET /api/corrosion/jobs/:jobId -> GET {apiBase}/jobs/:jobId
 * 输入: jobId 路径参数
 * 输出: { status: 'queued' | 'running' | 'done' | 'error', result?: object }
 * 说明: 按用户鉴权，任务归属与账户关联；未配置 apiBase 时读取本地 mock。
 */
import { defineEventHandler, createError } from 'h3'
import { readUserFromEvent, getJobById } from '../_store'

const readToken = (event: any) => {
  const auth = event.req.headers['authorization'] || ''
  if (typeof auth === 'string' && auth.toLowerCase().startsWith('bearer ')) return auth.slice(7)
  const cookieToken = event.req.headers.cookie?.match(/auth_token=([^;]+)/)?.[1]
  return cookieToken || ''
}

export default defineEventHandler(async (event) => {
  const user = readUserFromEvent(event)
  if (!user) {
    throw createError({ statusCode: 401, statusMessage: '未登录，无法查询任务' })
  }

  const jobId = event.context.params?.jobId
  if (!jobId) {
    throw createError({ statusCode: 400, statusMessage: '缺少jobId' })
  }

  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase || ''
  if (apiBase) {
    const token = readToken(event)
    const headers: Record<string, string> = {}
    if (token) headers.Authorization = `Bearer ${token}`
    const resp = await fetch(`${apiBase}/jobs/${jobId}`, { headers })
    if (!resp.ok) {
      throw createError({ statusCode: resp.status, statusMessage: '查询任务失败' })
    }
    return await resp.json()
  }

  const job = getJobById(jobId, user.id)
  if (!job) {
    return { status: 'error', message: '未找到任务或无权限' }
  }
  return { job_id: jobId, status: job.status, result: job.result, message: job.message }
})
