<template>
  <div class="page-card">
    <div class="title-row">
      <div>
        <h1 class="card-title">金属幕墙锈蚀污损检测</h1>
        <p class="card-sub"> </p>
      </div>
      <div class="segmented">
        <button :class="['seg-btn', { active: viewMode === 'performance' }]" @click="viewMode = 'performance'">模型性能对比</button>
        <button :class="['seg-btn', { active: viewMode === 'detect' }]" @click="viewMode = 'detect'">检测系统</button>
      </div>
    </div>
    <CorrosionDetectionCorrosionPanel :view-mode="viewMode" @update:view-mode="viewMode = $event" />
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const viewMode = ref<'performance' | 'detect'>(route.query.view === 'detect' ? 'detect' : 'performance')
</script>

<style scoped>
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.segmented {
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}
.seg-btn {
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-size: 13px;
}
.seg-btn + .seg-btn {
  border-left: 1px solid var(--border);
}
.seg-btn.active {
  background: var(--accent);
  color: #fff;
}
</style>
