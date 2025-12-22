<!--
组件名称：CorrosionPanel
功能说明：锈蚀检测前端界面（上传、参数、结果），通过 Nuxt API 代理调用 Flask 后端。
-->
<template>
  <div class="stack">
    <div class="top-row">
      <div class="page-card" style="background: var(--card);">
        <h3 class="card-title">上传</h3>
        <p class="card-sub">选择图片并开始检测，支持多张顺序处理。</p>
        <div class="upload-panel">
          <div class="upload-actions">
            <label class="btn">
              <input type="file" accept="image/*" multiple hidden @change="onFilesChange" />
              选择图像
            </label>
            <div class="progress-text">{{ progressText }}</div>
            <div class="action-row">
              <button class="btn" :disabled="busy || !files.length" @click="startDetect">同步检测</button>
              <button class="btn secondary" :disabled="busy || !files.length" @click="startQueue">队列检测</button>
              <button class="ghost-btn" @click="goTasks">任务队列</button>
              <button class="ghost-btn" @click="goLogs">日志</button>
              <span v-if="busy" class="muted">处理中...</span>
            </div>
          </div>
          <div class="thumb-row" v-if="gallery.length || inputPreviewSrc">
            <div class="thumb current" :class="{ active: !gallery.length }" v-if="inputPreviewSrc">
              <img :src="inputPreviewSrc" alt="输入预览" />
              <div class="thumb-label">当前输入</div>
            </div>
            <div v-for="item in gallery" :key="item.id" class="thumb" @click="selectThumb(item)">
              <img :src="item.output" :alt="item.filename" />
              <div class="thumb-label">{{ item.filename }}</div>
            </div>
          </div>
        </div>
      </div>
      <div class="page-card" style="background: var(--card);">
        <h3 class="card-title">参数</h3>
        <p class="card-sub">选择模型与阈值。</p>
        <div class="param-grid">
          <div class="param-block full">
            <div class="param-label">模型</div>
            <select v-model="params.model" class="param-input">
              <option v-for="m in models" :key="m.key" :value="m.key">{{ m.name }}</option>
            </select>
          </div>
          <div class="param-block">
            <div class="param-label">置信度 (conf)</div>
            <input v-model.number="params.conf" type="number" min="0" max="1" step="0.01" class="param-input" />
          </div>
          <div class="param-block">
            <div class="param-label">IOU 阈值 (iou)</div>
            <input v-model.number="params.iou" type="number" min="0" max="1" step="0.01" class="param-input" />
          </div>
          <div class="param-block">
            <div class="param-label">输入尺寸 (imgsz)</div>
            <input v-model.number="params.imgsz" type="number" min="320" max="1536" step="32" class="param-input" />
          </div>
          <div class="param-block">
            <div class="param-label">最大检测数 (max_det)</div>
            <input v-model.number="params.max_det" type="number" min="1" max="1000" step="1" class="param-input" />
          </div>
        </div>
      </div>
    </div>

    <div class="page-card" style="background: var(--card);">
      <div class="results-header">
        <div>
          <h3 class="card-title">结果预览</h3>
          <p class="card-sub">输入/输出对比与统计指标。</p>
        </div>
        <div class="link-row">
          <button class="ghost-btn" @click="goTasks">任务队列</button>
          <button class="ghost-btn" @click="goLogs">日志</button>
        </div>
      </div>
      <div class="preview-pair">
        <div class="preview-box">
          <div class="preview-title">输入图</div>
          <div class="preview-content">
            <img v-if="inputPreviewSrc" :src="inputPreviewSrc" alt="输入图" />
            <div v-else class="placeholder-box">等待选择图片</div>
          </div>
        </div>
        <div class="preview-box">
          <div class="preview-title">输出（标注结果）</div>
          <div class="preview-content">
            <img v-if="previewSrc" :src="previewSrc" alt="检测结果" />
            <div v-else class="placeholder-box">等待检测结果</div>
          </div>
        </div>
      </div>
      <div class="metrics-row">
        <div class="placeholder-box">检测数量: {{ metrics.count ?? '-' }}</div>
        <div class="placeholder-box">面积比例: {{ formatRatio(metrics.area_ratio) }}</div>
        <div class="placeholder-box">平均置信度: {{ formatConf(metrics.avg_conf) }}</div>
      </div>
      <div class="metrics-row">
        <div class="placeholder-box">模型: {{ lastParams.model }}</div>
        <div class="placeholder-box">置信度/IOU: {{ lastParams.conf }} / {{ lastParams.iou }}</div>
        <div class="placeholder-box">输入尺寸/最大检测数: {{ lastParams.imgsz }} / {{ lastParams.max_det }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useCorrosion } from '~/composables/useCorrosion'

const {
  models,
  fetchModels,
  files,
  setFiles,
  params,
  busy,
  metrics,
  previewSrc,
  inputPreviewSrc,
  lastParams,
  progressText,
  gallery,
  startDetect,
  startQueue
} = useCorrosion()

const router = useRouter()
const goTasks = () => router.push('/corrosion/tasks')
const goLogs = () => router.push('/corrosion/logs')

const onFilesChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (input.files) {
    setFiles(Array.from(input.files))
  }
}

onMounted(() => {
  fetchModels()
})

const selectThumb = (item: typeof gallery.value[number]) => {
  if (!item) return
  previewSrc.value = item.output
  inputPreviewSrc.value = item.input
  metrics.value = item.metrics
  lastParams.value = item.params
}

const formatRatio = (v?: number) => (typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : '-')
const formatConf = (v?: number) => (typeof v === 'number' ? v.toFixed(3) : '-')
</script>

<style scoped>
.stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.top-row {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 12px;
}
.upload-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.upload-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.action-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.progress-text {
  color: var(--muted);
  font-size: 13px;
}
.text-link {
  color: var(--accent);
  font-size: 13px;
}
.ghost-btn {
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--accent);
  font-size: 13px;
}
.muted {
  color: var(--muted);
  font-size: 13px;
}
.thumb-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
}
.thumb {
  position: relative;
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  background: var(--card);
  cursor: pointer;
}
.thumb.current {
  border: 2px solid var(--accent);
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.08);
}
.thumb img {
  width: 100%;
  height: 110px;
  object-fit: cover;
  display: block;
}
.thumb-label {
  position: absolute;
  left: 8px;
  bottom: 6px;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 6px;
}
.thumb.active {
  outline: 2px solid var(--accent);
}
.preview-pair {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}
.preview-box {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 10px;
  background: var(--card);
}
.preview-title {
  color: var(--muted);
  font-size: 13px;
  margin-bottom: 6px;
}
.preview-content {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.preview-content img {
  width: 100%;
  max-height: 480px;
  object-fit: contain;
}
.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.metrics-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(160px, 1fr));
  gap: 10px;
  margin-top: 12px;
}
.param-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
}
.param-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.param-block.full {
  grid-column: 1 / -1;
}
.param-label {
  color: var(--muted);
  font-size: 13px;
}
.param-input {
  width: 100%;
  padding: 10px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
}
@media (max-width: 960px) {
  .top-row {
    grid-template-columns: 1fr;
  }
  .metrics-row {
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  }
}
</style>
