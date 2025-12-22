<template>
  <div class="charts-container">
    <div class="chart-card">
      <h4>锈蚀严重程度分布 (饼图)</h4>
      <div class="chart-wrapper">
        <Pie ref="pieChartRef" v-if="gallery.length" :data="pieData" :options="pieOptions" />
        <div v-else class="no-data">暂无数据</div>
      </div>
    </div>
    <div class="chart-card">
      <h4>重点关注目标排行 (Top 10)</h4>
      <div class="chart-wrapper">
        <Bar ref="barChartRef" v-if="gallery.length" :data="barData" :options="barOptions" />
        <div v-else class="no-data">暂无数据</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  ArcElement
} from 'chart.js'
import { Bar, Pie } from 'vue-chartjs'
import { useCorrosion } from '~/composables/useCorrosion'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement)

const { gallery } = useCorrosion()
const pieChartRef = ref<any>(null)
const barChartRef = ref<any>(null)

defineExpose({
  getChartImages: () => {
    return {
      pie: pieChartRef.value?.chart?.toBase64Image(),
      bar: barChartRef.value?.chart?.toBase64Image()
    }
  }
})

// 1. 饼图数据：锈蚀严重程度分布
const pieData = computed(() => {
  let low = 0, mid = 0, high = 0
  gallery.value.forEach(item => {
    const ratio = item.metrics?.area_ratio || 0
    if (ratio < 0.001) low++
    else if (ratio < 0.01) mid++
    else high++
  })

  return {
    labels: ['轻微 (<0.1%)', '中度 (0.1%-1%)', '严重 (>1%)'],
    datasets: [
      {
        backgroundColor: ['#4ade80', '#facc15', '#ef4444'],
        data: [low, mid, high]
      }
    ]
  }
})

const pieOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom' as const
    }
  }
}

// 2. 柱状图数据：重点关注目标排行
const barData = computed(() => {
  // 按面积比例降序排序，取前10
  const sorted = [...gallery.value]
    .sort((a, b) => (b.metrics?.area_ratio || 0) - (a.metrics?.area_ratio || 0))
    .slice(0, 10)

  return {
    labels: sorted.map(item => item.filename.length > 10 ? item.filename.slice(0, 10) + '...' : item.filename),
    datasets: [
      {
        label: '锈蚀面积比例',
        backgroundColor: '#3b82f6',
        data: sorted.map(item => item.metrics?.area_ratio || 0)
      }
    ]
  }
})

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      title: {
        display: true,
        text: '面积比例 (0-1)'
      }
    }
  }
}
</script>

<style scoped>
.charts-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 1rem;
}

.chart-card {
  background: var(--card);
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  height: 350px;
}

.chart-card h4 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  color: var(--text-main);
  text-align: center;
}

.chart-wrapper {
  flex: 1;
  position: relative;
  min-height: 0; /* Fix for flex child overflow */
}

.no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .charts-container {
    grid-template-columns: 1fr;
  }
}
</style>
