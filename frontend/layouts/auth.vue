<template>
  <div class="auth-shell">
    <div class="auth-card">
      <div class="auth-illustration">
        <div class="glow" />
        <div class="panel">
          <div class="logo">MCW</div>
          <div class="headline">金属幕墙检测平台</div>
          <p class="sub">独立登录/注册页，接口格式与后端一致，后续可直接切换真实服务。</p>
        </div>
      </div>
      <main class="auth-main">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.auth-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
  background: radial-gradient(circle at 20% 20%, rgba(29, 78, 216, 0.12), transparent 30%),
    radial-gradient(circle at 80% 10%, rgba(14, 165, 233, 0.1), transparent 30%),
    linear-gradient(135deg, #f5f8ff 0%, #eef3ff 100%);
}
.auth-card {
  width: min(1100px, 100%);
  display: grid;
  grid-template-columns: 1fr minmax(360px, 420px);
  gap: 0;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--border);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 22px 60px rgba(15, 23, 42, 0.16);
  backdrop-filter: blur(6px);
}
.auth-illustration {
  position: relative;
  padding: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: linear-gradient(135deg, #eef3ff 0%, #f9fbff 100%);
}
.glow {
  position: absolute;
  inset: 10%;
  background: radial-gradient(circle at 40% 40%, rgba(29, 78, 216, 0.18), transparent 50%);
  filter: blur(30px);
  opacity: 0.9;
}
.panel {
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 28px;
  backdrop-filter: blur(8px);
  max-width: 420px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.12);
}
.logo {
  width: 54px;
  height: 54px;
  border-radius: 14px;
  background: var(--accent);
  color: #fff;
  display: grid;
  place-items: center;
  font-weight: 800;
  letter-spacing: 0.08em;
  margin-bottom: 16px;
}
.headline {
  font-size: 22px;
  font-weight: 800;
  margin-bottom: 10px;
}
.sub {
  color: var(--muted);
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
}
.auth-main {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 42px 32px;
  background: #fff;
}
@media (max-width: 960px) {
  .auth-card {
    grid-template-columns: 1fr;
  }
  .auth-illustration {
    display: none;
  }
  .auth-main {
    padding: 28px 18px;
  }
}
</style>
