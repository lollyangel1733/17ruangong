<template>
  <div class="layout-shell">
    <aside class="layout-sidebar">
      <div>
        <div class="brand">智慧幕墙前端</div>
        <div class="nav-section">
          <div class="nav-title">金属幕墙子系统</div>
          <NuxtLink class="nav-link" to="/corrosion">金属幕墙锈蚀污损检测</NuxtLink>
        </div>
      </div>
      <div class="sidebar-footer">
        <template v-if="isAuthenticated">
          <div class="user-chip">
            <div class="avatar">{{ initials }}</div>
            <div class="user-info">
              <div class="user-name">{{ user?.username }}</div>
              <div class="user-role">{{ user?.role || 'guest' }}</div>
            </div>
            <button class="ghost-btn" :disabled="loading" @click="handleLogout">退出</button>
          </div>
        </template>
        <template v-else>
          <div class="muted-note">未登录</div>
        </template>
      </div>
    </aside>
    <main class="layout-main">
      <NuxtPage />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const { user, isAuthenticated, loading, logout, restoreSession } = useAuth()
const initials = computed(() => (user.value?.username || 'G').slice(0, 2).toUpperCase())

restoreSession()

const handleLogout = () => {
  logout()
  navigateTo('/auth/login')
}
</script>

<style scoped>
.brand {
  margin-bottom: 16px;
  font-weight: 700;
  font-size: 18px;
}
.layout-sidebar {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.sidebar-footer {
  margin-top: 20px;
  padding-top: 14px;
  border-top: 1px dashed var(--border);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.muted-note {
  color: var(--muted);
  font-size: 13px;
}
.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--card);
}
.avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--accent);
  color: #fff;
  display: grid;
  place-items: center;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.user-name {
  font-weight: 700;
}
.user-role {
  color: var(--muted);
  font-size: 12px;
}
.auth-actions {
  display: flex;
  gap: 8px;
  align-items: center;
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
</style>
