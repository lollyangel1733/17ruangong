<template>
  <div class="page-card" style="background: var(--card);">
    <div class="tasks-header">
      <div>
        <h1 class="card-title">任务队列中心</h1>
        <p class="card-sub">实时查看各检测任务的状态与结果。</p>
      </div>
      <div class="link-row">
        <NuxtLink class="text-link" :to="{ path: '/corrosion', query: { view: 'detect' } }">返回检测</NuxtLink>
        <NuxtLink class="text-link" to="/corrosion/logs">查看日志</NuxtLink>
      </div>
    </div>

    <section class="section-block">
      <div class="section-title-row">
        <div class="section-title">任务队列</div>
        <div class="filter-actions">
          <div class="filter-row">
            <label class="filter-label" for="modelFilter">按模型筛选</label>
            <select id="modelFilter" v-model="selectedModel" class="filter-select">
              <option value="">全部</option>
              <option v-for="m in modelOptions" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>
          <button class="ghost-btn" :disabled="!selectedGallery.length" @click="exportSelected">导出选中</button>
        </div>
      </div>
      <div v-if="tasks.length === 0" class="placeholder-box">暂无任务</div>
      <div v-else-if="filteredTasks.length === 0" class="placeholder-box">该模型暂无任务</div>
      <div v-else class="task-table">
        <div class="task-header">
          <span class="select-col">选择</span><span>文件</span><span>模式</span><span>状态</span><span>模型</span><span>备注</span>
        </div>
        <template v-for="group in pagedGroups" :key="group.batchId">
          <div
            v-if="group.items.length > 1"
            class="task-row batch-row"
            @click="toggleBatch(group.batchId)"
          >
            <span class="select-col">
              <input type="checkbox" :checked="isBatchSelected(group)" @click.stop="toggleBatchSelect(group)" />
            </span>
            <span class="batch-cell">
              <span class="chevron" :class="{ open: isBatchOpen(group.batchId) }">▶</span>
              <span>批次 #{{ group.order }} ({{ group.items.length }} 张)</span>
            </span>
            <span>{{ group.items[0].mode === 'sync' ? '同步' : '队列' }}</span>
            <span :class="['badge', batchStatus(group)]">{{ batchStatus(group) }}</span>
            <span class="muted-text">{{ group.items[0].model || '-' }}</span>
            <span class="muted-text">展开查看子任务</span>
          </div>

          <div
            v-for="t in visibleItems(group)"
            :key="t.id"
            class="task-row"
            :class="{ selected: t.id === selectedTaskId }"
            @click="selectTask(t.id)"
          >
            <span class="select-col">
              <input type="checkbox" :checked="isSelected(t.id)" @click.stop="toggleSelect(t.id)" />
            </span>
            <span>{{ t.filename }}</span>
            <span>{{ group.items.length === 1 ? '' : t.mode === 'sync' ? '同步' : '队列' }}</span>
            <span :class="['badge', t.status]">{{ t.status }}</span>
            <span>{{ t.model || '-' }}</span>
            <span>{{ t.message || '-' }}</span>
          </div>
        </template>
      </div>

      <div v-if="pagedGroups.length > 0" class="pagination">
        <button class="page-btn" :disabled="currentPage === 1" @click="currentPage--">上一页</button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
        <button class="page-btn" :disabled="currentPage === totalPages" @click="currentPage++">下一页</button>
      </div>
    </section>

    <section class="section-block">
      <div class="section-title">检测结果预览</div>
      <div v-if="!selectedResult" class="placeholder-box">点击上方任务即可查看对应的检测结果</div>
      <div v-else class="preview-card">
        <div class="preview-pair">
          <div class="preview-box">
            <div class="preview-title">输入图</div>
            <div class="preview-content">
              <img :src="selectedResult.input" alt="输入图" />
            </div>
          </div>
          <div class="preview-box">
            <div class="preview-title">输出（标注结果）</div>
            <div class="preview-content">
              <img :src="selectedResult.output" alt="检测结果" />
            </div>
          </div>
        </div>
        <div class="metrics-row">
          <div class="placeholder-box">检测数量: {{ selectedResult.metrics.count ?? '-' }}</div>
          <div class="placeholder-box">面积比例: {{ formatRatio(selectedResult.metrics.area_ratio) }}</div>
          <div class="placeholder-box">平均置信度: {{ formatConf(selectedResult.metrics.avg_conf) }}</div>
        </div>
        <div class="metrics-row">
          <div class="placeholder-box">模型: {{ selectedResult.params.model }}</div>
          <div class="placeholder-box">置信度/IOU: {{ selectedResult.params.conf }} / {{ selectedResult.params.iou }}</div>
          <div class="placeholder-box">输入尺寸/最大检测数: {{ selectedResult.params.imgsz }} / {{ selectedResult.params.max_det }}</div>
        </div>
      </div>
    </section>

  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useCorrosion } from '~/composables/useCorrosion'
import { generatePDFReport } from '~/utils/pdfExport'

const { tasks, gallery } = useCorrosion()
const selectedTaskId = ref<string>('')
const expandedBatches = ref<Record<string, boolean>>({})
const currentPage = ref(1)
const PAGE_SIZE = 5
const selectedModel = ref<string>('')
const selectedIds = ref<Set<string>>(new Set())

type TaskItem = (typeof tasks.value)[number]
type TaskGroup = { batchId: string; items: TaskItem[]; order: number }

const selectTask = (id: string) => {
  selectedTaskId.value = id
}

const isSelected = (id: string) => selectedIds.value.has(id)
const toggleSelect = (id: string) => {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

const toggleBatchSelect = (group: TaskGroup) => {
  const next = new Set(selectedIds.value)
  const allSelected = group.items.every((i) => next.has(i.id))
  if (allSelected) {
    group.items.forEach((i) => next.delete(i.id))
  } else {
    group.items.forEach((i) => next.add(i.id))
  }
  selectedIds.value = next
}

const isBatchSelected = (group: TaskGroup) => group.items.every((i) => isSelected(i.id)) && group.items.length > 0

const modelOptions = computed(() => {
  const set = new Set<string>()
  tasks.value.forEach((t) => { if (t.model) set.add(t.model) })
  return Array.from(set)
})

const filteredTasks = computed(() => {
  if (!selectedModel.value) return tasks.value
  return tasks.value.filter((t) => t.model === selectedModel.value)
})

watch(selectedModel, () => {
  currentPage.value = 1
})

const grouped = computed(() => {
  const arr: Omit<TaskGroup, 'order'>[] = []
  const map = new Map<string, Omit<TaskGroup, 'order'>>()
  for (const t of filteredTasks.value) {
    const batchId = t.batchId || t.id
    let group = map.get(batchId)
    if (!group) {
      group = { batchId, items: [] }
      map.set(batchId, group)
      arr.push(group)
    }
    group.items.push(t)
  }
  return arr.map((g) => {
    const orders = g.items.map((i) => i.batchOrder ?? Number.POSITIVE_INFINITY)
    const order = Math.min(...orders)
    return { ...g, order: isFinite(order) ? order : 0 }
  })
})

const totalPages = computed(() => {
  const len = grouped.value.length
  return len === 0 ? 1 : Math.ceil(len / PAGE_SIZE)
})

watch(grouped, () => {
  if (currentPage.value > totalPages.value) currentPage.value = totalPages.value
})

const pagedGroups = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return grouped.value.slice(start, start + PAGE_SIZE)
})

const isBatchOpen = (batchId: string) => expandedBatches.value[batchId] ?? false
const toggleBatch = (batchId: string) => {
  expandedBatches.value[batchId] = !isBatchOpen(batchId)
}

const visibleItems = (group: TaskGroup) => {
  if (group.items.length === 1) return group.items
  return isBatchOpen(group.batchId) ? group.items : []
}

const batchStatus = (group: TaskGroup) => {
  const statuses = group.items.map((i) => i.status)
  if (statuses.includes('running')) return 'running'
  if (statuses.includes('error')) return 'error'
  if (statuses.every((s) => s === 'done')) return 'done'
  if (statuses.every((s) => s === 'pending')) return 'pending'
  return statuses[0] || 'pending'
}

const selectedResult = computed(() => {
  if (!selectedTaskId.value) return undefined
  const t = tasks.value.find((x) => x.id === selectedTaskId.value)
  if (!t) return undefined
  return gallery.value.find((g) => {
    if (t.batchId && g.batchId) return g.filename === t.filename && g.batchId === t.batchId
    return g.filename === t.filename
  })
})

const selectedGallery = computed(() => {
  const picked: typeof gallery.value = []
  const seen = new Set<string>()
  selectedIds.value.forEach((id) => {
    const t = tasks.value.find((x) => x.id === id)
    if (!t) return
    const g = gallery.value.find((img) => {
      if (t.batchId && img.batchId) return img.batchId === t.batchId && img.filename === t.filename
      return img.filename === t.filename
    })
    if (g) {
      const key = `${g.batchId || 'legacy'}-${g.filename}-${g.input}`
      if (!seen.has(key)) {
        picked.push({ ...g, batchOrder: t.batchOrder })
        seen.add(key)
      }
    }
  })
  return picked
})

const exportSelected = async () => {
  if (!selectedGallery.value.length) return
  await generatePDFReport(selectedGallery.value)
}

const formatConf = (v?: number) => (typeof v === 'number' ? v.toFixed(3) : '-')
const formatRatio = (v?: number) => (typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : '-')
</script>

<style scoped>
.tasks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.text-link {
  color: var(--accent);
  font-size: 13px;
}
.link-row {
  display: flex;
  gap: 12px;
  align-items: center;
}
.section-block {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.section-title {
  font-weight: 600;
  color: var(--text);
}
.filter-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.filter-row {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.filter-label {
  font-size: 13px;
  color: var(--muted);
}
.filter-select {
  padding: 6px 10px;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text);
  border-radius: 8px;
  min-width: 140px;
}
.task-table {
  display: grid;
  gap: 6px;
}
.task-header,
.task-row {
  display: grid;
  grid-template-columns: 0.7fr 2fr 0.8fr 0.9fr 1.5fr 1.8fr;
  gap: 8px;
  align-items: center;
}
.task-header span,
.task-row span {
  overflow-wrap: anywhere;
  word-break: break-all;
}
.task-header {
  color: var(--muted);
  font-size: 13px;
}
.task-row {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--card);
  cursor: pointer;
}
.batch-row {
  background: var(--card-strong, #0f172a08);
  font-weight: 600;
}
.batch-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}
.chevron {
  display: inline-block;
  transition: transform 0.15s ease;
  color: var(--muted);
}
.chevron.open {
  transform: rotate(90deg);
}
.muted-text {
  color: var(--muted);
}
.task-row.selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}
.select-col {
  display: flex;
  align-items: center;
}
.badge {
  padding: 4px 8px;
  border-radius: 10px;
  font-size: 12px;
  color: #fff;
  text-align: center;
}
.badge.running { background: #3b82f6; }
.badge.done { background: #22c55e; }
.badge.error { background: #ef4444; }
.badge.pending { background: #9ca3af; }
.preview-card {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
  background: var(--card);
  display: flex;
  flex-direction: column;
  gap: 12px;
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
.metrics-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(160px, 1fr));
  gap: 10px;
}
.pagination {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.page-btn {
  padding: 6px 12px;
  border: 1px solid var(--border);
  background: var(--card);
  border-radius: 8px;
  cursor: pointer;
  color: var(--text);
}
.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.page-info {
  font-size: 13px;
  color: var(--muted);
}
@media (max-width: 960px) {
  .task-header,
  .task-row {
    grid-template-columns: 0.7fr 1.6fr 0.8fr 0.9fr 1.3fr 1.6fr;
  }
}
</style>
