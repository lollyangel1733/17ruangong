/**
 * 接口名称: 锈蚀检测（同步）
 * 接口定义: POST /api/corrosion/detect -> POST {apiBase}/detect
 * 输入内容: FormData { file: File; model: string; conf: number; iou: number; imgsz: number; max_det: number }
 * 输出内容: JSON { success: boolean; image_base64: string; metrics: object; params: object }
 * 备注: 服务端代理转发，避免浏览器跨域；需后端 Flask 保持原有字段。
 */
import { defineEventHandler, readMultipartFormData, createError } from 'h3'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase || 'http://127.0.0.1:8000'
  const form = await readMultipartFormData(event)
  if (!form) {
    throw createError({ statusCode: 400, statusMessage: '未收到上传数据' })
  }

  const fd = new FormData()
  for (const part of form) {
    if (part.filename) {
      const blob = new Blob([new Uint8Array(part.data)], { type: part.type || 'application/octet-stream' })
      fd.append(part.name || 'file', blob, part.filename)
    } else {
      fd.append(part.name || 'model', part.data.toString())
    }
  }

  const resp = await fetch(`${apiBase}/detect`, { method: 'POST', body: fd })
  if (!resp.ok) {
    throw createError({ statusCode: resp.status, statusMessage: '后端检测接口调用失败' })
  }
  return await resp.json()
})
