<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, CheckCircle2, Target } from 'lucide-vue-next'
import { NAlert, NButton, NEmpty, NProgress, NSpin, NTag } from 'naive-ui'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { LearnerDimension, LearnerProfile, LearningPlan, LearningTask, ResourceItem, WeakPoint } from '../types/api'
import { dimensionLabels, getErrorMessage } from '../utils/format'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const errorText = ref('')
const profile = ref<LearnerProfile | null>(null)
const dimensions = ref<LearnerDimension[]>([])
const assessmentReady = ref(false)
const plan = ref<LearningPlan | null>(null)
const tasks = ref<LearningTask[]>([])
const resources = ref<ResourceItem[]>([])
const weakPoints = ref<WeakPoint[]>([])

const todayTask = computed(() => tasks.value.find(task => task.status === 'in_progress') || tasks.value.find(task => task.status === 'pending') || null)
const setupProgress = computed(() => Number(Boolean(profile.value)) + Number(assessmentReady.value) + Number(Boolean(plan.value)))
const nextAction = computed(() => {
  if (!profile.value) return { title: '完善学习档案', description: '告诉我们你的学习基础，系统才能安排合适的学习内容。', label: '完善学习档案', action: () => router.push('/onboarding') }
  if (!assessmentReady.value) return { title: '完成基础测评', description: '预计需要 2 分钟，测评结果将用于生成你的学习计划。', label: '开始基础测评', action: () => router.push('/diagnosis') }
  if (!plan.value) return { title: '生成个性化学习计划', description: '系统会依据测评结果和薄弱点安排今天的学习内容。', label: '生成我的学习计划', action: generatePlan }
  if (todayTask.value) return { title: todayTask.value.title, description: '这是当前最适合你的今日任务，完成后会自动更新学习画像。', label: todayTask.value.status === 'in_progress' ? '继续今日学习' : '开始今日学习', action: () => router.push('/learning-center') }
  return { title: '今天的学习已完成', description: '回顾学习记录，或在学习中心查看下一步安排。', label: '查看学习记录', action: () => router.push('/learning-center') }
})

async function generatePlan(): Promise<void> {
  try {
    await api.generateLearningPlan(auth.learnerId)
    await load()
  } catch (error) {
    errorText.value = getErrorMessage(error, '学习计划生成失败，请稍后重试。')
  }
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  const results = await Promise.allSettled([
    api.getProfile(auth.learnerId),
    api.getDimensions(auth.learnerId),
    api.getInitialTestStatus(auth.learnerId),
    api.getCurrentLearningPlan(auth.learnerId),
    api.listLearningTasks(auth.learnerId),
    api.listResources(auth.learnerId, 6),
    api.getWeakPoints(auth.learnerId),
  ])
  if (results[0].status === 'fulfilled') profile.value = results[0].value
  if (results[1].status === 'fulfilled') dimensions.value = results[1].value
  if (results[2].status === 'fulfilled') assessmentReady.value = results[2].value.completed
  if (results[3].status === 'fulfilled') plan.value = results[3].value
  if (results[4].status === 'fulfilled') tasks.value = results[4].value.items
  if (results[5].status === 'fulfilled') resources.value = results[5].value.items
  if (results[6].status === 'fulfilled') weakPoints.value = results[6].value.filter(item => !item.is_resolved).slice(0, 3)
  const failed = results.find(item => item.status === 'rejected')
  if (failed?.status === 'rejected' && profile.value) errorText.value = getErrorMessage(failed.reason, '部分首页数据加载失败，请刷新后重试。')
  loading.value = false
}

onMounted(load)
</script>

<template>
  <div class="page hub-page">
    <PageHeader title="首页" :meta="profile?.name || '今天也一起稳步学习'" />
    <n-alert v-if="errorText" type="warning" closable class="hub-alert" @close="errorText = ''">{{ errorText }}</n-alert>
    <n-spin :show="loading">
      <section class="next-task-band">
        <div>
          <span class="eyebrow">今日下一步</span>
          <h2>{{ nextAction.title }}</h2>
          <p>{{ nextAction.description }}</p>
        </div>
        <n-button type="primary" size="large" @click="nextAction.action">
          {{ nextAction.label }}
          <template #icon><ArrowRight :size="18" /></template>
        </n-button>
      </section>

      <section class="journey-strip" aria-label="个性化学习准备进度">
        <div :class="{ done: Boolean(profile) }"><span>1</span><strong>学习档案</strong><small>{{ profile ? '已完成' : '待完成' }}</small></div>
        <div :class="{ done: assessmentReady }"><span>2</span><strong>基础测评</strong><small>{{ assessmentReady ? '已完成' : '待完成' }}</small></div>
        <div :class="{ done: Boolean(plan) }"><span>3</span><strong>学习计划</strong><small>{{ plan ? '已准备' : '待生成' }}</small></div>
      </section>

      <section class="dashboard-grid">
        <article class="surface dashboard-card">
          <span class="eyebrow">今日任务</span>
          <template v-if="todayTask"><h3>{{ todayTask.title }}</h3><p>{{ todayTask.status === 'in_progress' ? '正在进行中' : '等待开始' }} · 预计 {{ todayTask.estimated_minutes || 10 }} 分钟</p></template>
          <n-empty v-else size="small" description="还没有今日任务" />
        </article>
        <article class="surface dashboard-card">
          <span class="eyebrow">当前薄弱点</span>
          <div v-if="weakPoints.length" class="weak-list"><n-tag v-for="item in weakPoints" :key="`${item.dimension_code}-${item.knowledge_point}`" type="warning" :bordered="false">{{ dimensionLabels[item.dimension_code] || item.dimension_code }} · {{ item.knowledge_point }}</n-tag></div>
          <n-empty v-else size="small" description="继续学习后会形成薄弱点提示" />
        </article>
        <article class="surface dashboard-card">
          <span class="eyebrow">学习进度</span>
          <div class="progress-copy"><strong>{{ setupProgress }} / 3</strong><span>个性化学习准备度</span></div>
          <n-progress type="line" :percentage="Math.round(setupProgress / 3 * 100)" :height="8" :show-indicator="false" color="#1f6b4f" rail-color="#edf1ee" />
        </article>
        <article class="surface dashboard-card recognition-card">
          <Target :size="20" /><div><span class="eyebrow">最近识别</span><p>{{ resources.length ? '已为你的学习任务准备相关资料' : '完成智能识药后，结果会沉淀到学习路径中。' }}</p></div>
        </article>
      </section>

      <section v-if="dimensions.length" class="learning-snapshot surface">
        <div class="snapshot-heading"><span class="eyebrow">能力快照</span><h2>六维学习基础</h2><p>学习记录会持续更新你的能力画像。</p></div>
        <div class="snapshot-bars"><div v-for="item in dimensions" :key="item.dimension_code"><span>{{ dimensionLabels[item.dimension_code] }}</span><n-progress type="line" :percentage="item.score" :height="7" :show-indicator="false" :color="item.score < 60 ? '#bd7a20' : '#1f6b4f'" rail-color="#edf1ee" /><strong>{{ Math.round(item.score) }}</strong></div></div>
      </section>
      <section v-else class="surface empty-panel"><CheckCircle2 :size="20" /><span>完成基础测评后，这里会展示你的学习进度。</span></section>
    </n-spin>
  </div>
</template>

<style scoped>
.hub-alert { margin-bottom: 16px; }
.next-task-band { display:flex; justify-content:space-between; align-items:center; gap:24px; min-height:148px; padding:26px 28px; color:#fff; background:#17211c; }.next-task-band h2 { margin:6px 0 9px; font-size:22px; }.next-task-band p { margin:0; color:#bdc9c1; font-size:13px; }.next-task-band .eyebrow { color:#8dc6a6; }.journey-strip { display:grid; grid-template-columns:repeat(3,1fr); margin-top:16px; background:#fff; border:1px solid var(--line); }.journey-strip>div { display:grid; grid-template-columns:28px minmax(0,1fr); gap:2px 8px; align-items:center; min-height:72px; padding:12px 16px; border-right:1px solid var(--line); }.journey-strip>div:last-child { border-right:0; }.journey-strip span { grid-row:1 / span 2; display:grid; width:26px; height:26px; place-items:center; border-radius:50%; color:var(--muted); background:#edf1ee; font-size:10px; }.journey-strip strong { color:var(--ink); font-size:12px; }.journey-strip small { color:var(--subtle); font-size:9px; }.journey-strip .done span { color:#fff; background:var(--primary); }.dashboard-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-top:18px; }.dashboard-card { min-height:156px; padding:19px; }.dashboard-card h3 { margin:10px 0 6px; color:var(--ink); font-size:15px; line-height:1.5; }.dashboard-card p { color:var(--muted); font-size:12px; line-height:1.7; }.weak-list { display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; }.progress-copy { display:flex; align-items:baseline; gap:8px; margin:17px 0 12px; }.progress-copy strong { color:var(--primary); font-size:25px; }.progress-copy span { color:var(--muted); font-size:11px; }.recognition-card { display:flex; gap:11px; }.recognition-card svg { flex:none; color:var(--primary); }.recognition-card p { margin:8px 0 0; }.learning-snapshot { display:grid; grid-template-columns:260px minmax(0,1fr); gap:28px; margin-top:18px; padding:22px; }.snapshot-heading h2 { margin:5px 0; font-size:18px; }.snapshot-heading p { color:var(--muted); font-size:12px; line-height:1.7; }.snapshot-bars { display:grid; gap:11px; }.snapshot-bars>div { display:grid; grid-template-columns:95px minmax(0,1fr) 30px; align-items:center; gap:10px; font-size:11px; }.snapshot-bars strong { color:var(--ink); text-align:right; }.empty-panel { display:flex; align-items:center; gap:9px; margin-top:18px; padding:22px; color:var(--muted); font-size:13px; } @media(max-width:900px){.dashboard-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.learning-snapshot{grid-template-columns:1fr}} @media(max-width:620px){.next-task-band{align-items:stretch;flex-direction:column}.next-task-band .n-button{width:100%}.journey-strip,.dashboard-grid{grid-template-columns:1fr}.journey-strip>div{border-right:0;border-bottom:1px solid var(--line)}.snapshot-bars>div{grid-template-columns:75px minmax(0,1fr) 26px}}
</style>
