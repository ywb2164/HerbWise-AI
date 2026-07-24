import { createRouter, createWebHistory } from 'vue-router'
import { api } from '../services/api'
import { clearAuthStorage, getAccessToken, getStoredUser, handoffToAdmin } from '../services/auth-storage'
import { isHttpStatus } from '../utils/format'

let checkedLearnerId = ''

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { title: '登录', public: true },
    },
    {
      path: '/',
      component: () => import('../layouts/AppShell.vue'),
      children: [
        { path: '', redirect: '/dashboard' },
        {
          path: 'onboarding',
          name: 'onboarding',
          component: () => import('../views/ProfileOnboardingView.vue'),
          meta: { title: '构建学习画像', allowWithoutProfile: true },
        },
        {
          path: 'diagnosis',
          name: 'diagnosis',
          component: () => import('../views/DiagnosisView.vue'),
          meta: { title: '学习能力诊断' },
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('../views/DashboardView.vue'),
          meta: { title: '学习工作台' },
        },
        {
          path: 'recognition',
          name: 'recognition',
          component: () => import('../views/RecognitionView.vue'),
          meta: { title: '药材辨识' },
        },
        {
          path: 'simulation',
          name: 'simulation',
          component: () => import('../views/SimulationView.vue'),
          meta: { title: '虚拟仿真实训' },
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('../views/ProfileView.vue'),
          meta: { title: '画像档案' },
        },
        {
          path: 'knowledge',
          name: 'knowledge',
          component: () => import('../views/KnowledgeView.vue'),
          meta: { title: '药材知识' },
        },
        {
          path: 'resources',
          name: 'resources',
          component: () => import('../views/ResourcesView.vue'),
          meta: { title: '学习资源' },
        },
        {
          path: 'learning-tasks',
          name: 'learning-tasks',
          component: () => import('../views/LearningTasksView.vue'),
          meta: { title: '学习任务' },
        },
        {
          path: 'reports',
          name: 'reports',
          component: () => import('../views/ReportsView.vue'),
          meta: { title: '学习报告' },
        },
        {
          path: 'traces',
          name: 'traces',
          component: () => import('../views/TracesView.vue'),
          meta: { title: '证据链' },
        },
        {
          path: 'metrics',
          name: 'metrics',
          component: () => import('../views/MetricsView.vue'),
          meta: { title: '测试指标大屏' },
        },
      ],
    },
    { path: '/home', redirect: '/dashboard' },
    { path: '/imgPredict', redirect: { path: '/recognition', query: { source: 'upload' } } },
    { path: '/imgPredictBatch', redirect: { path: '/recognition', query: { source: 'upload' } } },
    { path: '/dynamicPredict', redirect: { path: '/recognition', query: { source: 'upload' } } },
    { path: '/videoPredict', redirect: { path: '/recognition', query: { source: 'upload' } } },
    { path: '/cameraPredict', redirect: { path: '/recognition', query: { source: 'camera' } } },
    { path: '/virtualLab', redirect: '/simulation' },
    { path: '/smartChat', redirect: '/knowledge' },
    { path: '/medicalAgent', redirect: '/resources' },
    { path: '/traceCenter', redirect: '/traces' },
    { path: '/trace-dashboard', redirect: '/traces' },
    { path: '/trace-dashboard-3d', redirect: '/traces' },
    { path: '/screen', redirect: '/metrics' },
    { path: '/personal', redirect: '/profile' },
    { path: '/usermanage', redirect: { path: '/login', query: { role: 'admin' } } },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach(async to => {
  if (to.name === 'login' && to.query.logout === '1') {
    clearAuthStorage()
    checkedLearnerId = ''
    return {
      name: 'login',
      query: to.query.role === 'admin' ? { role: 'admin' } : {},
      replace: true,
    }
  }

  const token = getAccessToken()
  const user = getStoredUser()
  const isAdmin = Boolean(user?.roles.includes('admin'))

  if (to.path.startsWith('/admin')) {
    if (!token) return { name: 'login', query: { role: 'admin' } }
    if (isAdmin) {
      handoffToAdmin()
      return false
    }
    return { name: 'dashboard' }
  }

  if (!to.meta.public && !token) return { name: 'login', query: { redirect: to.fullPath } }
  if (to.name === 'login' && token) {
    if (to.query.role === 'admin') {
      if (isAdmin) {
        handoffToAdmin()
        return false
      }
      return true
    }
    return { name: 'dashboard' }
  }

  if (!to.meta.public && !to.meta.allowWithoutProfile && user?.learner_id && checkedLearnerId !== user.learner_id) {
    try {
      const [, history] = await Promise.all([
        api.getProfile(user.learner_id),
        api.getProfileHistory(user.learner_id),
      ])
      if (!history.some(item => item.event_type === 'initial_test_submitted')) {
        return { name: 'onboarding' }
      }
      checkedLearnerId = user.learner_id
    } catch (error) {
      if (isHttpStatus(error, 404)) return { name: 'onboarding' }
    }
  }

  document.title = `${String(to.meta.title || '学习工作台')} | 本草智策`
  return true
})

export default router
