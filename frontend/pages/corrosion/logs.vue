<template>
  <div class="page-card" style="background: var(--card);">
    <div class="tasks-header">
      <div>
        <h1 class="card-title">日志中心</h1>
        <p class="card-sub">追踪检测流程的详细运行日志。</p>
      </div>
      <div class="link-row">
        <NuxtLink class="text-link" to="/corrosion">返回检测</NuxtLink>
        <NuxtLink class="text-link" to="/corrosion/tasks">查看任务队列</NuxtLink>
      </div>
    </div>

    <section class="section-block">
      <div v-if="logs.length === 0" class="placeholder-box">暂无日志</div>
      <ul v-else class="log-list">
        <li v-for="(l, idx) in logs" :key="idx">{{ l }}</li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useCorrosion } from '~/composables/useCorrosion'

const { logs } = useCorrosion()
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
}
.log-list {
  margin: 0;
  padding-left: 16px;
  color: var(--muted);
  font-size: 13px;
  max-height: 320px;
  overflow-y: auto;
}
</style>
