<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAvatar, NButton, NDrawer, NDrawerContent, NTag, NTooltip } from 'naive-ui'
import {
  BookOpenText,
  ChartNoAxesCombined,
  ClipboardCheck,
  FileChartColumn,
  FlaskConical,
  Gauge,
  LibraryBig,
  LogOut,
  Menu,
  ScanSearch,
  Settings2,
  Target,
} from 'lucide-vue-next'
import AppLogo from '../components/AppLogo.vue'
import ModelSettingsDrawer from '../components/ModelSettingsDrawer.vue'
import { useAuthStore } from '../stores/auth'
import { useModelSettingsStore } from '../stores/model-settings'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const modelSettings = useModelSettingsStore()
const drawerOpen = ref(false)
const settingsOpen = ref(false)
const mobile = ref(false)

const navigation = [
  {
    label: '总览',
    items: [{ label: '学习工作台', path: '/dashboard', icon: Gauge }],
  },
  {
    label: '学习准备',
    items: [
      { label: '构建学习画像', path: '/onboarding', icon: ChartNoAxesCombined },
      { label: '能力诊断', path: '/diagnosis', icon: ClipboardCheck },
      { label: '画像档案', path: '/profile', icon: Target },
    ],
  },
  {
    label: '视觉实训',
    items: [
      { label: '药材辨识', path: '/recognition', icon: ScanSearch },
      { label: '虚拟仿真实训', path: '/simulation', icon: FlaskConical },
    ],
  },
  {
    label: '个性化学习',
    items: [
      { label: '药材知识', path: '/knowledge', icon: LibraryBig },
      { label: '学习资源', path: '/resources', icon: BookOpenText },
      { label: '学习任务', path: '/learning-tasks', icon: ClipboardCheck },
    ],
  },
  {
    label: '结果沉淀',
    items: [
      { label: '学习报告', path: '/reports', icon: FileChartColumn },
      { label: '证据链', path: '/traces', icon: FlaskConical },
      { label: '测试指标', path: '/metrics', icon: Gauge },
    ],
  },
]

const activeTitle = computed(() => String(route.meta.title || '学习工作台'))
const displayName = computed(() => auth.user?.display_name || auth.user?.username || '用户')
const initial = computed(() => displayName.value.slice(0, 1).toUpperCase())

function updateViewport(): void {
  mobile.value = window.matchMedia('(max-width: 900px)').matches
  if (!mobile.value) drawerOpen.value = false
}

async function handleLogout(): Promise<void> {
  await auth.logout()
  await router.replace('/login')
}

function closeDrawer(): void {
  drawerOpen.value = false
}

onMounted(() => {
  updateViewport()
  window.addEventListener('resize', updateViewport)
  void modelSettings.load()
})

onBeforeUnmount(() => window.removeEventListener('resize', updateViewport))
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="sidebar-brand"><AppLogo /></div>
      <nav class="primary-nav" aria-label="主导航">
        <section v-for="group in navigation" :key="group.label" class="nav-group">
          <span class="nav-group-label">{{ group.label }}</span>
          <router-link v-for="item in group.items" :key="item.path" :to="item.path" class="nav-item">
            <component :is="item.icon" :size="18" :stroke-width="1.9" aria-hidden="true" />
            <span>{{ item.label }}</span>
          </router-link>
        </section>
      </nav>
      <div class="sidebar-account">
        <n-avatar round size="small" color="#dcebe3" text-color="#195b43">{{ initial }}</n-avatar>
        <div><strong>{{ displayName }}</strong><span>{{ auth.learnerId }}</span></div>
        <n-tooltip trigger="hover">
          <template #trigger>
            <n-button quaternary circle size="small" aria-label="退出登录" @click="handleLogout">
              <template #icon><LogOut :size="17" /></template>
            </n-button>
          </template>
          退出登录
        </n-tooltip>
      </div>
    </aside>

    <div class="main-shell">
      <header class="topbar">
        <div class="topbar-leading">
          <n-button v-if="mobile" quaternary circle aria-label="打开导航" @click="drawerOpen = true">
            <template #icon><Menu :size="21" /></template>
          </n-button>
          <div class="location-copy"><span>学习中心</span><strong>{{ activeTitle }}</strong></div>
        </div>
        <div class="topbar-meta">
          <n-tag v-if="modelSettings.status.configured" size="small" type="success" :bordered="false">
            {{ modelSettings.status.model_id }}
          </n-tag>
          <span class="learner-chip">{{ auth.learnerId }}</span>
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button quaternary circle aria-label="模型服务设置" @click="settingsOpen = true">
                <template #icon><Settings2 :size="19" /></template>
              </n-button>
            </template>
            模型服务设置
          </n-tooltip>
        </div>
      </header>
      <main class="app-content"><router-view /></main>
    </div>
  </div>

  <n-drawer v-model:show="drawerOpen" placement="left" :width="286">
    <n-drawer-content :native-scrollbar="false" body-content-style="padding: 0;">
      <div class="drawer-panel">
        <div class="drawer-brand"><AppLogo /></div>
        <nav class="primary-nav" aria-label="移动端主导航">
          <section v-for="group in navigation" :key="group.label" class="nav-group">
            <span class="nav-group-label">{{ group.label }}</span>
            <router-link v-for="item in group.items" :key="item.path" :to="item.path" class="nav-item" @click="closeDrawer">
              <component :is="item.icon" :size="18" :stroke-width="1.9" aria-hidden="true" />
              <span>{{ item.label }}</span>
            </router-link>
          </section>
        </nav>
        <n-button secondary block @click="handleLogout">
          <template #icon><LogOut :size="17" /></template>
          退出登录
        </n-button>
      </div>
    </n-drawer-content>
  </n-drawer>

  <ModelSettingsDrawer v-model:show="settingsOpen" />
</template>

<style scoped>
.app-shell {
  display: grid;
  grid-template-columns: 242px minmax(0, 1fr);
  min-height: 100vh;
}

.sidebar {
  position: sticky;
  top: 0;
  display: grid;
  grid-template-rows: 70px minmax(0, 1fr) auto;
  height: 100vh;
  color: #dce4de;
  background: #18231d;
  border-right: 1px solid #2c3931;
}

.sidebar-brand,
.drawer-brand {
  display: flex;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid #2c3931;
}

.sidebar-brand :deep(.app-logo),
.drawer-brand :deep(.app-logo) {
  color: #fff;
}

.primary-nav {
  min-height: 0;
  padding: 13px 11px 20px;
  overflow-y: auto;
}

.nav-group {
  display: grid;
  gap: 2px;
  margin-bottom: 10px;
}

.nav-group-label {
  padding: 8px 10px 4px;
  color: #7f9185;
  font-size: 9px;
  font-weight: 700;
}

.nav-item {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  min-height: 38px;
  padding: 8px 10px;
  color: #bdc8c0;
  border-radius: 6px;
  font-size: 11px;
  text-decoration: none;
}

.nav-item:hover {
  color: #fff;
  background: #243129;
}

.nav-item.router-link-active {
  color: #fff;
  background: #2d4a3a;
}

.nav-item.router-link-active svg {
  color: #85c29f;
}

.sidebar-account {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 32px;
  align-items: center;
  gap: 8px;
  min-height: 66px;
  padding: 11px 14px;
  border-top: 1px solid #2c3931;
}

.sidebar-account > div {
  display: grid;
  min-width: 0;
}

.sidebar-account strong {
  overflow: hidden;
  color: #fff;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-account span {
  color: #829187;
  font-size: 9px;
}

.main-shell {
  min-width: 0;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 62px;
  padding: 8px 22px;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid var(--line);
  backdrop-filter: blur(10px);
}

.topbar-leading,
.topbar-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.location-copy {
  display: grid;
  min-width: 0;
}

.location-copy span {
  color: var(--subtle);
  font-size: 9px;
}

.location-copy strong {
  overflow: hidden;
  color: var(--ink);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.learner-chip {
  color: var(--muted);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 10px;
}

.app-content {
  min-width: 0;
}

.drawer-panel {
  display: grid;
  grid-template-rows: 70px minmax(0, 1fr) auto;
  min-height: 100vh;
  padding-bottom: 14px;
  color: #dce4de;
  background: #18231d;
}

.drawer-panel > .n-button {
  margin: 0 12px;
  color: #dce4de;
}

@media (max-width: 900px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    display: none;
  }

  .topbar {
    padding-inline: 12px;
  }
}

@media (max-width: 560px) {
  .topbar-meta .n-tag,
  .learner-chip {
    display: none;
  }
}
</style>
