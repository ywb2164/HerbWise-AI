<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NAlert, NButton, NProgress, NSpin, NTag } from 'naive-ui'
import {
  ArrowRight,
  BookOpenText,
  ChartNoAxesCombined,
  ClipboardCheck,
  FileChartColumn,
  FlaskConical,
  Gauge,
  LibraryBig,
  ScanSearch,
  Sparkles,
  Target,
  UserRoundSearch,
} from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { DiagnosisResult, LearnerDimension, LearnerProfile, LearningPath, ResourceItem } from '../types/api'
import { dimensionLabels, formatRecommendation, getErrorMessage, levelLabels, taskTypeLabels } from '../utils/format'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const errorText = ref('')
const profile = ref<LearnerProfile | null>(null)
const dimensions = ref<LearnerDimension[]>([])
const diagnosis = ref<DiagnosisResult | null>(null)
const path = ref<LearningPath | null>(null)
const resources = ref<ResourceItem[]>([])

const groups = [
  {
    code: 'prepare',
    title: '学习准备',
    subtitle: '画像与能力诊断',
    tone: 'green',
    icon: UserRoundSearch,
    items: [
      { label: '构建学习画像', path: '/onboarding', icon: ChartNoAxesCombined },
      { label: '查看能力诊断', path: '/diagnosis', icon: ClipboardCheck },
      { label: '画像档案', path: '/profile', icon: Target },
    ],
  },
  {
    code: 'practice',
    title: '视觉实训',
    subtitle: '饮片识别与仿真任务',
    tone: 'amber',
    icon: ScanSearch,
    items: [
      { label: '图片与摄像头识别', path: '/recognition', icon: ScanSearch },
      { label: '虚拟仿真实训', path: '/simulation', icon: FlaskConical },
    ],
  },
  {
    code: 'learn',
    title: '个性化学习',
    subtitle: '知识、资源与动态任务',
    tone: 'blue',
    icon: Sparkles,
    items: [
      { label: '药材知识库', path: '/knowledge', icon: LibraryBig },
      { label: '学习资源', path: '/resources', icon: BookOpenText },
      { label: '学习任务', path: '/learning-tasks', icon: ClipboardCheck },
    ],
  },
  {
    code: 'result',
    title: '结果沉淀',
    subtitle: '报告、证据与指标',
    tone: 'dark',
    icon: FileChartColumn,
    items: [
      { label: '学习报告', path: '/reports', icon: FileChartColumn },
      { label: '证据链', path: '/traces', icon: FlaskConical },
      { label: '测试指标', path: '/metrics', icon: Gauge },
    ],
  },
]

const averageScore = computed(() => {
  if (!dimensions.value.length) return 0
  return Math.round(dimensions.value.reduce((sum, item) => sum + item.score, 0) / dimensions.value.length)
})
const weakestDimension = computed(() => [...dimensions.value].sort((a, b) => a.score - b.score)[0] || null)
const nextRoute = computed(() => {
  if (!dimensions.value.length) return '/onboarding'
  if (!localStorage.getItem('herbwise.last_task_id')) return '/recognition'
  return '/learning-tasks'
})
const nextTaskTitle = computed(() => {
  if (!dimensions.value.length) return '完成学习画像与理论测试'
  if (!localStorage.getItem('herbwise.last_task_id')) return '完成一次饮片识别实训'
  return formatRecommendation(diagnosis.value?.recommended_next_task)
})
const journey = computed(() => [
  { label: '画像建立', done: Boolean(profile.value) },
  { label: '能力诊断', done: dimensions.value.length > 0 },
  { label: '视觉实训', done: Boolean(localStorage.getItem('herbwise.last_task_id')) },
  { label: '资源学习', done: resources.value.length > 0 },
])

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  const results = await Promise.allSettled([
    api.getProfile(auth.learnerId),
    api.getDimensions(auth.learnerId),
    api.diagnoseProfile(auth.learnerId),
    api.getLearningPath(auth.learnerId),
    api.listResources(auth.learnerId, 6),
  ])
  if (results[0].status === 'fulfilled') profile.value = results[0].value
  if (results[1].status === 'fulfilled') dimensions.value = results[1].value
  if (results[2].status === 'fulfilled') diagnosis.value = results[2].value
  if (results[3].status === 'fulfilled') path.value = results[3].value
  if (results[4].status === 'fulfilled') resources.value = results[4].value.items
  const failed = results.find(result => result.status === 'rejected')
  if (failed?.status === 'rejected') errorText.value = getErrorMessage(failed.reason, '部分工作台数据加载失败')
  loading.value = false
}

onMounted(load)
</script>

<template>
  <div class="page hub-page">
    <PageHeader title="学习工作台" :meta="profile?.name || auth.learnerId">
      <template #actions>
        <n-button secondary @click="router.push('/diagnosis')">查看诊断</n-button>
        <n-button type="primary" @click="router.push(nextRoute)">
          继续学习
          <template #icon><ArrowRight :size="17" /></template>
        </n-button>
      </template>
    </PageHeader>

    <n-alert v-if="errorText" type="warning" :bordered="false" class="hub-alert">{{ errorText }}</n-alert>

    <n-spin :show="loading">
      <section class="next-task-band">
        <div class="next-task-copy">
          <span class="eyebrow">下一步任务</span>
          <h2>{{ nextTaskTitle }}</h2>
          <div class="next-task-meta">
            <n-tag size="small" :bordered="false" type="success">
              {{ levelLabels[diagnosis?.overall_level || profile?.overall_level || 'weak'] }}
            </n-tag>
            <span v-if="weakestDimension">重点：{{ dimensionLabels[weakestDimension.dimension_code] }}</span>
            <span>六维均分：{{ averageScore }}</span>
          </div>
        </div>
        <div class="next-task-stage">
          <span>当前路径</span>
          <strong>{{ levelLabels[path?.current_stage || 'foundation'] || path?.current_stage || '基础巩固' }}</strong>
          <small>
            {{ (path?.path.recommended_task_types || ['lecture', 'quiz']).map(type => taskTypeLabels[type] || type).join(' · ') }}
          </small>
        </div>
        <n-button type="primary" size="large" @click="router.push(nextRoute)">
          开始
          <template #icon><ArrowRight :size="18" /></template>
        </n-button>
      </section>

      <section class="journey-strip" aria-label="学习闭环进度">
        <div v-for="(item, index) in journey" :key="item.label" :class="{ done: item.done }">
          <span>{{ index + 1 }}</span>
          <strong>{{ item.label }}</strong>
          <small>{{ item.done ? '已完成' : '待完成' }}</small>
        </div>
      </section>

      <section class="function-groups">
        <article v-for="group in groups" :key="group.code" class="function-group" :class="group.tone">
          <header>
            <div class="group-icon"><component :is="group.icon" :size="22" /></div>
            <div><span>{{ group.subtitle }}</span><h2>{{ group.title }}</h2></div>
          </header>
          <nav :aria-label="group.title">
            <button v-for="item in group.items" :key="item.path" type="button" @click="router.push(item.path)">
              <component :is="item.icon" :size="17" />
              <span>{{ item.label }}</span>
              <ArrowRight :size="15" />
            </button>
          </nav>
        </article>
      </section>

      <section class="learning-snapshot">
        <div class="snapshot-heading">
          <span class="eyebrow">能力快照</span>
          <h2>六维学习基础</h2>
          <p>最新诊断结果将随理论测试、视觉实训和学习反馈持续更新。</p>
        </div>
        <div class="snapshot-bars">
          <div v-for="item in dimensions" :key="item.dimension_code">
            <span>{{ dimensionLabels[item.dimension_code] }}</span>
            <n-progress
              type="line"
              :percentage="item.score"
              :height="7"
              :show-indicator="false"
              :color="item.score < 60 ? '#bd7a20' : '#1f6b4f'"
              rail-color="#edf1ee"
            />
            <strong>{{ Math.round(item.score) }}</strong>
          </div>
        </div>
      </section>
    </n-spin>
  </div>
</template>

<style scoped>
.hub-alert {
  margin-bottom: 16px;
}

.next-task-band {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(220px, 0.6fr) auto;
  align-items: center;
  gap: 28px;
  min-height: 152px;
  padding: 26px 28px;
  color: #fff;
  background: #17211c;
}

.next-task-copy .eyebrow {
  color: #8dc6a6;
}

.next-task-copy h2 {
  margin: 6px 0 10px;
  font-size: 22px;
  line-height: 1.45;
}

.next-task-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 14px;
  color: #bdc9c1;
  font-size: 11px;
}

.next-task-stage {
  display: grid;
  gap: 5px;
  padding-left: 24px;
  border-left: 1px solid #435048;
}

.next-task-stage span,
.next-task-stage small {
  color: #aebbb2;
  font-size: 10px;
}

.next-task-stage strong {
  color: #fff;
  font-size: 15px;
}

.journey-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-top: 16px;
  background: #fff;
  border: 1px solid var(--line);
}

.journey-strip > div {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  align-items: center;
  gap: 2px 8px;
  min-height: 72px;
  padding: 12px 16px;
  border-right: 1px solid var(--line);
}

.journey-strip > div:last-child {
  border-right: 0;
}

.journey-strip span {
  grid-row: 1 / span 2;
  display: grid;
  width: 26px;
  height: 26px;
  color: var(--muted);
  background: #edf1ee;
  border-radius: 50%;
  font-size: 10px;
  place-items: center;
}

.journey-strip strong {
  color: var(--ink);
  font-size: 12px;
}

.journey-strip small {
  color: var(--subtle);
  font-size: 9px;
}

.journey-strip .done span {
  color: #fff;
  background: var(--primary);
}

.function-groups {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.function-group {
  min-width: 0;
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.function-group > header {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 82px;
  padding: 16px;
  border-bottom: 1px solid var(--line);
}

.group-icon {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 6px;
  place-items: center;
}

.function-group.amber .group-icon {
  color: var(--amber);
  background: var(--amber-soft);
}

.function-group.blue .group-icon {
  color: var(--blue);
  background: var(--blue-soft);
}

.function-group.dark .group-icon {
  color: #fff;
  background: #38463e;
}

.function-group header > div:last-child {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.function-group header span {
  color: var(--muted);
  font-size: 9px;
}

.function-group h2 {
  color: var(--ink);
  font-size: 15px;
}

.function-group nav {
  display: grid;
}

.function-group button {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 8px;
  min-height: 48px;
  padding: 9px 14px;
  color: #435048;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--line);
  cursor: pointer;
  font-size: 11px;
  text-align: left;
}

.function-group button:last-child {
  border-bottom: 0;
}

.function-group button:hover {
  color: var(--primary-strong);
  background: var(--surface-soft);
}

.function-group button > svg:first-child {
  color: var(--muted);
}

.function-group button > svg:last-child {
  color: var(--subtle);
}

.learning-snapshot {
  display: grid;
  grid-template-columns: minmax(240px, 0.65fr) minmax(0, 1.35fr);
  align-items: center;
  gap: 28px;
  margin-top: 18px;
  padding: 24px;
  background: #fff;
  border: 1px solid var(--line);
}

.snapshot-heading h2 {
  margin: 5px 0 7px;
  color: var(--ink);
  font-size: 18px;
}

.snapshot-heading p {
  color: var(--muted);
  font-size: 11px;
  line-height: 1.7;
}

.snapshot-bars {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 13px 24px;
}

.snapshot-bars > div {
  display: grid;
  grid-template-columns: minmax(90px, auto) minmax(80px, 1fr) 30px;
  align-items: center;
  gap: 9px;
}

.snapshot-bars span {
  color: var(--muted);
  font-size: 10px;
}

.snapshot-bars strong {
  color: var(--ink);
  font-size: 10px;
  text-align: right;
}

@media (max-width: 1180px) {
  .function-groups {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .next-task-band,
  .learning-snapshot {
    grid-template-columns: 1fr;
  }

  .next-task-stage {
    padding-top: 16px;
    padding-left: 0;
    border-top: 1px solid #435048;
    border-left: 0;
  }

  .journey-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .journey-strip > div:nth-child(2) {
    border-right: 0;
  }

  .journey-strip > div:nth-child(-n + 2) {
    border-bottom: 1px solid var(--line);
  }
}

@media (max-width: 620px) {
  .function-groups,
  .snapshot-bars {
    grid-template-columns: 1fr;
  }

  .next-task-band {
    padding: 22px 18px;
  }
}
</style>
