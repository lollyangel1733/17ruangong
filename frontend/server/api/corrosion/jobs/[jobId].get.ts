/**
 * 接口名称: 查询锈蚀检测队列任务
 * 接口定义: GET /api/corrosion/jobs/:jobId -> GET {apiBase}/jobs/:jobId
 * 输入内容: 路径参数 jobId: string
 * 输出内容: JSON { status: 'queued' | 'running' | 'done' | 'error', result?: object }
 * 备注: 服务端代理转发，保持字段与后端一致。
 */
import { defineEventHandler, createError } from 'h3'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase || 'http://127.0.0.1:8000'
  const jobId = event.context.params?.jobId
  if (!jobId) {
    throw createError({ statusCode: 400, statusMessage: '缺少jobId' })
  }
  const resp = await fetch(`${apiBase}/jobs/${jobId}`)
  if (!resp.ok) {
    throw createError({ statusCode: resp.status, statusMessage: '查询任务失败' })
  }
  return await resp.json()
})
