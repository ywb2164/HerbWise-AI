<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAvatar, NButton, NDrawer, NDrawerContent, NTooltip } from 'naive-ui'
import {
  Activity,
  Bot,
  BrainCircuit,
  ChevronLeft,
  FileCode2,
  FlaskConical,
  Gauge,
  GraduationCap,
  ListTree,
  LogOut,
  Maximize2,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  RefreshCw,
  Settings2,
  ShieldCheck,
  UsersRound,
  X,
} from 'lucide-vue-next'
import AppLogo from '../components/AppLogo.vue'
import { useAuthStore } from '../stores/auth'

interface NavigationItem {
  label: string
  path: string
  icon: Component
}

interface NavigationGroup {
  label: string
  items: NavigationItem[]
}

interface VisitedTab {
  path: string
  title: string
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const collapsed = ref(false)
const mobile = ref(false)
const mobileOpen = ref(false)
const visitedTabs = ref<VisitedTab[]>([{ path: '/admin/overview', title: '管理总览' }])

const navigation: NavigationGroup[] = [
  {
    label: '控制台',
    items: [{ label: '管理总览', path: '/admin/overview', icon: Gauge }],
  },
  {
    label: '组织权限',
    items: [
      { label: '用户管理', path: '/admin/users', icon: UsersRound },
      { label: '角色管理', path: '/admin/roles', icon: ShieldCheck },
      { label: '菜单管理', path: '/admin/menus', icon: ListTree },
    ],
  },
  {
    label: 'AI 运行',
    items: [
      { label: '模型服务', path: '/admin/models', icon: BrainCircuit },
      { label: '智能体编排', path: '/admin/agents', icon: Bot },
      { label: '提示词模板', path: '/admin/prompts', icon: FileCode2 },
      { label: '测试用例', path: '/admin/tests', icon: FlaskConical },
    ],
  },
  {
    label: '系统运维',
    items: [
      { label: '运行日志', path: '/admin/operations', icon: Activity },
      { label: '系统配置', path: '/admin/system', icon: Settings2 },
    ],
  },
]

const activeTitle = computed(() => String(route.meta.title || '管理总览'))
const displayName = computed(() => auth.user?.display_name || auth.user?.username || '管理员')
const initial = computed(() => displayName.value.slice(0, 1).toUpperCase())

function updateViewport(): void {
  mobile.value = window.matchMedia('(max-width: 900px)').matches
  if (!mobile.value) mobileOpen.value = false
}

function toggleSidebar(): void {
  if (mobile.value) mobileOpen.value = true
  else collapsed.value = !collapsed.value
}

function closeMobile(): void {
  mobileOpen.value = false
}

function refreshPage(): void {
  router.go(0)
}

async function toggleFullscreen(): Promise<void> {
  if (document.fullscreenElement) await document.exitFullscreen()
  else await document.documentElement.requestFullscreen()
}

async function handleLogout(): Promise<void> {
  await auth.logout()
  await router.replace('/login')
}

function closeTab(tab: VisitedTab): void {
  if (tab.path === '/admin/overview') return
  const index = visitedTabs.value.findIndex((item) => item.path === tab.path)
  visitedTabs.value.splice(index, 1)
  if (route.path === tab.path) {
    const next = visitedTabs.value[Math.max(0, index - 1)] || visitedTabs.value[0]
    void router.push(next.path)
  }
}

watch(
  () => route.path,
  (path) => {
    if (!path.startsWith('/admin/')) return
    if (!visitedTabs.value.some((tab) => tab.path === path)) {
      visitedTabs.value.push({ path, title: activeTitle.value })
    }
  },
  { immediate: true },
)

onMounted(() => {
  updateViewport()
  window.addEventListener('resize', updateViewport)
})

onBeforeUnmount(() => window.removeEventListener('resize', updateViewport))
</script>

<template>
  <div class="admin-shell" :class="{ collapsed }">
    <aside class="admin-sider">
      <div class="admin-brand">
        <AppLogo :compact="collapsed" to="/admin/overview" />
      </div>
      <nav class="admin-navigation" aria-label="管理员导航">
        <section v-for="group in navigation" :key="group.label" class="nav-group">
          <span v-if="!collapsed" class="nav-group-label">{{ group.label }}</span>
          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="admin-nav-item"
            :title="collapsed ? item.label : undefined"
          >
            <component :is="item.icon" :size="19" :stroke-width="1.8" />
            <span v-if="!collapsed">{{ item.label }}</span>
          </router-link>
        </section>
      </nav>
      <div class="sider-collapse">
        <n-button quaternary circle :aria-label="collapsed ? '展开侧栏' : '收起侧栏'" @click="collapsed = !collapsed">
          <template #icon>
            <PanelLeftOpen v-if="collapsed" :size="18" />
            <PanelLeftClose v-else :size="18" />
          </template>
        </n-button>
      </div>
    </aside>

    <div class="admin-main">
      <header class="admin-header">
        <div class="header-leading">
          <n-button quaternary circle aria-label="切换导航" @click="toggleSidebar">
            <template #icon><Menu v-if="mobile" :size="20" /><ChevronLeft v-else :size="20" /></template>
          </n-button>
          <div class="admin-breadcrumb"><span>系统管理</span><strong>{{ activeTitle }}</strong></div>
        </div>
        <div class="header-actions">
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button quaternary circle aria-label="刷新页面" @click="refreshPage">
                <template #icon><RefreshCw :size="18" /></template>
              </n-button>
            </template>
            刷新页面
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
              <n-button quaternary circle aria-label="进入学生端" @click="router.push('/dashboard')">
                <template #icon><GraduationCap :size="19" /></template>
              </n-button>
            </template>
            进入学生端
          </n-tooltip>
          <div class="admin-account">
            <n-avatar round size="small" color="#dcebe3" text-color="#195b43">{{ initial }}</n-avatar>
            <div><strong>{{ displayName }}</strong><span>管理员</span></div>
          </div>
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-button quaternary circle aria-label="退出登录" @click="handleLogout">
                <template #icon><LogOut :size="18" /></template>
              </n-button>
            </template>
            退出登录
          </n-tooltip>
        </div>
      </header>

      <div class="admin-tabs" role="tablist" aria-label="已访问页面">
        <button
          v-for="tab in visitedTabs"
          :key="tab.path"
          type="button"
          class="admin-tab"
          :class="{ active: route.path === tab.path }"
          @click="router.push(tab.path)"
        >
          <span>{{ tab.title }}</span>
          <X
            v-if="tab.path !== '/admin/overview'"
            :size="13"
            aria-label="关闭标签"
            @click.stop="closeTab(tab)"
          />
        </button>
      </div>

      <main class="admin-content"><router-view /></main>
    </div>
  </div>

  <n-drawer v-model:show="mobileOpen" placement="left" :width="280">
    <n-drawer-content :native-scrollbar="false" body-content-style="padding: 0;">
      <div class="mobile-admin-panel">
        <div class="admin-brand"><AppLogo to="/admin/overview" /></div>
        <nav class="admin-navigation" aria-label="移动端管理员导航">
          <section v-for="group in navigation" :key="group.label" class="nav-group">
            <span class="nav-group-label">{{ group.label }}</span>
            <router-link
              v-for="item in group.items"
              :key="item.path"
              :to="item.path"
              class="admin-nav-item"
              @click="closeMobile"
            >
              <component :is="item.icon" :size="19" :stroke-width="1.8" />
              <span>{{ item.label }}</span>
            </router-link>
          </section>
        </nav>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.admin-shell {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  min-height: 100vh;
  background: #f7fafc;
  transition: grid-template-columns 180ms ease;
}

.admin-shell.collapsed {
  grid-template-columns: 64px minmax(0, 1fr);
}

.admin-sider {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: #fff;
  border-right: 1px solid #e7ece9;
  box-shadow: 2px 0 8px rgba(29, 35, 41, 0.04);
  z-index: 20;
}

.admin-brand {
  display: flex;
  align-items: center;
  height: 64px;
  padding: 0 12px;
  border-bottom: 1px solid #edf0ee;
}

.collapsed .admin-brand {
  justify-content: center;
  padding: 0;
}

.admin-navigation {
  display: grid;
  align-content: start;
  gap: 12px;
  padding: 12px 9px;
  overflow-y: auto;
}

.nav-group {
  display: grid;
  gap: 3px;
}

.nav-group-label {
  min-height: 24px;
  padding: 5px 10px 3px;
  color: #98a19c;
  font-size: 10px;
  font-weight: 650;
}

.admin-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 0 11px;
  color: #526058;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 550;
  text-decoration: none;
}

.admin-nav-item:hover {
  color: var(--ink);
  background: #f4f7f5;
}

.admin-nav-item.router-link-active {
  color: var(--primary-strong);
  background: var(--primary-soft);
  font-weight: 650;
}

.collapsed .admin-navigation {
  gap: 4px;
  padding: 10px 8px;
}

.collapsed .nav-group {
  gap: 4px;
}

.collapsed .admin-nav-item {
  justify-content: center;
  padding: 0;
}

.sider-collapse {
  display: flex;
  justify-content: flex-end;
  margin-top: auto;
  padding: 10px;
  border-top: 1px solid #edf0ee;
}

.collapsed .sider-collapse {
  justify-content: center;
}

.admin-main {
  min-width: 0;
}

.admin-header {
  position: sticky;
  top: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: 56px;
  padding: 0 18px;
  background: rgba(255, 255, 255, 0.97);
  border-bottom: 1px solid #e7ece9;
  box-shadow: 0 1px 2px rgba(0, 21, 41, 0.05);
  z-index: 15;
}

.header-leading,
.header-actions,
.admin-account {
  display: flex;
  align-items: center;
}

.header-leading,
.header-actions {
  gap: 6px;
}

.admin-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 6px;
  font-size: 12px;
}

.admin-breadcrumb span { color: var(--muted); }
.admin-breadcrumb span::after { content: '/'; margin-left: 8px; color: #b6beba; }
.admin-breadcrumb strong { color: var(--ink); font-weight: 650; }

.admin-account {
  gap: 8px;
  margin-left: 6px;
  padding-left: 12px;
  border-left: 1px solid var(--line);
}

.admin-account > div {
  display: grid;
  min-width: 92px;
}

.admin-account strong { color: var(--ink); font-size: 12px; }
.admin-account span { color: var(--muted); font-size: 9px; }

.admin-tabs {
  position: sticky;
  top: 56px;
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 42px;
  padding: 6px 12px 0;
  overflow-x: auto;
  background: #fff;
  border-bottom: 1px solid #e7ece9;
  box-shadow: 0 1px 2px rgba(0, 21, 41, 0.04);
  z-index: 14;
}

.admin-tab {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex: 0 0 auto;
  min-height: 32px;
  padding: 0 11px;
  color: #68756d;
  background: #f7f9f8;
  border: 1px solid #e5eae7;
  border-bottom: 0;
  border-radius: 5px 5px 0 0;
  cursor: pointer;
  font-size: 11px;
}

.admin-tab.active {
  color: var(--primary-strong);
  background: #fff;
  border-color: #cfdad3;
  font-weight: 650;
}

.admin-tab svg { color: #98a29c; }

.admin-content {
  min-width: 0;
  min-height: calc(100vh - 98px);
}

.mobile-admin-panel {
  min-height: 100vh;
  background: #fff;
}

@media (max-width: 900px) {
  .admin-shell,
  .admin-shell.collapsed {
    grid-template-columns: 1fr;
  }

  .admin-sider { display: none; }
  .admin-header { padding: 0 10px; }
  .admin-account > div { display: none; }
  .admin-account { min-width: 0; padding-left: 8px; }
}

@media (max-width: 560px) {
  .admin-breadcrumb span,
  .header-actions > :nth-child(1),
  .header-actions > :nth-child(2) {
    display: none;
  }

  .admin-tabs { padding-inline: 8px; }
}
</style>
