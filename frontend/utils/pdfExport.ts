import { jsPDF } from 'jspdf'

interface ReportItem {
  filename: string
  input: string
  output: string
  params: any
  metrics: any
}

export async function generatePDFReport(items: ReportItem[], chartImages?: { pie?: string, bar?: string }) {
  if (!items.length) return

  const pdf = new jsPDF('p', 'mm', 'a4')
  const pageWidth = pdf.internal.pageSize.getWidth()
  const pageHeight = pdf.internal.pageSize.getHeight()
  const margin = 10
  const contentWidth = pageWidth - margin * 2

  let y = margin

  // 标题
  pdf.setFontSize(18)
  pdf.text('Corrosion Detection Report', pageWidth / 2, y, { align: 'center' })
  y += 15

  // 日期
  pdf.setFontSize(10)
  pdf.text(`Date: ${new Date().toLocaleString()}`, margin, y)
  y += 10

  // 摘要
  pdf.text(`Total Images: ${items.length}`, margin, y)
  y += 15

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

  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    
    // 检查是否需要新页面
    if (y > pageHeight - 100) {
      pdf.addPage()
      y = margin
    }

    // 项目标题
    pdf.setFontSize(12)
    // 注意：jsPDF 默认字体不支持中文。
    // 我们将使用清理后的文件名，或者如果无法渲染则使用 "Image N"。
    // 目前假设使用英文或接受中文可能显示异常。
    // 为了安全起见，我们可以使用 "Image Index" 作为回退标签。
    pdf.text(`Image ${i + 1}: ${item.filename}`, margin, y)
    y += 7

    // 图像
    // 我们需要加载图像以获取尺寸
    // 输入
    const imgHeight = 60
    const imgWidth = (contentWidth / 2) - 2
    
    try {
      // 添加输入图像
      // 我们假设输入/输出是 base64 或有效的 URL。
      // 如果是 blob URL，我们需要获取它们。
      const inputData = await getImageData(item.input)
      if (inputData) {
        pdf.addImage(inputData, 'JPEG', margin, y, imgWidth, imgHeight, undefined, 'FAST')
        pdf.setFontSize(8)
        pdf.text('Original', margin, y + imgHeight + 4)
      }

      // 添加输出图像
      const outputData = await getImageData(item.output)
      if (outputData) {
        pdf.addImage(outputData, 'JPEG', margin + imgWidth + 4, y, imgWidth, imgHeight, undefined, 'FAST')
        pdf.text('Detected', margin + imgWidth + 4, y + imgHeight + 4)
      }
    } catch (e) {
      console.error('Error adding image to PDF', e)
    }

    y += imgHeight + 8

    // 信息块
    pdf.setFontSize(9)
    const metricsStr = `Count: ${item.metrics.count ?? 0} | Area: ${(item.metrics.area_ratio * 100).toFixed(2)}% | Conf: ${item.metrics.avg_conf?.toFixed(2) ?? 0}`
    const paramsStr = `Model: ${item.params.model} | Conf: ${item.params.conf} | IOU: ${item.params.iou}`
    
    pdf.text(metricsStr, margin, y)
    y += 5
    pdf.text(paramsStr, margin, y)
    
    y += 15 // 下一项的间距
  }

  pdf.save(`corrosion_report_${new Date().getTime()}.pdf`)
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
