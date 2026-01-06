/**
 * 接口名称: 锈蚀检测入队
 * 路径: POST /api/corrosion/enqueue -> POST {apiBase}/enqueue
 * 输入: FormData { file, model, conf, iou, imgsz, max_det }
 * 输出: { success: boolean; job_id?: string }
 * 说明: 按用户鉴权，队列记录与账户关联；未配置 apiBase 时使用本地 mock 并立即完成。
 */
import { defineEventHandler, readMultipartFormData, createError } from 'h3'
import { readUserFromEvent, createMockJob } from './_store'

const readToken = (event: any) => {
  const auth = event.req.headers['authorization'] || ''
  if (typeof auth === 'string' && auth.toLowerCase().startsWith('bearer ')) return auth.slice(7)
  const cookieToken = event.req.headers.cookie?.match(/auth_token=([^;]+)/)?.[1]
  return cookieToken || ''
}

export default defineEventHandler(async (event) => {
  const user = readUserFromEvent(event)
  if (!user) {
    throw createError({ statusCode: 401, statusMessage: '未登录，无法入队' })
  }

  const form = await readMultipartFormData(event)
  if (!form) {
    throw createError({ statusCode: 400, statusMessage: '未收到上传数据' })
  }

  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase || ''
  const params: any = { model: '', conf: 0.25, iou: 0.45, imgsz: 640, max_det: 300 }
  let filePart: any = null

  for (const part of form) {
    if (part.filename) {
      filePart = part
    } else {
      params[part.name || 'model'] = part.data.toString()
    }
  }

  if (!filePart) {
    throw createError({ statusCode: 400, statusMessage: '缺少文件' })
  }

  if (apiBase) {
    const fd = new FormData()
    const blob = new Blob([new Uint8Array(filePart.data)], { type: filePart.type || 'application/octet-stream' })
    fd.append(filePart.name || 'file', blob, filePart.filename)
    fd.append('model', params.model)
    fd.append('conf', String(params.conf))
    fd.append('iou', String(params.iou))
    fd.append('imgsz', String(params.imgsz))
    fd.append('max_det', String(params.max_det))

    const token = readToken(event)
    const headers: Record<string, string> = {}
    if (token) headers.Authorization = `Bearer ${token}`

    const resp = await fetch(`${apiBase}/detect/enqueue`, { method: 'POST', body: fd, headers })
    if (!resp.ok) {
      throw createError({ statusCode: resp.status, statusMessage: '后端入队接口调用失败' })
    }
    return await resp.json()
  }

  const job = createMockJob(user.id, user.username, { data: filePart.data, filename: filePart.filename }, {
    model: String(params.model || 'yolo11s.pt'),
    conf: Number(params.conf ?? 0.25),
    iou: Number(params.iou ?? 0.45),
    imgsz: Number(params.imgsz ?? 640),
    max_det: Number(params.max_det ?? 300)
  })
  return { success: true, job_id: job.id, status: job.status }
})
