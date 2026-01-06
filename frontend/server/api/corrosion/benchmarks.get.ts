/**
 * 接口名称: 模型性能对比数据
 * 接口定义: GET /api/corrosion/benchmarks -> GET {apiBase}{benchmarkPath}
 * 输入内容: 无
 * 输出内容: JSON { success: boolean; data: BenchmarkItem[] }
 * 备注: 使用 runtimeConfig.public.benchmarkPath（默认 /benchmarks）指向后端固定接口。
 */
import { defineEventHandler, createError } from 'h3'

// 前端本地 mock，当后端尚未提供 benchmarks 接口时可用
const mockData = [
  { model: 'yolo11s.pt', name: 'yolo11s (base)', map50: 0.73, map5095: 0.41, precision: 0.78, recall: 0.64, fps: 38, latency_ms: 26 },
  { model: 'yolo11n.pt', name: 'yolo11n (base)', map50: 0.68, map5095: 0.36, precision: 0.72, recall: 0.58, fps: 55, latency_ms: 18 },
  { model: 'runs/rust_yolo11s_train1/weights/best.pt', name: 'rust_yolo11s_train1', map50: 0.82, map5095: 0.49, precision: 0.80, recall: 0.69, fps: 32, latency_ms: 31 },
  { model: 'runs/rust_seg_v2/weights/best.pt', name: 'rust_seg_v2 (seg)', map50: 0.85, map5095: 0.52, precision: 0.83, recall: 0.72, fps: 24, latency_ms: 42 }
]

export default defineEventHandler(async () => {
  const config = useRuntimeConfig()
  const apiBase = config.public.apiBase || 'http://127.0.0.1:8000'
  const benchmarkPath = config.public.benchmarkPath || '/benchmarks'
  const target = `${apiBase}${benchmarkPath}`

  try {
    const resp = await fetch(target)
    if (!resp.ok) {
      throw createError({ statusCode: resp.status, statusMessage: '获取模型性能数据失败' })
    }
    return await resp.json()
  } catch (err) {
    // 后端未就绪时返回本地 mock，方便前端开发
    return { success: true, data: mockData, mock: true }
  }
})
