<template>
  <div class="compare-stack">
    <div class="compare-header">
      <div class="header-actions">
        <button class="ghost-btn" @click="onRefresh" :disabled="pending">刷新</button>
      </div>
    </div>

    <div v-if="pending" class="placeholder-box">加载中...</div>
    <div v-else-if="error" class="error-box">加载失败：{{ errorMessage }}</div>
    <div v-else-if="!rows.length" class="placeholder-box">暂无性能数据</div>
    <div v-else class="compare-grid">
      <div class="chart-card">
        <div class="chart-title">mAP 对比</div>
        <Bar :data="mapBarData" :options="barOptions" />
      </div>
      <div class="chart-card">
        <div class="chart-title">Prec / Recall / F1 雷达图</div>
        <Radar :data="radarData" :options="radarOptions" />
      </div>
      <div class="table-card">
        <div class="chart-title">关键指标表</div>
        <div class="table-header">
          <span>模型</span>
          <span>mAP@0.5</span>
          <span>mAP@0.5:0.95</span>
          <span>Precision</span>
          <span>Recall</span>
          <span>F1</span>
          <span>Latency (ms)</span>
          <span>FPS</span>
        </div>
        <div v-for="item in rows" :key="item.model" class="table-row">
          <span>{{ item.name || item.model }}</span>
          <span>{{ fmt(item.map50) }}</span>
          <span>{{ fmt(item.map5095) }}</span>
          <span>{{ fmt(item.precision) }}</span>
          <span>{{ fmt(item.recall) }}</span>
          <span>{{ fmt(item.f1 ?? calcF1(item.precision, item.recall)) }}</span>
          <span>{{ item.latency_ms ? item.latency_ms.toFixed(1) : '-' }}</span>
          <span>{{ item.fps ? item.fps.toFixed(1) : '-' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler
} from 'chart.js'
import { Bar, Radar } from 'vue-chartjs'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale, RadialLinearScale, PointElement, LineElement, Filler)

type BenchmarkItem = {
  model: string
  name?: string
  map50?: number
  map5095?: number
  precision?: number
  recall?: number
  f1?: number
  fps?: number
  latency_ms?: number
}

type BenchResponse = { success?: boolean; data?: BenchmarkItem[]; models?: BenchmarkItem[]; benchmarks?: BenchmarkItem[]; message?: string }

const { data, pending, error, refresh } = await useAsyncData<BenchResponse>('model-benchmarks', async () => {
  return await $fetch<BenchResponse>('/api/corrosion/benchmarks')
})

const onRefresh = () => refresh()

const rows = computed<BenchmarkItem[]>(() => data.value?.data || data.value?.models || data.value?.benchmarks || [])
const labels = computed(() => rows.value.map((r) => r.name || r.model))
const palette = ['#3b82f6', '#22c55e', '#f97316', '#a855f7', '#06b6d4', '#ef4444']

const mapBarData = computed(() => ({
  labels: labels.value,
  datasets: [
    { label: 'mAP@0.5', backgroundColor: palette[0], data: rows.value.map((r) => r.map50 ?? 0) },
    { label: 'mAP@0.5:0.95', backgroundColor: palette[1], data: rows.value.map((r) => r.map5095 ?? 0) }
  ]
}))

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { position: 'bottom' as const } },
  scales: { y: { beginAtZero: true, max: 1 } }
}

const radarData = computed(() => ({
  labels: ['Precision', 'Recall', 'F1'],
  datasets: rows.value.map((r, idx) => {
    const color = palette[idx % palette.length]
    return {
      label: r.name || r.model,
      data: [r.precision ?? 0, r.recall ?? 0, r.f1 ?? calcF1(r.precision, r.recall)],
      backgroundColor: color + '33',
      borderColor: color,
      pointBackgroundColor: color,
      fill: true
    }
  })
}))

const radarOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    r: {
      beginAtZero: true,
      max: 1,
      ticks: { stepSize: 0.2 }
    }
  },
  plugins: { legend: { position: 'bottom' as const } }
}

const fmt = (v?: number) => (typeof v === 'number' ? v.toFixed(3) : '-')
const calcF1 = (p?: number, r?: number) => {
  if (p === undefined || r === undefined || p + r === 0) return 0
  return (2 * p * r) / (p + r)
}

const errorMessage = computed(() => error.value?.message || data.value?.message || '')
</script>

<style scoped>
.compare-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.compare-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.header-actions {
  display: flex;
  gap: 8px;
}
.compare-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.chart-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px;
  height: 320px;
  display: flex;
  flex-direction: column;
}
.chart-title {
  font-size: 14px;
  color: var(--muted);
  margin-bottom: 8px;
}
.table-card {
  grid-column: 1 / -1;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.table-header,
.table-row {
  display: grid;
  grid-template-columns: 1.4fr repeat(7, 1fr);
  gap: 6px;
  font-size: 13px;
  align-items: center;
}
.table-header {
  color: var(--muted);
  border-bottom: 1px solid var(--border);
  padding-bottom: 6px;
}
.table-row {
  color: var(--text);
  padding: 4px 0;
}
.error-box {
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
}
.ghost-btn {
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--accent);
  font-size: 13px;
  cursor: pointer;
}
@media (max-width: 960px) {
  .compare-grid {
    grid-template-columns: 1fr;
  }
  .chart-card {
    height: 280px;
  }
  .table-header,
  .table-row {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    row-gap: 4px;
  }
  .table-header span:nth-child(n+5),
  .table-row span:nth-child(n+5) {
    display: none;
  }
}
</style>
