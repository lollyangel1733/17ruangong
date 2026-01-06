import { jsPDF } from 'jspdf'

interface ReportItem {
  filename: string
  input: string
  output: string
  params: any
  metrics: any
  batchId?: string
  batchOrder?: number
}

const REPORT_SEQ_KEY = 'corrosion-report-seq'

function nextReportSeq(): number {
  try {
    const raw = localStorage.getItem(REPORT_SEQ_KEY)
    const current = raw ? parseInt(raw, 10) || 0 : 0
    const next = current + 1
    localStorage.setItem(REPORT_SEQ_KEY, String(next))
    return next
  } catch {
    // 若 localStorage 不可用则退化为时间戳，但仍返回数字便于编号
    return Math.floor(Date.now() / 1000)
  }
}

function padSeq(seq: number, width = 4): string {
  return seq.toString().padStart(width, '0')
}

async function ensureCJKFont(pdf: jsPDF): Promise<boolean> {
  // 若已加载则直接返回
  if ((pdf as any)._cjkLoaded) return true

  const cacheKey = 'corrosion-font-noto-sc'
  const sources = [
    '/fonts/NotoSansSC-Regular.ttf',
    'https://unpkg.com/@fontsource/noto-sans-sc/files/noto-sans-sc-chinese-simplified-400-normal.ttf'
  ]

  // 先尝试从 sessionStorage 拿缓存的 base64，避免重复 fetch
  const cached = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem(cacheKey) : null
  if (cached) {
    try {
      pdf.addFileToVFS('NotoSansSC-Regular.ttf', cached)
      pdf.addFont('NotoSansSC-Regular.ttf', 'NotoSansSC', 'normal')
      pdf.setFont('NotoSansSC', 'normal')
      ;(pdf as any)._cjkLoaded = true
      return true
    } catch (e) {
      console.warn('Cached font load failed, will refetch', e)
    }
  }

  for (const src of sources) {
    try {
      const res = await fetch(src)
      if (!res.ok) throw new Error(`font fetch failed: ${res.status}`)
      const buf = await res.arrayBuffer()
      const base64 = bufferToBase64(buf)
      pdf.addFileToVFS('NotoSansSC-Regular.ttf', base64)
      pdf.addFont('NotoSansSC-Regular.ttf', 'NotoSansSC', 'normal')
      pdf.setFont('NotoSansSC', 'normal')
      ;(pdf as any)._cjkLoaded = true
      if (typeof sessionStorage !== 'undefined') {
        sessionStorage.setItem(cacheKey, base64)
      }
      return true
    } catch (e) {
      console.warn('CJK font fetch failed', src, e)
      continue
    }
  }

  console.warn('CJK font unavailable, fallback to Helvetica')
  return false
}

function bufferToBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

export async function generatePDFReport(items: ReportItem[], chartImages?: { pie?: string, bar?: string }) {
  if (!items.length) return

  const reportSeq = nextReportSeq()
  const today = new Date()
  const year = today.getFullYear()
  const m = String(today.getMonth() + 1).padStart(2, '0')
  const d = String(today.getDate()).padStart(2, '0')
  const reportId = `R${year}${m}${d}${padSeq(reportSeq)}`

  const pdf = new jsPDF('p', 'mm', 'a4')
  const hasCJK = await ensureCJKFont(pdf)
  if (!hasCJK) pdf.setFont('helvetica', 'normal')
  const pageWidth = pdf.internal.pageSize.getWidth()
  const pageHeight = pdf.internal.pageSize.getHeight()
  const margin = 10
  const contentWidth = pageWidth - margin * 2

  let y = margin

  // 标题与报告编号
  pdf.setFontSize(18)
  pdf.text('Corrosion Detection Report', pageWidth / 2, y, { align: 'center' })
  y += 12

  pdf.setFontSize(12)
  pdf.text(`Report ID: ${reportId}`, margin, y)
  y += 8

  // 日期与摘要
  pdf.setFontSize(10)
  pdf.text(`Date: ${new Date().toLocaleString()}`, margin, y)
  y += 8
  pdf.text(`Total Images: ${items.length}`, margin, y)
  y += 12

  // 图表（如果提供）
  if (chartImages) {
    const chartHeight = 70
    const chartWidth = (contentWidth / 2) - 5
    
    try {
      if (chartImages.pie) {
        pdf.addImage(chartImages.pie, 'PNG', margin, y, chartWidth, chartHeight)
      }
      if (chartImages.bar) {
        pdf.addImage(chartImages.bar, 'PNG', margin + chartWidth + 10, y, chartWidth, chartHeight)
      }
      if (chartImages.pie || chartImages.bar) {
        y += chartHeight + 10
      }
    } catch (e) {
      console.error('Error adding charts to PDF', e)
    }
  }

  // 按 batch 分组，保持首次出现的顺序
  type BatchGroup = { id: string; items: ReportItem[]; orderHint: number }
  const batchList: BatchGroup[] = []
  const map = new Map<string, BatchGroup>()
  for (const item of items) {
    const bid = item.batchId || 'N/A'
    let group = map.get(bid)
    if (!group) {
      group = { id: bid, items: [], orderHint: Number.POSITIVE_INFINITY }
      map.set(bid, group)
      batchList.push(group)
    }
    group.items.push(item)
    if (typeof item.batchOrder === 'number') {
      group.orderHint = Math.min(group.orderHint, item.batchOrder)
    }
  }

  for (let b = 0; b < batchList.length; b++) {
    const bid = batchList[b].id
    const list = batchList[b].items
    const labelNumber = isFinite(batchList[b].orderHint) ? (batchList[b].orderHint as number) : b + 1

    // 批次标题
    pdf.setFontSize(13)
    if (!hasCJK) pdf.setFont('helvetica', 'bold')
    else pdf.setFont('NotoSansSC', 'normal')
    const batchLabel = bid !== 'N/A' ? bid : `Batch-${padSeq(labelNumber, 2)}`
    const batchTitle = hasCJK
      ? `批次 #${padSeq(labelNumber, 2)} (${batchLabel})`
      : `Batch #${padSeq(labelNumber, 2)} (${batchLabel})`
    pdf.text(batchTitle, margin, y)
    if (!hasCJK) pdf.setFont('helvetica', 'normal')
    else pdf.setFont('NotoSansSC', 'normal')
    y += 8

    for (let i = 0; i < list.length; i++) {
      const item = list[i]

      // 检查是否需要新页面
      if (y > pageHeight - 100) {
        pdf.addPage()
        y = margin
      }

      const safeBatch = batchLabel.replace(/\s+/g, '_')
      const itemSeqLabel = `${reportId}-B${padSeq(labelNumber, 2)}-${padSeq(i + 1, 2)}-${safeBatch}`

      // 编号
      pdf.setFontSize(12)
      if (!hasCJK) pdf.setFont('helvetica', 'bold')
      else pdf.setFont('NotoSansSC', 'normal')
      pdf.text(`ID: ${itemSeqLabel}`, margin, y)
      if (!hasCJK) pdf.setFont('helvetica', 'normal')
      else pdf.setFont('NotoSansSC', 'normal')
      y += 6

      // 文件名
      pdf.setFontSize(9)
      pdf.text(`File: ${item.filename}`, margin, y)
      y += 8

      // 图像
      const imgHeight = 60
      const imgWidth = (contentWidth / 2) - 2
      
      try {
        const inputData = await getImageData(item.input)
        if (inputData) {
          pdf.addImage(inputData, 'JPEG', margin, y, imgWidth, imgHeight, undefined, 'FAST')
          pdf.setFontSize(10)
          if (!hasCJK) pdf.setFont('helvetica', 'bold')
          else pdf.setFont('NotoSansSC', 'normal')
          pdf.text('Before', margin, y + imgHeight + 6)
          if (!hasCJK) pdf.setFont('helvetica', 'normal')
          else pdf.setFont('NotoSansSC', 'normal')
        }

        const outputData = await getImageData(item.output)
        if (outputData) {
          pdf.addImage(outputData, 'JPEG', margin + imgWidth + 4, y, imgWidth, imgHeight, undefined, 'FAST')
          pdf.setFontSize(10)
          if (!hasCJK) pdf.setFont('helvetica', 'bold')
          else pdf.setFont('NotoSansSC', 'normal')
          pdf.text('After', margin + imgWidth + 4, y + imgHeight + 6)
          if (!hasCJK) pdf.setFont('helvetica', 'normal')
          else pdf.setFont('NotoSansSC', 'normal')
        }
      } catch (e) {
        console.error('Error adding image to PDF', e)
      }

      y += imgHeight + 10

      // 信息块（表格形式突出关键数据）
      const areaRatio = item.metrics?.area_ratio ?? 0
      const countVal = item.metrics?.count ?? 0
      const avgConf = item.metrics?.avg_conf ?? 0
      const confThresh = item.params.conf
      const iouThresh = item.params.iou
      const modelName = item.params.model || 'N/A'

      const tableX = margin
      const tableWidth = contentWidth
      const colWidth = tableWidth / 3
      const baseRow = 8
      const lineHeight = 4.5
      const pad = 4

      const measureHeight = (lines: string[]) => Math.max(baseRow, lines.length * lineHeight + pad)

      const metricValuesRaw = [
        String(countVal),
        `${(areaRatio * 100).toFixed(2)}%`,
        avgConf ? avgConf.toFixed(2) : '0'
      ]
      const metricLines = metricValuesRaw.map((val) => pdf.splitTextToSize(val, colWidth - 4))
      const metricRowHeight = measureHeight(metricLines.flat())

      const modelLines = pdf.splitTextToSize(modelName, colWidth - 4)
      const paramsValuesRaw: (string | string[])[] = [modelLines, confThresh?.toString() ?? 'N/A', iouThresh?.toString() ?? 'N/A']
      const paramsLines = paramsValuesRaw.map((val) => (Array.isArray(val) ? val : [val]))
      const paramsRowHeight = measureHeight(paramsLines.flat())

      const headerHeight = baseRow
      const neededHeight = headerHeight + metricRowHeight + paramsRowHeight + 10
      if (y > pageHeight - neededHeight) {
        pdf.addPage()
        y = margin
      }

      pdf.setDrawColor(180)
      pdf.setLineWidth(0.1)
      pdf.setFontSize(9)

      // Metrics 表头
      const header = [hasCJK ? '数量' : 'Count', hasCJK ? '面积占比' : 'Area %', hasCJK ? '平均置信度' : 'Avg Conf']
      for (let c = 0; c < 3; c++) {
        const x = tableX + c * colWidth
        pdf.rect(x, y, colWidth, headerHeight)
        if (!hasCJK) pdf.setFont('helvetica', 'bold')
        else pdf.setFont('NotoSansSC', 'normal')
        pdf.text(header[c], x + 2, y + 5)
      }
      if (!hasCJK) pdf.setFont('helvetica', 'normal')
      else pdf.setFont('NotoSansSC', 'normal')

      // Metrics 数值行（自适应行高）
      const metricY = y + headerHeight
      for (let c = 0; c < 3; c++) {
        const x = tableX + c * colWidth
        pdf.rect(x, metricY, colWidth, metricRowHeight)
        pdf.text(metricLines[c], x + 2, metricY + 5)
      }

      // Params 行：Model / Conf / IOU（自适应行高）
      const paramsY = metricY + metricRowHeight
      const paramsHeader = [hasCJK ? '模型' : 'Model', 'Conf', 'IOU']
      for (let c = 0; c < 3; c++) {
        const x = tableX + c * colWidth
        pdf.rect(x, paramsY, colWidth, paramsRowHeight)
        if (!hasCJK) pdf.setFont('helvetica', 'bold')
        else pdf.setFont('NotoSansSC', 'normal')
        pdf.text(paramsHeader[c], x + 2, paramsY + 5)
        if (!hasCJK) pdf.setFont('helvetica', 'normal')
        else pdf.setFont('NotoSansSC', 'normal')
        pdf.text(paramsLines[c], x + 2, paramsY + 10)
      }

      y = paramsY + paramsRowHeight + 12 // 下一项的间距
    }

    y += 4 // 批次之间留白
  }

  pdf.save(`corrosion_report_${reportId}.pdf`)
}

async function getImageData(url: string): Promise<string | null> {
  if (!url) return null
  if (url.startsWith('data:image')) return url

  try {
    const res = await fetch(url)
    const blob = await res.blob()
    return new Promise((resolve) => {
      const reader = new FileReader()
      reader.onloadend = () => resolve(reader.result as string)
      reader.readAsDataURL(blob)
    })
  } catch (e) {
    console.error('Failed to load image', url)
    return null
  }
}
