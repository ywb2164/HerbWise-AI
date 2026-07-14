<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  NAlert,
  NButton,
  NEmpty,
  NInput,
  NModal,
  NSpace,
  NSpin,
  NSteps,
  NStep,
  NTabPane,
  NTag,
  NTabs,
  useMessage,
} from 'naive-ui'
import { ArrowRight, CheckCircle2, RefreshCw } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { LearningPlan, LearningPlanItem, LearningTask, ResourceGenerationJob, ResourceItem, WeakPoint } from '../types/api'
import { formatDate, getApiErrorCode, getErrorMessage } from '../utils/format'
import { learningDifficulty, learningDimension, learningResourceType, learningTaskStatus, learningText } from '../utils/learningDisplay'

const auth = useAuthStore()
const router = useRouter()
const message = useMessage()
const loading = ref(true)
const errorText = ref('')
const profileReady = ref(false)
const assessmentReady = ref(false)
const plan = ref<LearningPlan | null>(null)
const tasks = ref<LearningTask[]>([])
const resources = ref<ResourceItem[]>([])
const weakPoints = ref<WeakPoint[]>([])
const jobs = ref<ResourceGenerationJob[]>([])
const runningJob = ref<ResourceGenerationJob | null>(null)
const freeModal = ref(false)
const freeTopic = ref('')
const freeGenerating = ref(false)
const activeTab = ref('today')
const staleReference = ref(false)
const showGuide = ref(false)

const executableTask = computed(() => tasks.value.find(task => task.status === 'in_progress') || tasks.value.find(task => task.status === 'pending') || null)
const readiness = computed(() => Number(profileReady.value) + Number(assessmentReady.value) + Number(Boolean(plan.value)))
const approvedResources = computed(() => resources.value.filter(item => item.status === 'approved'))
const activeJobs = computed(() => jobs.value.filter(item => ['pending', 'loading_context', 'retrieving', 'generating', 'reviewing', 'rewriting'].includes(item.status)))
const nextAction = computed(() => {
  if (!profileReady.value) return { title: '完成学习档案', description: '先补充你的学习背景，系统才能为你安排合适的学习内容。', label: '完善学习档案', action: () => router.push('/onboarding') }
  if (!assessmentReady.value) return { title: '完成基础测评', description: '系统需要了解你的学习基础，预计需要 2 分钟。', label: '开始基础测评', action: () => router.push('/diagnosis') }
  if (!plan.value) return { title: '生成个性化学习计划', description: '系统将根据测评结果和薄弱点安排今天的学习内容。', label: '生成我的学习计划', action: generatePlan }
  if (executableTask.value) return { title: executableTask.value.title, description: '这是当前最适合你的今日任务，完成后会自动更新学习画像。', label: executableTask.value.status === 'in_progress' ? '继续学习' : '开始今日学习', action: () => prepareTask(executableTask.value!) }
  return { title: '今天的学习已完成', description: '你可以回顾学习资源，或生成新的个性化学习计划。', label: '查看学习记录', action: () => router.push('/reports') }
})

function jobLabel(status: string): string {
  return {
    pending: '正在排队', loading_context: '正在分析学习目标', retrieving: '正在查找专业资料', generating: '正在生成学习内容', reviewing: '正在检查内容质量', rewriting: '正在优化内容', completed: '学习资料已准备完成', degraded: '已使用基础模板生成', rejected: '本次生成未通过质量检查',
  }[status] || '正在准备学习资料'
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  const result = await Promise.allSettled([
    api.getProfile(auth.learnerId), api.getInitialTestStatus(auth.learnerId), api.getCurrentLearningPlan(auth.learnerId),
    api.listLearningTasks(auth.learnerId), api.listResources(auth.learnerId), api.getWeakPoints(auth.learnerId), api.listResourceGenerationJobs(auth.learnerId),
  ])
  profileReady.value = result[0].status === 'fulfilled'
  if (result[1].status === 'fulfilled') assessmentReady.value = result[1].value.completed
  if (result[2].status === 'fulfilled') plan.value = result[2].value
  if (result[3].status === 'fulfilled') tasks.value = result[3].value.items
  if (result[4].status === 'fulfilled') resources.value = result[4].value.items
  if (result[5].status === 'fulfilled') weakPoints.value = result[5].value.filter(item => !item.is_resolved).slice(0, 3)
  if (result[6].status === 'fulfilled') jobs.value = result[6].value.items
  const failed = result.find(item => item.status === 'rejected')
  if (failed?.status === 'rejected' && profileReady.value) errorText.value = getErrorMessage(failed.reason, '部分学习数据加载失败，请刷新后重试')
  loading.value = false
}

async function generatePlan(): Promise<void> {
  try {
    plan.value = await api.generateLearningPlan(auth.learnerId)
    await load()
    message.success('个性化学习计划已准备完成')
  } catch (error) { errorText.value = getErrorMessage(error, '学习计划生成失败') }
}

function planItemFor(task: LearningTask): LearningPlanItem | undefined {
  return plan.value?.items.find(item => item.linked_task_id === task.task_id)
}

async function prepareTask(task: LearningTask): Promise<void> {
  const planItem = planItemFor(task)
  const existing = approvedResources.value.find(resource => resource.task_id === task.task_id || (planItem && resource.learning_plan_item_id === planItem.item_id))
  if (existing) {
    await router.push({ name: 'resources', query: { resource: existing.resource_id } })
    return
  }
  try {
    runningJob.value = await api.createResourceGenerationJob({
      learner_id: auth.learnerId,
      learning_plan_item_id: planItem?.item_id,
      task_id: task.task_id,
      resource_type: planItem?.resource_type === 'comparison_card' ? 'comparison_card' : 'practice_guide',
      difficulty: task.difficulty,
    })
    await load()
    if (runningJob.value.resource_id) {
      message.success('学习资料已准备完成，现在可以开始任务')
      await router.push({ name: 'learning-tasks' })
    }
  } catch (error) {
    staleReference.value = getApiErrorCode(error) === 'PLAN_ITEM_NOT_FOUND'
    errorText.value = getErrorMessage(error, '学习资料准备失败')
  }
}

async function refreshPlanAfterReferenceError(): Promise<void> {
  staleReference.value = false
  activeTab.value = 'today'
  await load()
}

async function generateFreeResource(): Promise<void> {
  if (!freeTopic.value.trim()) { message.warning('请输入想学习的主题'); return }
  freeGenerating.value = true
  try {
    runningJob.value = await api.createResourceGenerationJob({ learner_id: auth.learnerId, topic: freeTopic.value.trim(), resource_type: 'knowledge_card', difficulty: 'basic' })
    freeModal.value = false
    freeTopic.value = ''
    await load()
    message.success(runningJob.value.resource_id ? '学习资料已准备完成' : jobLabel(runningJob.value.status))
  } catch (error) { errorText.value = getErrorMessage(error, '自定义学习资料生成失败') }
  finally { freeGenerating.value = false }
}

onMounted(() => {
  showGuide.value = localStorage.getItem('herbwise.learning-center-guide') !== 'seen'
  void load()
})

function dismissGuide(): void {
  localStorage.setItem('herbwise.learning-center-guide', 'seen')
  showGuide.value = false
}
</script>

<template>
  <div class="page learning-center-page">
    <PageHeader title="学习中心" eyebrow="本草智策" meta="按步骤完成今天的个性化学习">
      <template #actions><n-button secondary :loading="loading" @click="load"><template #icon><RefreshCw :size="16" /></template>刷新</n-button></template>
    </PageHeader>
    <n-alert v-if="errorText" type="warning" closable class="center-alert" @close="errorText = ''">{{ errorText }}</n-alert>
    <n-alert v-if="staleReference" type="warning" class="center-alert" title="原学习任务已更新">
      <p>这项学习任务可能已经被重新生成或删除，请刷新最新学习计划。</p>
      <n-space><n-button size="small" @click="refreshPlanAfterReferenceError">刷新学习计划</n-button><n-button size="small" text @click="activeTab = 'today'">返回今日学习</n-button></n-space>
    </n-alert>
    <n-spin :show="loading">
      <section v-if="readiness < 3" class="onboarding-card surface">
        <div><span class="eyebrow">欢迎使用本草智策</span><h2>个性化学习准备度 {{ readiness }} / 3</h2><p>完成基础测评后，系统会自动生成适合你的学习计划和今日任务。</p></div>
        <n-steps vertical size="small" :current="readiness"><n-step title="已建立学习档案" :status="profileReady ? 'finish' : 'process'" /><n-step title="已完成基础测评" :status="assessmentReady ? 'finish' : 'wait'" /><n-step title="已生成学习计划" :status="plan ? 'finish' : 'wait'" /></n-steps>
      </section>
      <section class="next-step surface">
        <div><span class="eyebrow">唯一下一步</span><h2>{{ nextAction.title }}</h2><p>{{ nextAction.description }}</p></div>
        <n-button type="primary" size="large" @click="nextAction.action">{{ nextAction.label }}<template #icon><ArrowRight :size="18" /></template></n-button>
      </section>
      <section v-if="runningJob || activeJobs.length" class="job-card surface"><div><span class="eyebrow">学习资料准备进度</span><h3>{{ jobLabel((runningJob || activeJobs[0]).status) }}</h3><p>分析学习目标 → 整理基础知识 → 生成内容 → 检查质量</p></div><n-tag type="info" :bordered="false">{{ (runningJob || activeJobs[0]).status === 'retrieving' ? '正在查找专业资料' : '正在准备' }}</n-tag></section>
      <n-tabs v-model:value="activeTab" type="segment" animated class="center-tabs">
        <n-tab-pane name="today" tab="今日学习"><section v-if="executableTask" class="today-task surface"><span class="eyebrow">今日任务</span><h2>{{ learningText(executableTask.title) }}</h2><p>{{ learningText(planItemFor(executableTask)?.reason) || '根据你的当前薄弱点推荐。' }}</p><div><n-tag :bordered="false">{{ learningDifficulty(executableTask.difficulty) }}</n-tag><span>预计 {{ executableTask.estimated_minutes || 10 }} 分钟</span></div><n-button type="primary" @click="prepareTask(executableTask)">{{ executableTask.status === 'in_progress' ? '继续学习' : '开始学习' }}</n-button></section><n-empty v-else description="还没有今日任务"><template #extra><n-button type="primary" @click="generatePlan">生成学习计划</n-button></template></n-empty></n-tab-pane>
        <n-tab-pane name="plan" tab="我的计划"><section v-if="plan" class="plan-overview surface"><h3>{{ learningText(plan.goal) }}</h3><p>{{ learningText(plan.summary) }}</p><article v-for="item in plan.items" :key="item.item_id"><strong>{{ learningText(item.title) }}</strong><span>{{ item.estimated_minutes }} 分钟 · {{ learningTaskStatus(item.status) }}</span></article></section><n-empty v-else description="还没有学习计划"><template #extra><n-button type="primary" @click="nextAction.action">{{ nextAction.label }}</n-button></template></n-empty></n-tab-pane>
        <n-tab-pane name="resources" tab="学习资源"><section v-if="resources.length" class="resource-list surface"><article v-for="resource in resources" :key="resource.resource_id"><div><strong>{{ learningText(resource.title) }}</strong><span>{{ learningResourceType(resource.resource_type) }} · {{ resource.estimated_minutes || 10 }} 分钟</span></div><n-button text @click="router.push({ name: 'resources', query: { resource: resource.resource_id } })">打开</n-button></article></section><n-empty v-else description="还没有学习资源"><template #extra><n-button secondary @click="freeModal = true">自定义生成学习资料</n-button></template></n-empty></n-tab-pane>
        <n-tab-pane name="record" tab="学习记录"><section v-if="tasks.some(task => task.status === 'completed')" class="record-list surface"><article v-for="task in tasks.filter(task => task.status === 'completed').slice(0, 5)" :key="task.task_id"><CheckCircle2 :size="18" /><div><strong>{{ learningText(task.title) }}</strong><span>{{ formatDate(task.latest_attempt?.submitted_at) }} · 得分 {{ task.latest_attempt?.raw_score ?? '--' }}/{{ task.question_count || '--' }} · 正确率 {{ task.latest_attempt?.accuracy == null ? '--' : `${Math.round(task.latest_attempt.accuracy * 100)}%` }}</span></div><n-button text :disabled="!task.latest_attempt?.attempt_id" @click="router.push({ name: 'learning-tasks', query: { attempt: task.latest_attempt?.attempt_id } })">查看结果</n-button></article></section><n-empty v-else description="还没有学习记录"><template #extra><n-button type="primary" @click="nextAction.action">开始今日学习</n-button></template></n-empty></n-tab-pane>
      </n-tabs>
      <section v-if="weakPoints.length" class="weak-strip"><span>当前重点：</span><n-tag v-for="item in weakPoints" :key="`${item.dimension_code}-${item.knowledge_point}`" type="warning" :bordered="false">{{ learningDimension(item.dimension_code) }} · {{ item.knowledge_point }}</n-tag></section>
    </n-spin>
  </div>
  <n-modal v-model:show="freeModal" preset="card" title="自定义生成学习资料" :style="{ width: 'min(460px, calc(100vw - 32px))' }"><p>输入想学习的主题，系统会生成基础学习资料，不会关联或复用旧任务。</p><n-input v-model:value="freeTopic" placeholder="例如：黄芪与甘草的性状区别" @keyup.enter="generateFreeResource" /><template #footer><n-space justify="end"><n-button @click="freeModal = false">取消</n-button><n-button type="primary" :loading="freeGenerating" @click="generateFreeResource">生成资料</n-button></n-space></template></n-modal>
  <n-modal v-model:show="showGuide" preset="card" title="欢迎使用本草智策学习中心" :style="{ width: 'min(480px, calc(100vw - 32px))' }">
    <p>你可以按以下步骤开始学习：</p><ol><li>查看今日学习任务</li><li>完成练习</li><li>根据结果查看讲解和学习资源</li></ol>
    <template #footer><n-space justify="end"><n-button @click="dismissGuide">我知道了</n-button><n-button type="primary" @click="dismissGuide(); activeTab = 'today'">开始今日学习</n-button></n-space></template>
  </n-modal>
</template>

<style scoped>
.center-alert { margin-bottom: 16px; }.onboarding-card,.next-step,.job-card,.today-task,.plan-overview,.resource-list,.record-list { margin-bottom: 18px; padding: 22px; }.onboarding-card,.next-step,.job-card { display:flex; align-items:center; justify-content:space-between; gap:24px; }.onboarding-card h2,.next-step h2,.today-task h2 { margin:5px 0 9px; color:var(--ink); }.onboarding-card p,.next-step p,.job-card p,.today-task p,.plan-overview p { color:var(--muted); font-size:13px; line-height:1.7; }.next-step { background:#173125; color:#fff; }.next-step h2 { color:#fff; }.next-step p { color:#c1d1c7; }.job-card { background:var(--surface-soft); }.center-tabs { margin-top:20px; }.today-task { display:grid; gap:12px; }.today-task > div { display:flex; gap:12px; align-items:center; color:var(--muted); font-size:12px; }.today-task > .n-button { justify-self:start; }.plan-overview article,.resource-list article,.record-list article { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:13px 0; border-top:1px solid var(--line); }.plan-overview article span,.resource-list article span { color:var(--muted); font-size:12px; }.resource-list article div { display:grid; gap:4px; }.record-list article { justify-content:flex-start; }.record-list .n-button { margin-left:auto; }.weak-strip { display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin-top:18px; color:var(--muted); font-size:12px; }@media(max-width:760px){.onboarding-card,.next-step,.job-card{align-items:stretch;flex-direction:column}.next-step .n-button{width:100%}}
</style>
