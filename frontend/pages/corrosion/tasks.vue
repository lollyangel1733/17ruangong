<template>
  <div class="page-card" style="background: var(--card);">
    <div class="tasks-header">
      <div>
        <h1 class="card-title">任务队列中心</h1>
        <p class="card-sub">实时查看各检测任务的状态与结果。</p>
      </div>
      <div class="link-row">
        <NuxtLink class="text-link" to="/corrosion">返回检测</NuxtLink>
        <NuxtLink class="text-link" to="/corrosion/logs">查看日志</NuxtLink>
      </div>
    </div>

    <section class="section-block">
      <div class="section-title">任务队列</div>
      <div v-if="tasks.length === 0" class="placeholder-box">暂无任务</div>
      <div v-else class="task-table">
        <div class="task-header">
          <span>文件</span><span>模式</span><span>状态</span><span>指标</span><span>备注</span>
        </div>
        <div v-for="t in tasks" :key="t.id" class="task-row">
          <span>{{ t.filename }}</span>
          <span>{{ t.mode === 'sync' ? '同步' : '队列' }}</span>
          <span :class="['badge', t.status]">{{ t.status }}</span>
          <span>
            <template v-if="t.metrics">count: {{ t.metrics.count ?? '-' }}, conf: {{ formatConf(t.metrics.avg_conf) }}</template>
            <template v-else>-</template>
          </span>
          <span>{{ t.message || '-' }}</span>
        </div>
      </div>
    </section>

  </div>
</template>

<script setup lang="ts">
import { useCorrosion } from '~/composables/useCorrosion'

const { tasks } = useCorrosion()
const formatConf = (v?: number) => (typeof v === 'number' ? v.toFixed(3) : '-')
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
.section-title {
  font-weight: 600;
  color: var(--text);
}
.task-table {
  display: grid;
  gap: 6px;
}
.task-header,
.task-row {
  display: grid;
  grid-template-columns: 2fr 0.8fr 0.9fr 1.5fr 1.8fr;
  gap: 8px;
  align-items: center;
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
@media (max-width: 960px) {
  .task-header,
  .task-row {
    grid-template-columns: 1.6fr 0.8fr 0.9fr 1.3fr 1.6fr;
  }
}
</style>
