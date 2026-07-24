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
  ShieldCheck,
  Sparkles,
  Target,
  UserRoundSearch,
} from 'lucide-vue-next'
import TcmIcon from '../components/TcmIcon.vue'
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
    illustration: 'intro',
    icon: UserRoundSearch,
    items: [
      { label: '查看学习画像', path: '/profile', icon: ChartNoAxesCombined },
      { label: '查看能力诊断', path: '/diagnosis', icon: ClipboardCheck },
      { label: '画像档案', path: '/profile', icon: Target },
    ],
  },
  {
    code: 'practice',
    title: '视觉实训',
    subtitle: '饮片识别与仿真任务',
    tone: 'amber',
    illustration: 'identify',
    icon: ScanSearch,
    items: [
      { label: '图片与摄像头锁帧', path: '/recognition', icon: ScanSearch },
      { label: '虚拟仿真实训', path: '/simulation', icon: FlaskConical },
    ],
  },
  {
    code: 'learn',
    title: '个性化学习',
    subtitle: '知识、资源与动态任务',
    tone: 'blue',
    illustration: 'study',
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
    illustration: 'archive',
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
const completedJourney = computed(() => journey.value.filter(item => item.done).length)
const trustBars = computed(() => {
  const score = Math.max(24, averageScore.value)
  return [0.7, 0.84, 0.76, 1, 0.8].map(scale => Math.max(18, Math.round(score * scale)))
})

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
    <n-alert v-if="errorText" type="warning" :bordered="false" class="hub-alert">{{ errorText }}</n-alert>

    <n-spin :show="loading">
      <section class="hero-grid">
        <article class="workbench-hero">
          <div class="hero-copy">
            <span class="hero-kicker"><Sparkles :size="14" /> HERBWISE INTELLIGENCE CONSOLE</span>
            <h1>智鉴本草统一工作台</h1>
            <p>
              以学习者画像连接中药识别、能力诊断、个性化资源与证据沉淀，
              在同一条学习路径中完成实训与成长。
            </p>
            <div class="hero-actions">
              <n-button type="primary" size="large" @click="router.push('/recognition')">
                开始鉴别
                <template #icon><ScanSearch :size="18" /></template>
              </n-button>
              <n-button secondary size="large" @click="router.push(nextRoute)">
                继续学习
                <template #icon><ArrowRight :size="18" /></template>
              </n-button>
            </div>
          </div>
          <div class="hero-task">
            <span>下一步任务</span>
            <strong>{{ nextTaskTitle }}</strong>
            <small v-if="weakestDimension">
              重点提升：{{ dimensionLabels[weakestDimension.dimension_code] }}
            </small>
          </div>
        </article>

        <aside class="trust-panel">
          <div class="trust-heading">
            <span><ShieldCheck :size="16" /> 综合能力指数</span>
            <n-tag size="small" :bordered="false" type="success">实时画像</n-tag>
          </div>
          <strong>{{ averageScore }}<small>%</small></strong>
          <p>融合画像、理论诊断、视觉实训与资源学习进度。</p>
          <div class="trust-bars" aria-hidden="true">
            <i v-for="(height, index) in trustBars" :key="index" :style="{ height: `${height}%` }" />
          </div>
        </aside>
      </section>

      <section class="metric-grid" aria-label="学习数据概览">
        <article>
          <span>能力均分</span>
          <strong>{{ averageScore }}<small>%</small></strong>
          <p>六维学习能力综合结果</p>
        </article>
        <article>
          <span>已完成环节</span>
          <strong>{{ completedJourney }}<small>/ 4</small></strong>
          <p>画像、诊断、实训与资源</p>
        </article>
        <article>
          <span>能力维度</span>
          <strong>{{ dimensions.length }}<small>项</small></strong>
          <p>持续随学习反馈更新</p>
        </article>
        <article>
          <span>推荐资源</span>
          <strong>{{ resources.length }}<small>份</small></strong>
          <p>来自当前个性化学习路径</p>
        </article>
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
            <TcmIcon :name="group.illustration" size="md" />
            <div>
              <span>{{ group.subtitle }}</span>
              <h2>{{ group.title }}</h2>
            </div>
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
          <div class="path-label">
            <span>当前路径</span>
            <strong>{{ levelLabels[path?.current_stage || 'foundation'] || path?.current_stage || '基础巩固' }}</strong>
            <small>
              {{ (path?.path.recommended_task_types || ['lecture', 'quiz']).map(type => taskTypeLabels[type] || type).join(' · ') }}
            </small>
          </div>
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
  position: relative;
  isolation: isolate;
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(220px, 0.6fr) auto;
  align-items: center;
  gap: 28px;
  min-height: 152px;
  padding: 26px 28px;
  color: #fff;
  overflow: hidden;
  background-color: var(--forest-900);
  background-image: url('/images/herbwise-page-banner.jpg');
  background-position: center;
  background-size: cover;
  border: 1px solid #1c493a;
  border-radius: 8px;
  box-shadow: 0 16px 38px rgba(10, 42, 31, 0.18);
}

.next-task-band::before {
  position: absolute;
  z-index: -1;
  inset: 0;
  content: "";
  background: rgba(7, 38, 29, 0.82);
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
  border-radius: 8px;
  box-shadow: var(--shadow-soft);
  overflow: hidden;
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
  box-shadow: var(--shadow-soft);
  transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
}

.function-group:hover {
  border-color: var(--line-strong);
  box-shadow: 0 15px 34px rgba(18, 52, 38, 0.11);
  transform: translateY(-2px);
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
  border-radius: 8px;
  box-shadow: var(--shadow-soft);
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

<style scoped>
.hub-page {
  padding-top: 24px;
}

.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 292px;
  gap: 14px;
}

.workbench-hero {
  position: relative;
  isolation: isolate;
  min-height: 270px;
  overflow: hidden;
  padding: 30px 34px;
  background-color: #f8f3e5;
  background-image: url('/images/herbwise-page-banner.jpg');
  background-position: center;
  background-size: cover;
  border: 1px solid #e2d7bd;
  border-radius: 8px;
  box-shadow: 0 16px 38px rgba(67, 70, 48, 0.1);
}

.workbench-hero::before {
  position: absolute;
  z-index: -1;
  inset: 0;
  content: "";
  background: linear-gradient(90deg, rgba(255, 252, 242, 0.96) 0%, rgba(255, 252, 242, 0.82) 48%, rgba(255, 252, 242, 0.28) 100%);
}

.hero-copy {
  max-width: 700px;
}

.hero-kicker {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 11px;
  color: #24664f;
  background: rgba(234, 242, 231, 0.86);
  border: 1px solid rgba(45, 107, 81, 0.16);
  border-radius: 999px;
  font-size: 10px;
  font-weight: 800;
}

.hero-copy h1 {
  margin-top: 14px;
  color: #184d3c;
  font-family: "Noto Serif SC", "Songti SC", SimSun, serif;
  font-size: 38px;
  font-weight: 900;
  line-height: 1.2;
}

.hero-copy > p {
  max-width: 630px;
  margin-top: 10px;
  color: #48645a;
  font-size: 13px;
  line-height: 1.8;
}

.hero-actions {
  display: flex;
  gap: 10px;
  margin-top: 22px;
}

.hero-task {
  position: absolute;
  right: 24px;
  bottom: 22px;
  display: grid;
  gap: 4px;
  width: 260px;
  padding: 13px 15px;
  background: rgba(255, 253, 245, 0.84);
  border: 1px solid rgba(183, 151, 87, 0.25);
  border-radius: 8px;
  box-shadow: 0 12px 28px rgba(83, 69, 39, 0.08);
  backdrop-filter: blur(12px);
}

.hero-task span,
.hero-task small {
  color: #68786f;
  font-size: 10px;
}

.hero-task strong {
  color: #184d3c;
  font-size: 13px;
  line-height: 1.45;
}

.trust-panel {
  display: flex;
  flex-direction: column;
  min-height: 270px;
  padding: 24px 22px 18px;
  background: #fff;
  border: 1px solid #dedfd7;
  border-radius: 8px;
  box-shadow: 0 16px 38px rgba(26, 65, 51, 0.08);
}

.trust-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.trust-heading > span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #68786f;
  font-size: 11px;
  font-weight: 700;
}

.trust-panel > strong {
  margin-top: 15px;
  color: #1a5742;
  font-family: "Noto Serif SC", "Songti SC", SimSun, serif;
  font-size: 48px;
  line-height: 1;
}

.trust-panel > strong small {
  margin-left: 2px;
  font-size: 20px;
}

.trust-panel > p {
  margin-top: 10px;
  color: #718078;
  font-size: 11px;
  line-height: 1.7;
}

.trust-bars {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  height: 72px;
  margin-top: auto;
  padding-top: 10px;
}

.trust-bars i {
  flex: 1;
  min-height: 12px;
  border-radius: 18px 18px 2px 2px;
  background: linear-gradient(180deg, #75c9aa, #0d654b);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.42);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.metric-grid article {
  min-width: 0;
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid #dedfd7;
  border-radius: 8px;
  box-shadow: 0 10px 26px rgba(26, 65, 51, 0.06);
}

.metric-grid article > span {
  display: inline-block;
  padding: 4px 8px;
  color: #2e6d56;
  background: #e8f3ed;
  border-radius: 999px;
  font-size: 9px;
  font-weight: 800;
}

.metric-grid article:nth-child(3) > span {
  color: #95631b;
  background: #fbf0d8;
}

.metric-grid article:nth-child(4) > span {
  color: #a14b43;
  background: #fae9e4;
}

.metric-grid strong {
  display: block;
  margin-top: 8px;
  color: #174e3c;
  font-size: 28px;
  line-height: 1.1;
}

.metric-grid strong small {
  margin-left: 3px;
  color: #748279;
  font-size: 11px;
}

.metric-grid p {
  margin-top: 5px;
  color: #78867e;
  font-size: 10px;
}

.journey-strip {
  margin-top: 14px;
  background: rgba(255, 255, 255, 0.9);
}

.function-groups {
  margin-top: 14px;
}

.function-group {
  background: rgba(255, 255, 255, 0.94);
  border-color: #dedfd7;
}

.function-group > header {
  min-height: 86px;
  padding: 14px 15px;
}

.function-group h2 {
  font-family: "Noto Serif SC", "Songti SC", SimSun, serif;
  font-size: 16px;
}

.learning-snapshot {
  margin-top: 14px;
  background: rgba(255, 255, 255, 0.94);
  border-color: #dedfd7;
}

.path-label {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 5px 8px;
  margin-top: 12px;
}

.path-label span,
.path-label small {
  color: #7b887f;
  font-size: 9px;
}

.path-label strong {
  color: #1d624a;
  font-size: 12px;
}

@media (max-width: 1100px) {
  .hero-grid {
    grid-template-columns: 1fr;
  }

  .trust-panel {
    min-height: 220px;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .hub-page {
    padding-top: 16px;
  }

  .workbench-hero {
    min-height: 0;
    padding: 24px 20px;
  }

  .workbench-hero::before {
    background: rgba(255, 252, 242, 0.86);
  }

  .hero-copy h1 {
    font-size: 30px;
  }

  .hero-task {
    position: static;
    width: 100%;
    margin-top: 18px;
  }

  .hero-actions {
    flex-wrap: wrap;
  }
}

@media (max-width: 620px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .trust-panel > strong {
    font-size: 42px;
  }
}
</style>
