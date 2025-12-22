/**
 * Hook 名称：useCorrosion
 * 作用：管理锈蚀检测前端状态，并调用 Nuxt API 代理转发到 Flask 后端。
 */
import { ref } from 'vue'

interface ModelItem {
  key: string
  name: string
}

interface DetectionMetrics {
  count?: number
  area_ratio?: number
  avg_conf?: number
}

interface DetectParams {
  model: string
  conf: number
  iou: number
  imgsz: number
  max_det: number
}

interface TaskItem {
  id: string
  filename: string
  mode: 'sync' | 'queue'
  status: 'pending' | 'running' | 'done' | 'error'
  message?: string
  metrics?: DetectionMetrics
}

export function useCorrosion() {
  // 使用 useState 在页面之间共享状态（任务、日志、画廊、进度）
  const models = ref<ModelItem[]>([])
  const files = ref<File[]>([])
  const busy = ref(false)
  const metrics = useState<DetectionMetrics>('corrosion-metrics', () => ({}))
  const previewSrc = useState<string>('corrosion-preview', () => '')
  const inputPreviewSrc = useState<string>('corrosion-input-preview', () => '')
  const progressText = useState<string>('corrosion-progress', () => '未开始')
  const gallery = useState<Array<{ id: string; input: string; output: string; metrics: DetectionMetrics; params: DetectParams; filename: string }>>('corrosion-gallery', () => [])
  const tasks = useState<TaskItem[]>('corrosion-tasks', () => [])
  const logs = useState<string[]>('corrosion-logs', () => [])
  const params = useState<DetectParams>('corrosion-params', () => ({ model: 'yolo11s.pt', conf: 0.25, iou: 0.45, imgsz: 640, max_det: 300 }))
  const lastParams = useState<DetectParams>('corrosion-last-params', () => ({ ...params.value }))

  const pushLog = (msg: string) => {
    const line = `${new Date().toLocaleTimeString()} - ${msg}`
    logs.value.unshift(line)
    if (logs.value.length > 100) logs.value.pop()
  }

  const fetchModels = async () => {
    try {
      const res = await $fetch<{ success: boolean; models?: ModelItem[] }>('/api/corrosion/models')
      if (res?.success && res.models?.length) {
        models.value = res.models
        // 仅在当前选择无效或为空时才回落到第一个模型，避免覆盖用户选择
        const current = params.value.model
        const hasCurrent = res.models.some((m) => m.key === current)
        if (!current || !hasCurrent) {
          params.value.model = res.models[0].key
        }
        pushLog('模型列表加载成功')
      }
      if (!res?.success) {
        console.error('加载模型列表失败', res)
        pushLog('模型列表加载失败')
      }
    } catch (e) {
      console.warn('加载模型列表失败', e)
      pushLog('模型列表加载异常')
    }
  }

  const setFiles = (list: File[]) => {
    files.value = list
    gallery.value = []
    tasks.value = []
    progressText.value = list.length ? `已选择 ${list.length} 张图片` : '未开始'
    if (list.length) {
      inputPreviewSrc.value = URL.createObjectURL(list[0])
    } else {
      inputPreviewSrc.value = ''
    }
  }

  const handleResult = (data: any, inputUrl: string, filename: string, taskId?: string) => {
    if (!data) return
    const outputUrl = data.image_base64 ? `data:image/png;base64,${data.image_base64}` : ''
    previewSrc.value = outputUrl
    inputPreviewSrc.value = inputUrl
    const m = data.metrics || {}
    const met: DetectionMetrics = {
      count: m['检测数量'] ?? m.count,
      area_ratio: m['面积比例'] ?? m.area_ratio,
      avg_conf: m['平均置信度'] ?? m.avg_conf
    }
    metrics.value = met
    const p: DetectParams = {
      model: data.params?.model ?? params.value.model,
      conf: data.params?.conf ?? params.value.conf,
      iou: data.params?.iou ?? params.value.iou,
      imgsz: data.params?.imgsz ?? params.value.imgsz,
      max_det: data.params?.max_det ?? params.value.max_det
    }
    lastParams.value = p
    console.log('检测结果', {
      filename,
      base64Length: data.image_base64 ? data.image_base64.length : 0,
      metrics: met,
      params: p
    })
    if ((met.count ?? 0) === 0) {
      progressText.value = '模型未检出目标（count=0），可尝试降低 conf 或换权重'
    }
    if (taskId) {
      const t = tasks.value.find((x: TaskItem) => x.id === taskId)
      if (t) {
        t.status = 'done'
        t.metrics = met
        t.message = '完成'
      }
    }
    pushLog(`检测成功: ${filename}, count=${met.count ?? '-'}, model=${p.model}`)
    gallery.value.unshift({
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      input: inputUrl,
      output: outputUrl,
      metrics: met,
      params: p,
      filename
    })
  }

  const startDetect = async () => {
    if (!files.value.length) return
    busy.value = true
    progressText.value = '检测中...'
    try {
      let done = 0
      for (const file of files.value) {
        const inputUrl = URL.createObjectURL(file)
        const taskId = `${Date.now()}-${Math.random().toString(16).slice(2)}`
        tasks.value.unshift({ id: taskId, filename: file.name, mode: 'sync', status: 'running' })
        const form = new FormData()
        form.append('file', file)
        form.append('model', params.value.model)
        form.append('conf', String(params.value.conf))
        form.append('iou', String(params.value.iou))
        form.append('imgsz', String(params.value.imgsz))
        form.append('max_det', String(params.value.max_det))

        try {
          const res = await $fetch<any>('/api/corrosion/detect', {
            method: 'POST',
            body: form
          })
          if (res?.success) {
            handleResult(res, inputUrl, file.name, taskId)
          } else {
            console.error('检测失败', res)
            progressText.value = res?.message || '检测失败'
            const t = tasks.value.find((x: TaskItem) => x.id === taskId)
            if (t) {
              t.status = 'error'
              t.message = res?.message || '检测失败'
            }
            pushLog(`检测失败: ${file.name}`)
          }
        } catch (err) {
          console.error('检测请求异常', err)
          progressText.value = '请求异常，查看控制台'
          const t = tasks.value.find((x: TaskItem) => x.id === taskId)
          if (t) {
            t.status = 'error'
            t.message = '请求异常'
          }
          pushLog(`请求异常: ${file.name}`)
        }
        done += 1
        progressText.value = `完成 ${done}/${files.value.length}`
      }
      progressText.value = '完成'
    } finally {
      busy.value = false
    }
  }

  const startQueue = async () => {
    if (!files.value.length) return
    busy.value = true
    try {
      progressText.value = '检测中...'
      let done = 0
      for (const file of files.value) {
        const inputUrl = URL.createObjectURL(file)
        inputPreviewSrc.value = inputUrl
        const taskId = `${Date.now()}-${Math.random().toString(16).slice(2)}`
        tasks.value.unshift({ id: taskId, filename: file.name, mode: 'queue', status: 'running' })

        const form = new FormData()
        form.append('file', file)
        form.append('model', params.value.model)
        form.append('conf', String(params.value.conf))
        form.append('iou', String(params.value.iou))
        form.append('imgsz', String(params.value.imgsz))
        form.append('max_det', String(params.value.max_det))

        let jobId: string | undefined
        try {
          const enq = await $fetch<{ success: boolean; job_id?: string; message?: string }>('/api/corrosion/enqueue', {
            method: 'POST',
            body: form
          })
          if (!enq?.success || !enq.job_id) {
            console.error('入队失败', enq)
            const t = tasks.value.find((x: TaskItem) => x.id === taskId)
            if (t) { t.status = 'error'; t.message = enq?.message || '入队失败' }
            pushLog(`入队失败: ${file.name}`)
            continue
          }
          jobId = enq.job_id
          pushLog(`已入队: ${file.name}, job=${jobId}`)
        } catch (err) {
          console.error('入队请求异常', err)
          const t = tasks.value.find((x: TaskItem) => x.id === taskId)
          if (t) { t.status = 'error'; t.message = '入队异常' }
          pushLog(`入队异常: ${file.name}`)
          continue
        }

        const poll = async (): Promise<void> => {
          const jr = await $fetch<any>(`/api/corrosion/jobs/${jobId}`)
          if (jr?.status === 'done' && jr.result?.success) {
            handleResult(jr.result, inputUrl, file.name, taskId)
            pushLog(`队列完成: ${file.name}`)
            return
          }
          if (jr?.status === 'error') {
            console.error('队列任务错误', jr)
            const t = tasks.value.find((x: TaskItem) => x.id === taskId)
            if (t) { t.status = 'error'; t.message = jr?.message || '队列任务错误' }
            pushLog(`队列任务错误: ${file.name}`)
            return
          }
          await new Promise((r) => setTimeout(r, 800))
          return poll()
        }

        await poll()
        done += 1
        progressText.value = `完成 ${done}/${files.value.length}`
      }
      progressText.value = '完成'
    } finally {
      busy.value = false
    }
  }

  return {
    models,
    files,
    params,
    busy,
    metrics,
    previewSrc,
    inputPreviewSrc,
    lastParams,
    progressText,
    gallery,
    tasks,
    logs,
    fetchModels,
    setFiles,
    startDetect,
    startQueue
  }
}
