<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CheckCircle2, Play, RefreshCw } from 'lucide-vue-next'
import { NAlert, NButton, NCheckbox, NCheckboxGroup, NEmpty, NRadio, NRadioGroup, NSpace, NSpin, NTag, useMessage } from 'naive-ui'
import { api } from '../services/api'
import type { LearnerDimension, LearningPlan, LearningTask, LearningTaskAttempt, LearningTaskResult, ResourceItem } from '../types/api'
import { useAuthStore } from '../stores/auth'
import PageHeader from '../components/PageHeader.vue'
import { getErrorMessage } from '../utils/format'
import { learningDifficulty, learningDimension, learningPlanStage, learningResourceType, learningTaskStatus, learningText } from '../utils/learningDisplay'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const message = useMessage()
const loading = ref(true)
const refreshing = ref(false)
const errorText = ref('')
const tasks = ref<LearningTask[]>([])
const dimensions = ref<LearnerDimension[]>([])
const resources = ref<ResourceItem[]>([])
const attempt = ref<LearningTaskAttempt | null>(null)
const selectedTask = ref<LearningTask | null>(null)
const answers = ref<Record<number, string | string[]>>({})
const result = ref<LearningTaskResult | null>(null)
const submitting = ref(false)
const plan = ref<LearningPlan | null>(null)
const generatingPlan = ref(false)
const generatingResource = ref<string | null>(null)
const resourceRetry = ref<(() => Promise<void>) | null>(null)

const pending = computed(() => tasks.value.filter(item => item.status === 'pending'))
const active = computed(() => tasks.value.filter(item => item.status === 'in_progress'))
const complete = computed(() => tasks.value.filter(item => item.status === 'completed'))
const questions = computed(() => attempt.value?.questions || [])
const planCompleted = computed(() => plan.value?.items.filter(item => taskForPlanItem(item.linked_task_id)?.status === 'completed').length || 0)
const incorrectQuestionIds = computed(() => result.value?.question_results.filter(item => !item.is_correct).map(item => item.question_id) || [])

async function load(showFeedback = false): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const [taskPage, profileDimensions, currentPlan, resourcePage] = await Promise.all([
      api.listLearningTasks(auth.learnerId), api.getDimensions(auth.learnerId), api.getCurrentLearningPlan(auth.learnerId), api.listResources(auth.learnerId),
    ])
    tasks.value = taskPage.items
    dimensions.value = profileDimensions
    plan.value = currentPlan
    resources.value = resourcePage.items
    if (showFeedback) message.success(tasks.value.some(task => task.status === 'pending' || task.status === 'in_progress') ? '已为你更新练习内容。' : '当前没有新的可用题目。')
  } catch (error) { errorText.value = getErrorMessage(error, '学习任务加载失败，请稍后重试。') }
  finally { loading.value = false; refreshing.value = false }
}

async function refreshTasks(): Promise<void> {
  if (refreshing.value || loading.value) return
  refreshing.value = true
  await load(true)
}

async function generatePlan(): Promise<void> {
  if (generatingPlan.value) return
  generatingPlan.value = true
  errorText.value = ''
  const previousPlanId = plan.value?.plan_id
  try {
    const created = await api.generateLearningPlan(auth.learnerId, 30)
    await load()
    message.success(created.plan_id === previousPlanId ? '当前学习情况没有明显变化，现有计划仍然适合你。' : '学习计划已更新，今日任务已重新安排。')
  } catch (error) { errorText.value = getErrorMessage(error, '学习计划生成失败，请稍后重试。') }
  finally { generatingPlan.value = false }
}

function taskForPlanItem(taskId: string | null): LearningTask | undefined { return tasks.value.find(task => task.task_id === taskId) }

async function start(task: LearningTask): Promise<void> {
  errorText.value = ''; result.value = null
  try { attempt.value = await api.startLearningTask(task.task_id, auth.learnerId); selectedTask.value = task; answers.value = {}; await load() }
  catch (error) { errorText.value = getErrorMessage(error, '无法开始学习任务，请稍后重试。') }
}

async function openResource(resource: ResourceItem): Promise<void> { await router.push({ name: 'resources', query: { resource: resource.resource_id } }) }

async function generateTaskResource(task: LearningTask, resourceType = 'practice_guide', planItemId?: string, wrongQuestionIds: number[] = []): Promise<void> {
  const key = `${task.task_id}:${resourceType}`
  if (generatingResource.value) return
  const existing = resources.value.find(resource => resource.task_id === task.task_id && resource.resource_type === resourceType)
  if (existing) { await openResource(existing); return }
  generatingResource.value = key; errorText.value = ''; resourceRetry.value = null
  try {
    const job = await api.createResourceGenerationJob({
      learner_id: auth.learnerId, learning_plan_item_id: planItemId, task_id: task.task_id, resource_type: resourceType, difficulty: task.difficulty,
      additional_instruction: wrongQuestionIds.length ? `请重点讲解本次作答错误的题目：${wrongQuestionIds.join('、')}。` : undefined,
    })
    await load()
    if (job.resource_id) {
      const resource = resources.value.find(item => item.resource_id === job.resource_id)
      message.success(resourceType === 'error_explanation' ? '错题讲解已准备完成。' : '任务讲解已准备完成。')
      if (resource) await openResource(resource)
    } else message.info('讲解正在准备中，完成后会出现在学习资源中。')
  } catch (error) {
    errorText.value = getErrorMessage(error, '讲解准备失败，请稍后重试。')
    resourceRetry.value = () => generateTaskResource(task, resourceType, planItemId, wrongQuestionIds)
  } finally { generatingResource.value = null }
}

async function openResult(task: LearningTask): Promise<void> {
  errorText.value = ''
  try {
    result.value = task.latest_attempt?.attempt_id
      ? await api.getLearningAttemptResult(task.latest_attempt.attempt_id, auth.learnerId)
      : await api.getLearningTaskResult(task.task_id, auth.learnerId)
    selectedTask.value = task; attempt.value = null
  } catch (error) { errorText.value = getErrorMessage(error, '无法读取这次练习结果，请稍后重试。') }
}

async function submit(): Promise<void> {
  if (!attempt.value || !selectedTask.value || questions.value.some(question => !answers.value[question.question_id]) || submitting.value) return
  submitting.value = true; errorText.value = ''
  try {
    result.value = await api.submitLearningTask(selectedTask.value.task_id, auth.learnerId, attempt.value.attempt_id, questions.value.map(question => ({ question_id: question.question_id, answer: answers.value[question.question_id] })))
    attempt.value = null; await load(); message.success('任务已由服务端判分，学习画像已更新。')
  } catch (error) { errorText.value = getErrorMessage(error, '任务提交失败，请稍后重试。') }
  finally { submitting.value = false }
}

function leaveWorkspace(): void { attempt.value = null; result.value = null; selectedTask.value = null; resourceRetry.value = null }
onMounted(async () => {
  await load()
  const attemptId = typeof route.query.attempt === 'string' ? route.query.attempt : ''
  const task = tasks.value.find(item => item.latest_attempt?.attempt_id === attemptId)
  if (task) await openResult(task)
})
</script>

<template>
  <div class="page learning-tasks-page">
    <PageHeader title="学习任务" eyebrow="个性化学习" meta="完成练习后，系统会更新你的学习画像">
      <template #actions><n-button secondary :loading="refreshing || loading" @click="refreshTasks"><template #icon><RefreshCw :size="17" /></template>刷新任务</n-button></template>
    </PageHeader>
    <n-alert v-if="errorText" type="warning" closable class="task-alert" @close="errorText = ''"><p>{{ errorText }}</p><n-button v-if="resourceRetry" size="small" @click="resourceRetry?.()">重试</n-button></n-alert>
    <n-spin :show="loading">
      <section v-if="attempt" class="surface workspace"><header><div><span>进行中的任务</span><h2>{{ learningText(selectedTask?.title) }}</h2></div><n-space><n-button secondary size="small" :loading="generatingResource === `${selectedTask?.task_id}:practice_guide`" @click="selectedTask && generateTaskResource(selectedTask)">{{ generatingResource ? '正在准备讲解' : '生成任务讲解' }}</n-button><n-button text @click="leaveWorkspace">返回列表</n-button></n-space></header><article v-for="(question, index) in questions" :key="question.question_id" class="question"><small>第 {{ index + 1 }} 题 · {{ learningDimension(question.dimension_code) }}</small><h3>{{ question.stem }}</h3><n-checkbox-group v-if="question.question_type === 'multiple_choice'" v-model:value="answers[question.question_id] as string[]"><n-space vertical><n-checkbox v-for="option in question.options" :key="option.key" :value="option.key">{{ option.key }}. {{ option.text }}</n-checkbox></n-space></n-checkbox-group><n-radio-group v-else v-model:value="answers[question.question_id] as string"><n-space vertical><n-radio v-for="option in question.options" :key="option.key" :value="option.key">{{ option.key }}. {{ option.text }}</n-radio></n-space></n-radio-group></article><n-button type="primary" block :loading="submitting" :disabled="questions.some(question => !answers[question.question_id])" @click="submit">提交答案</n-button></section>
      <section v-else-if="result" class="surface workspace"><header><div><span>本次练习结果</span><h2>得分 {{ result.final_score }} · 正确率 {{ Math.round(result.accuracy * 100) }}%</h2></div><n-button text @click="leaveWorkspace">返回列表</n-button></header><article v-for="item in result.question_results" :key="item.question_id" class="result-row" :class="{ correct: item.is_correct }"><CheckCircle2 :size="18" /><div><strong>{{ item.is_correct ? '回答正确' : '需要巩固' }}</strong><p>你的答案：{{ Array.isArray(item.student_answer) ? item.student_answer.join('、') : item.student_answer || '未作答' }} · 正确答案：{{ Array.isArray(item.correct_answer) ? item.correct_answer.join('、') : item.correct_answer }}</p><p>{{ item.explanation }}</p></div></article><n-alert v-if="incorrectQuestionIds.length" type="warning" :bordered="false"><n-space justify="space-between" align="center"><span>本次有 {{ incorrectQuestionIds.length }} 道题需要巩固。</span><n-button size="small" :loading="generatingResource === `${selectedTask?.task_id}:error_explanation`" @click="selectedTask && generateTaskResource(selectedTask, 'error_explanation', undefined, incorrectQuestionIds)">生成 {{ incorrectQuestionIds.length }} 道错题讲解</n-button></n-space></n-alert><n-alert v-else type="success" :bordered="false">本次练习全部答对，无需生成错题讲解。</n-alert></section>
      <template v-else><section class="surface plan-card"><header class="plan-header"><div><span>当前个性化学习计划</span><h2>{{ learningPlanStage(plan?.stage) }}</h2></div><n-button type="primary" :loading="generatingPlan" @click="generatePlan">{{ plan ? '重新生成计划' : '生成学习计划' }}</n-button></header><template v-if="plan"><p class="plan-goal"><strong>学习目标：</strong>{{ learningText(plan.goal) }}</p><p class="plan-summary">{{ learningText(plan.summary) }}</p><div class="plan-meta"><span>预计总时长 {{ plan.total_estimated_minutes }} 分钟</span><span>已完成 {{ planCompleted }}/{{ plan.items.length }} 项</span></div><article v-for="item in plan.items" :key="item.item_id" class="plan-item"><div><h3>{{ learningText(item.title) }}</h3><p>{{ learningText(item.reason) }}</p><small>{{ item.target_dimensions.map(learningDimension).join('、') }} · {{ learningDifficulty(item.difficulty) }} · {{ item.estimated_minutes }} 分钟 · {{ learningTaskStatus(taskForPlanItem(item.linked_task_id)?.status || item.status) }}</small></div><n-space vertical size="small"><n-button v-if="item.linked_task_id && taskForPlanItem(item.linked_task_id)" size="small" type="primary" @click="taskForPlanItem(item.linked_task_id)?.status === 'completed' ? openResult(taskForPlanItem(item.linked_task_id)!) : start(taskForPlanItem(item.linked_task_id)!)">{{ taskForPlanItem(item.linked_task_id)?.status === 'completed' ? '查看结果' : taskForPlanItem(item.linked_task_id)?.status === 'in_progress' ? '继续学习' : '开始学习' }}</n-button><n-button v-else size="small" secondary :loading="generatingPlan" @click="generatePlan">生成练习</n-button><n-button v-if="item.linked_task_id && taskForPlanItem(item.linked_task_id)" size="small" secondary :loading="generatingResource === `${item.linked_task_id}:${item.resource_type}`" @click="generateTaskResource(taskForPlanItem(item.linked_task_id)!, item.resource_type === 'none' ? 'practice_guide' : item.resource_type, item.item_id)">生成{{ learningResourceType(item.resource_type === 'none' ? 'practice_guide' : item.resource_type) }}</n-button></n-space></article></template><n-empty v-else size="small" description="完成基础测评后，系统会为你安排学习计划。" /></section><section v-for="group in [{ title: '待开始任务', items: pending }, { title: '进行中任务', items: active }, { title: '已完成任务', items: complete }]" :key="group.title" class="task-section"><h2>{{ group.title }}</h2><div v-if="group.items.length" class="task-grid"><article v-for="task in group.items" :key="task.task_id" class="surface task-card"><n-tag size="small" :bordered="false">{{ learningTaskStatus(task.status) }}</n-tag><h3>{{ learningText(task.title) }}</h3><p>{{ task.target_dimensions.map(learningDimension).join(' · ') }}</p><small>{{ task.question_count || 0 }} 题 · {{ learningDifficulty(task.difficulty) }} · 约 {{ task.estimated_minutes || 10 }} 分钟</small><n-button v-if="task.status === 'completed'" secondary block @click="openResult(task)">查看结果</n-button><n-button v-else type="primary" block @click="start(task)"><template #icon><Play :size="16" /></template>{{ task.status === 'in_progress' ? '继续学习' : '开始学习' }}</n-button><n-button secondary block :loading="generatingResource === `${task.task_id}:${task.status === 'completed' ? 'error_explanation' : 'practice_guide'}`" :disabled="task.status === 'completed' && task.latest_attempt?.wrong_count === 0" @click="generateTaskResource(task, task.status === 'completed' ? 'error_explanation' : 'practice_guide')">{{ task.status === 'completed' && task.latest_attempt?.wrong_count === 0 ? '无需错题讲解' : task.status === 'completed' ? '生成错题讲解' : '生成任务讲解' }}</n-button><small v-if="task.status === 'completed' && task.latest_attempt?.wrong_count === 0">本次练习全部答对，无需生成错题讲解。</small></article></div><n-empty v-else size="small" description="暂无任务" /></section></template>
    </n-spin>
  </div>
</template>

<style scoped>
.task-alert{margin-bottom:16px}.plan-card{display:grid;gap:12px;padding:20px;margin-bottom:22px}.plan-header,.plan-item,.workspace>header{display:flex;align-items:center;justify-content:space-between;gap:12px}.plan-header h2,.workspace h2,.workspace h3{color:var(--ink);margin:4px 0}.plan-header span,.plan-summary,.plan-item p,.plan-item small,.task-card p,.task-card small,.workspace header span,.question small{color:var(--muted);font-size:12px}.plan-summary,.plan-item p{line-height:1.7}.plan-meta{display:flex;gap:16px;color:var(--primary);font-size:12px}.plan-item{padding-top:12px;border-top:1px solid var(--line)}.plan-item h3,.task-card h3{margin:0;color:var(--ink);font-size:15px}.task-section{margin:24px 0}.task-section h2{color:var(--ink);font-size:18px}.task-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}.task-card{display:grid;gap:12px;padding:18px}.workspace{padding:20px}.question{padding:18px 0;border-top:1px solid var(--line)}.question h3{margin:8px 0 14px;color:var(--ink);font-size:15px;line-height:1.7}.result-row{display:flex;gap:10px;padding:13px;color:#8a5c20;background:var(--amber-soft)}.result-row.correct{color:var(--primary-strong);background:var(--primary-soft)}.result-row p{margin:5px 0;color:var(--muted);font-size:12px}
</style>
