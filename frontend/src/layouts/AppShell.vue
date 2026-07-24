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
  Maximize2,
  Menu,
  ScanSearch,
  Search,
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
  { label: '学习工作台', path: '/dashboard', icon: Gauge },
  { label: '学习画像', path: '/profile', icon: ChartNoAxesCombined, matches: ['/onboarding', '/diagnosis', '/profile'] },
  { label: '药材识别', path: '/recognition', icon: ScanSearch },
  { label: '虚拟实训', path: '/simulation', icon: FlaskConical },
  { label: '药材知识', path: '/knowledge', icon: LibraryBig },
  { label: '学习资源', path: '/resources', icon: BookOpenText },
  { label: '学习任务', path: '/learning-tasks', icon: ClipboardCheck },
  { label: '结果沉淀', path: '/reports', icon: FileChartColumn, matches: ['/reports', '/traces', '/metrics'] },
]

const mobileGroups = [
  {
    label: '学习中心',
    items: navigation.slice(0, 4),
  },
  {
    label: '知识与任务',
    items: navigation.slice(4, 7),
  },
  {
    label: '结果与证据',
    items: [
      navigation[7],
      { label: '证据链', path: '/traces', icon: FlaskConical },
      { label: '测试指标', path: '/metrics', icon: Target },
    ],
  },
]

const displayName = computed(() => auth.user?.display_name || auth.user?.username || '用户')
const initial = computed(() => displayName.value.slice(0, 1).toUpperCase())

function isActive(item: (typeof navigation)[number]): boolean {
  return item.matches?.includes(route.path) || route.path === item.path
}

function updateViewport(): void {
  mobile.value = window.matchMedia('(max-width: 960px)').matches
  if (!mobile.value) drawerOpen.value = false
}

async function handleLogout(): Promise<void> {
  await auth.logout()
  await router.replace('/login')
}

function closeDrawer(): void {
  drawerOpen.value = false
}

function toggleFullscreen(): void {
  if (document.fullscreenElement) {
    void document.exitFullscreen()
  } else {
    void document.documentElement.requestFullscreen()
  }
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
    <header class="global-header">
      <div class="header-brand">
        <n-button v-if="mobile" quaternary circle aria-label="打开导航" @click="drawerOpen = true">
          <template #icon><Menu :size="21" /></template>
        </n-button>
        <AppLogo />
      </div>

      <nav v-if="!mobile" class="desktop-nav" aria-label="主导航">
        <router-link
          v-for="item in navigation"
          :key="item.path"
          :to="item.path"
          class="top-nav-item"
          :class="{ active: isActive(item) }"
        >
          <component :is="item.icon" :size="17" :stroke-width="1.7" aria-hidden="true" />
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="header-tools">
        <n-tag
          v-if="modelSettings.status.configured && !mobile"
          size="small"
          type="success"
          :bordered="false"
        >
          {{ modelSettings.status.model_id }}
        </n-tag>
        <n-tooltip trigger="hover">
          <template #trigger>
            <n-button quaternary circle aria-label="搜索">
              <template #icon><Search :size="18" /></template>
            </n-button>
          </template>
          页面导航
        </n-tooltip>
        <n-tooltip trigger="hover">
          <template #trigger>
            <n-button quaternary circle aria-label="全屏" @click="toggleFullscreen">
              <template #icon><Maximize2 :size="18" /></template>
            </n-button>
          </template>
          全屏
        </n-tooltip>
        <n-tooltip trigger="hover">
          <template #trigger>
            <n-button quaternary circle aria-label="模型服务设置" @click="settingsOpen = true">
              <template #icon><Settings2 :size="18" /></template>
            </n-button>
          </template>
          模型服务设置
        </n-tooltip>
        <n-tooltip trigger="hover">
          <template #trigger>
            <button type="button" class="account-button" aria-label="当前用户">
              <n-avatar round size="small" color="#e6f1e9" text-color="#1c634c">{{ initial }}</n-avatar>
              <span v-if="!mobile">{{ displayName }}</span>
            </button>
          </template>
          学习者 {{ auth.learnerId }}
        </n-tooltip>
        <n-tooltip trigger="hover">
          <template #trigger>
            <n-button quaternary circle aria-label="退出登录" @click="handleLogout">
              <template #icon><LogOut :size="17" /></template>
            </n-button>
          </template>
          退出登录
        </n-tooltip>
      </div>
    </header>

    <main class="app-content"><router-view /></main>
  </div>

  <n-drawer v-model:show="drawerOpen" placement="left" :width="286">
    <n-drawer-content :native-scrollbar="false" body-content-style="padding: 0;">
      <div class="drawer-panel">
        <div class="drawer-brand"><AppLogo /></div>
        <nav class="mobile-nav" aria-label="移动端主导航">
          <section v-for="group in mobileGroups" :key="group.label">
            <span>{{ group.label }}</span>
            <router-link
              v-for="item in group.items"
              :key="item.path"
              :to="item.path"
              :class="{ active: route.path === item.path }"
              @click="closeDrawer"
            >
              <component :is="item.icon" :size="18" />
              {{ item.label }}
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
  min-height: 100vh;
  background: var(--canvas);
}

.global-header {
  position: sticky;
  z-index: 100;
  top: 0;
  display: grid;
  grid-template-columns: 242px minmax(0, 1fr) auto;
  min-height: 76px;
  background: rgba(255, 254, 248, 0.96);
  border-bottom: 1px solid #e8e1d2;
  box-shadow: 0 5px 18px rgba(87, 77, 48, 0.05);
  backdrop-filter: blur(18px);
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 10px 18px;
}

.header-brand :deep(.logo-copy strong) {
  font-family: "Noto Serif SC", "Songti SC", SimSun, serif;
}

.desktop-nav {
  display: grid;
  grid-template-columns: repeat(8, minmax(92px, 1fr));
  min-width: 0;
}

.top-nav-item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  min-width: 0;
  padding: 0 10px;
  color: #335d4e;
  border-left: 1px solid #eee9dd;
  font-size: 12px;
  font-weight: 650;
  text-decoration: none;
  transition: color 160ms ease, background 160ms ease;
}

.top-nav-item:last-child {
  border-right: 1px solid #eee9dd;
}

.top-nav-item::after {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 3px;
  content: "";
  background: transparent;
}

.top-nav-item:hover {
  color: #15553f;
  background: #fbfaf4;
}

.top-nav-item.active {
  color: #165a43;
  background: #f2f7f1;
}

.top-nav-item.active::after {
  background: #2c765a;
}

.header-tools {
  display: flex;
  align-items: center;
  gap: 1px;
  min-width: 0;
  padding: 0 16px 0 12px;
}

.account-button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  max-width: 128px;
  padding: 3px 5px;
  color: #375a4d;
  background: transparent;
  border: 0;
  cursor: default;
  font-size: 11px;
}

.account-button span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-content {
  min-height: calc(100vh - 76px);
  background:
    linear-gradient(rgba(255, 253, 246, 0.86), rgba(249, 248, 241, 0.94)),
    url('/images/herbwise-page-banner.jpg') top center / 100% 250px no-repeat;
}

.drawer-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  min-height: 100vh;
  padding: 0 16px 20px;
  background: #fffef8;
}

.drawer-brand {
  padding: 18px 4px;
  border-bottom: 1px solid #e9e3d6;
}

.mobile-nav {
  min-height: 0;
  padding: 16px 0;
  overflow-y: auto;
}

.mobile-nav section {
  display: grid;
  gap: 4px;
  margin-bottom: 14px;
}

.mobile-nav section > span {
  padding: 7px 10px;
  color: #87968e;
  font-size: 10px;
  font-weight: 700;
}

.mobile-nav a {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 44px;
  padding: 9px 11px;
  color: #3f5d52;
  border-radius: 6px;
  text-decoration: none;
}

.mobile-nav a.active,
.mobile-nav a:hover {
  color: #15543e;
  background: #eaf3ec;
}

@media (max-width: 1320px) {
  .global-header {
    grid-template-columns: 210px minmax(0, 1fr) auto;
  }

  .header-brand {
    padding-inline: 13px;
  }

  .desktop-nav {
    grid-template-columns: repeat(8, minmax(78px, 1fr));
  }

  .top-nav-item {
    gap: 5px;
    padding-inline: 5px;
    font-size: 11px;
  }

  .header-tools {
    padding-inline: 7px;
  }
}

@media (max-width: 1080px) {
  .top-nav-item span {
    display: none;
  }

  .desktop-nav {
    grid-template-columns: repeat(8, minmax(46px, 1fr));
  }
}

@media (max-width: 960px) {
  .global-header {
    grid-template-columns: minmax(0, 1fr) auto;
    min-height: 68px;
  }

  .header-brand {
    padding: 8px 12px;
  }

  .header-tools {
    padding-right: 9px;
  }

  .app-content {
    min-height: calc(100vh - 68px);
  }
}
</style>
