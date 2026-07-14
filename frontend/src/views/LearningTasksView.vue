<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CheckCircle2, Play, RefreshCw } from 'lucide-vue-next'
import {
  NAlert,
  NButton,
  NCheckbox,
  NCheckboxGroup,
  NEmpty,
  NRadio,
  NRadioGroup,
  NSpace,
  NSpin,
  useMessage,
} from 'naive-ui'
import { api } from '../services/api'
import type { LearnerDimension, LearningPlan, LearningTask, LearningTaskAttempt, LearningTaskResult } from '../types/api'
import { useAuthStore } from '../stores/auth'
import PageHeader from '../components/PageHeader.vue'
import { dimensionLabels, getErrorMessage } from '../utils/format'

const auth = useAuthStore()
const message = useMessage()
const loading = ref(true)
const errorText = ref('')
const tasks = ref<LearningTask[]>([])
const dimensions = ref<LearnerDimension[]>([])
const attempt = ref<LearningTaskAttempt | null>(null)
const selectedTask = ref<LearningTask | null>(null)
const answers = ref<Record<number, string | string[]>>({})
const result = ref<LearningTaskResult | null>(null)
const submitting = ref(false)
const plan = ref<LearningPlan | null>(null)
const generatingPlan = ref(false)

const pending = computed(() => tasks.value.filter(item => item.status === 'pending'))
const active = computed(() => tasks.value.filter(item => item.status === 'in_progress'))
const complete = computed(() => tasks.value.filter(item => item.status === 'completed'))
const questions = computed(() => attempt.value?.questions || [])
const planCompleted = computed(() => plan.value?.items.filter(item => item.status === 'completed').length || 0)

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const [taskPage, profileDimensions, currentPlan] = await Promise.all([
      api.listLearningTasks(auth.learnerId),
      api.getDimensions(auth.learnerId),
      api.getCurrentLearningPlan(auth.learnerId),
    ])
    tasks.value = taskPage.items
    dimensions.value = profileDimensions
    plan.value = currentPlan
  } catch (error) {
    errorText.value = getErrorMessage(error, '学习任务加载失败')
  } finally {
    loading.value = false
  }
}

async function generatePlan(): Promise<void> {
  generatingPlan.value = true
  errorText.value = ''
  try {
    plan.value = await api.generateLearningPlan(auth.learnerId, 30)
    await load()
    message.success('个性化学习计划已生成')
  } catch (error) {
    errorText.value = getErrorMessage(error, '学习计划生成失败')
  } finally {
    generatingPlan.value = false
  }
}

function taskForPlanItem(taskId: string | null): LearningTask | undefined {
  return tasks.value.find(task => task.task_id === taskId)
}

async function start(task: LearningTask): Promise<void> {
  errorText.value = ''
  result.value = null
  try {
    attempt.value = await api.startLearningTask(task.task_id, auth.learnerId)
    selectedTask.value = task
    answers.value = {}
    await load()
  } catch (error) {
    errorText.value = getErrorMessage(error, '无法开始学习任务')
  }
}

async function openResult(task: LearningTask): Promise<void> {
  errorText.value = ''
  try {
    result.value = await api.getLearningTaskResult(task.task_id, auth.learnerId)
    selectedTask.value = task
    attempt.value = null
  } catch (error) {
    errorText.value = getErrorMessage(error, '无法读取任务结果')
  }
}

async function submit(): Promise<void> {
  if (!attempt.value || !selectedTask.value || questions.value.some(question => !answers.value[question.question_id])) return
  submitting.value = true
  errorText.value = ''
  try {
    result.value = await api.submitLearningTask(
      selectedTask.value.task_id,
      auth.learnerId,
      attempt.value.attempt_id,
      questions.value.map(question => ({ question_id: question.question_id, answer: answers.value[question.question_id] })),
    )
    attempt.value = null
    await load()
    message.success('任务已由服务端判分，学习画像已更新')
  } catch (error) {
    errorText.value = getErrorMessage(error, '任务提交失败')
  } finally {
    submitting.value = false
  }
}

function leaveWorkspace(): void {
  attempt.value = null
  result.value = null
  selectedTask.value = null
}

onMounted(load)
</script>

<template>
  <div class="page learning-tasks-page">
    <PageHeader title="学习任务" eyebrow="个性化学习" meta="服务端判分与画像闭环">
      <template #actions>
        <n-button secondary :loading="loading" @click="load"><template #icon><RefreshCw :size="17" /></template>刷新任务</n-button>
      </template>
    </PageHeader>

    <n-alert v-if="errorText" type="warning" closable class="task-alert" @close="errorText = ''">{{ errorText }}</n-alert>
    <n-spin :show="loading">
      <section v-if="attempt" class="surface workspace">
        <header><div><span>进行中的任务</span><h2>{{ selectedTask?.title }}</h2></div><n-button text @click="leaveWorkspace">返回列表</n-button></header>
        <article v-for="(question, index) in questions" :key="question.question_id" class="question">
          <small>第 {{ index + 1 }} 题 · {{ dimensionLabels[question.dimension_code] || question.dimension_code }}</small>
          <h3>{{ question.stem }}</h3>
          <n-checkbox-group v-if="question.question_type === 'multiple_choice'" v-model:value="answers[question.question_id] as string[]">
            <n-space vertical><n-checkbox v-for="option in question.options" :key="option.key" :value="option.key">{{ option.key }}. {{ option.text }}</n-checkbox></n-space>
          </n-checkbox-group>
          <n-radio-group v-else v-model:value="answers[question.question_id] as string">
            <n-space vertical><n-radio v-for="option in question.options" :key="option.key" :value="option.key">{{ option.key }}. {{ option.text }}</n-radio></n-space>
          </n-radio-group>
        </article>
        <n-button type="primary" block :loading="submitting" :disabled="questions.some(question => !answers[question.question_id])" @click="submit">确认提交，由服务端判分</n-button>
      </section>

      <section v-else-if="result" class="surface workspace">
        <header><div><span>已完成任务</span><h2>得分 {{ result.final_score }} · 正确率 {{ Math.round(result.accuracy * 100) }}%</h2></div><n-button text @click="leaveWorkspace">返回列表</n-button></header>
        <article v-for="item in result.question_results" :key="item.question_id" class="result-row" :class="{ correct: item.is_correct }">
          <CheckCircle2 :size="18" /><div><strong>{{ item.is_correct ? '回答正确' : '需要巩固' }}</strong><p>{{ item.explanation }}</p></div>
        </article>
        <div class="changes"><h3>六维能力变化</h3><p v-for="change in result.dimension_changes" :key="change.dimension_code">{{ dimensionLabels[change.dimension_code] || change.dimension_code }}：{{ change.before }} → {{ change.after }}（{{ change.delta >= 0 ? '+' : '' }}{{ change.delta }}）</p></div>
        <n-alert v-if="result.next_task" type="success" :bordered="false">下一任务已推荐：{{ result.next_task.title }}（{{ result.next_task.difficulty }}）</n-alert>
      </section>

      <template v-else>
        <section class="surface plan-card">
          <header class="plan-header"><div><span>今日个性化学习计划</span><h2>{{ plan?.stage || '尚未生成计划' }}</h2></div><n-button type="primary" :loading="generatingPlan" @click="generatePlan">{{ plan ? '重新生成计划' : '生成计划' }}</n-button></header>
          <template v-if="plan">
            <p class="plan-goal"><strong>今日目标：</strong>{{ plan.goal }}</p>
            <p class="plan-summary">{{ plan.summary }}</p>
            <div class="plan-meta"><span>预计总时长 {{ plan.total_estimated_minutes }} 分钟</span><span>完成进度 {{ planCompleted }}/{{ plan.items.length }}</span></div>
            <article v-for="item in plan.items" :key="item.item_id" class="plan-item">
              <div><h3>{{ item.title }}</h3><p>{{ item.reason }}</p><small>目标维度：{{ item.target_dimensions.map(code => dimensionLabels[code] || code).join('、') }} · 知识点：{{ item.target_knowledge_points.join('、') }} · {{ item.difficulty }} · {{ item.estimated_minutes }} 分钟 · {{ item.status }}</small></div>
              <n-button v-if="item.linked_task_id && taskForPlanItem(item.linked_task_id)" size="small" type="primary" @click="taskForPlanItem(item.linked_task_id)?.status === 'completed' ? openResult(taskForPlanItem(item.linked_task_id)!) : start(taskForPlanItem(item.linked_task_id)!)">{{ taskForPlanItem(item.linked_task_id)?.status === 'completed' ? '查看结果' : taskForPlanItem(item.linked_task_id)?.status === 'in_progress' ? '继续任务' : '开始任务' }}</n-button>
              <span v-else class="empty-task">当前题库暂无对应任务</span>
            </article>
          </template>
          <n-empty v-else size="small" description="根据画像、薄弱点和近期任务生成今日计划" />
        </section>
        <section class="dimension-band"><div v-for="dimension in dimensions" :key="dimension.dimension_code"><span>{{ dimensionLabels[dimension.dimension_code] || dimension.dimension_code }}</span><strong>{{ dimension.score }}</strong></div></section>
        <section v-for="group in [{ title: '待完成任务', items: pending }, { title: '进行中任务', items: active }, { title: '已完成任务', items: complete }]" :key="group.title" class="task-section">
          <h2>{{ group.title }}</h2>
          <div v-if="group.items.length" class="task-grid"><article v-for="task in group.items" :key="task.task_id" class="surface task-card"><span>{{ task.source }}</span><h3>{{ task.title }}</h3><p>{{ task.target_dimensions.map(code => dimensionLabels[code] || code).join(' · ') }}</p><small>{{ task.question_count || 0 }} 题 · {{ task.difficulty }} · {{ task.estimated_minutes || '-' }} 分钟</small><n-button v-if="task.status === 'completed'" secondary block @click="openResult(task)">查看结果</n-button><n-button v-else type="primary" block @click="start(task)"><template #icon><Play :size="16" /></template>{{ task.status === 'in_progress' ? '继续任务' : '开始任务' }}</n-button></article></div>
          <n-empty v-else size="small" description="暂无任务" />
        </section>
      </template>
    </n-spin>
  </div>
</template>

<style scoped>
.task-alert { margin-bottom: 16px; }
.plan-card { display: grid; gap: 12px; padding: 20px; margin-bottom: 22px; }.plan-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }.plan-header span, .plan-summary, .plan-item p, .plan-item small { color: var(--muted); font-size: 12px; }.plan-header h2 { color: var(--ink); margin-top: 4px; font-size: 18px; }.plan-goal { color: var(--ink); }.plan-summary { line-height: 1.7; }.plan-meta { display: flex; gap: 16px; color: var(--primary); font-size: 12px; }.plan-item { display: flex; align-items: center; justify-content: space-between; gap: 12px; border-top: 1px solid var(--line); padding-top: 12px; }.plan-item h3 { color: var(--ink); font-size: 14px; }.plan-item p { margin: 5px 0; }.empty-task { color: var(--muted); font-size: 12px; white-space: nowrap; }
.dimension-band { display: grid; grid-template-columns: repeat(6, 1fr); gap: 1px; margin-bottom: 22px; background: var(--line); }
.dimension-band div { display: grid; gap: 6px; padding: 14px; background: var(--surface); }.dimension-band span { color: var(--muted); font-size: 11px; }.dimension-band strong { color: var(--primary); font-size: 20px; }
.task-section { margin: 24px 0; }.task-section h2 { margin-bottom: 12px; color: var(--ink); font-size: 18px; }.task-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; }.task-card { display: grid; gap: 12px; padding: 18px; }.task-card > span { color: var(--primary); font-size: 11px; }.task-card h3 { color: var(--ink); font-size: 15px; }.task-card p, .task-card small { color: var(--muted); font-size: 12px; }
.workspace { padding: 20px; }.workspace > header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }.workspace header span, .question small { color: var(--muted); font-size: 11px; }.workspace h2, .workspace h3 { color: var(--ink); }.question { padding: 18px 0; border-top: 1px solid var(--line); }.question h3 { margin: 8px 0 14px; font-size: 15px; line-height: 1.7; }.result-row { display: flex; gap: 10px; padding: 13px; color: #8a5c20; background: var(--amber-soft); }.result-row.correct { color: var(--primary-strong); background: var(--primary-soft); }.result-row p { margin-top: 5px; color: var(--muted); font-size: 12px; }.changes { margin: 18px 0; padding: 15px; background: var(--surface-soft); }.changes p { margin-top: 8px; color: var(--muted); font-size: 12px; }
@media (max-width: 760px) { .dimension-band { grid-template-columns: repeat(2, 1fr); } }
</style>
