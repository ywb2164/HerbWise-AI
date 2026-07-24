<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NAlert, NButton, NProgress, NSpin, NTag } from 'naive-ui'
import {
  ArrowRight,
  BookOpenCheck,
  BrainCircuit,
  RefreshCw,
  ScanSearch,
  TriangleAlert,
} from 'lucide-vue-next'
import DimensionRadar from '../components/DimensionRadar.vue'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { DiagnosisResult, LearnerDimension, LearnerProfile, WeakPoint } from '../types/api'
import { dimensionLabels, getErrorMessage, levelLabels, taskTypeLabels } from '../utils/format'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const refreshing = ref(false)
const errorText = ref('')
const diagnosis = ref<DiagnosisResult | null>(null)
const profile = ref<LearnerProfile | null>(null)
const dimensions = ref<LearnerDimension[]>([])
const weakPoints = ref<WeakPoint[]>([])

const difficulty = computed(() => {
  const score = diagnosis.value?.overall_score || 0
  if (score < 60) return { label: '入门', note: '概念讲义、基础性状与单点练习', tone: 'warning' as const }
  if (score < 75) return { label: '基础', note: '实操指南、辨析卡与巩固测验', tone: 'info' as const }
  if (score < 90) return { label: '进阶', note: '相似饮片辨析与质量控制任务', tone: 'success' as const }
  return { label: '挑战', note: '复杂样本复核与综合质量评价', tone: 'success' as const }
})

const weakDimensionItems = computed(() =>
  (diagnosis.value?.weak_dimensions || []).map(code => ({
    code,
    label: dimensionLabels[code] || code,
    score: diagnosis.value?.dimension_scores[code] || 0,
  })),
)

const confusionPoints = computed(() =>
  weakPoints.value.filter(point => point.dimension_code === 'similar_medicine' && !point.is_resolved),
)

const initialScore = computed(() => {
  const value = Number(sessionStorage.getItem('herbwise.last_initial_score'))
  return Number.isFinite(value) ? Math.round(value) : null
})

async function load(showRefresh = false): Promise<void> {
  if (showRefresh) refreshing.value = true
  else loading.value = true
  errorText.value = ''
  try {
    const [diagnosisResult, profileResult, dimensionResult, weakPointResult] = await Promise.all([
      api.diagnoseProfile(auth.learnerId),
      api.getProfile(auth.learnerId),
      api.getDimensions(auth.learnerId),
      api.getWeakPoints(auth.learnerId),
    ])
    diagnosis.value = diagnosisResult
    profile.value = profileResult
    dimensions.value = dimensionResult
    weakPoints.value = weakPointResult
    sessionStorage.setItem('herbwise.last_diagnosis', JSON.stringify(diagnosisResult))
  } catch (error) {
    errorText.value = getErrorMessage(error, '诊断结果加载失败')
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

onMounted(() => {
  const cached = sessionStorage.getItem('herbwise.last_diagnosis')
  if (cached) {
    try {
      diagnosis.value = JSON.parse(cached) as DiagnosisResult
    } catch {
      sessionStorage.removeItem('herbwise.last_diagnosis')
    }
  }
  void load()
})
</script>

<template>
  <div class="page diagnosis-page">
    <PageHeader title="学习能力诊断" eyebrow="学习准备" :meta="profile?.name || auth.learnerId">
      <template #actions>
        <n-button secondary :loading="refreshing" @click="load(true)">
          重新诊断
          <template #icon><RefreshCw :size="17" /></template>
        </n-button>
        <n-button type="primary" @click="router.push('/dashboard')">
          进入学习工作台
          <template #icon><ArrowRight :size="17" /></template>
        </n-button>
      </template>
    </PageHeader>

    <n-alert v-if="errorText" type="error" :bordered="false" class="diagnosis-alert">
      {{ errorText }}
    </n-alert>

    <n-spin :show="loading">
      <section class="diagnosis-hero">
        <div class="score-block">
          <span>综合能力</span>
          <strong>{{ Math.round(diagnosis?.overall_score || 0) }}</strong>
          <small>/ 100</small>
        </div>
        <div class="diagnosis-copy">
          <n-tag size="small" :bordered="false" type="success">
            {{ levelLabels[diagnosis?.overall_level || 'weak'] || diagnosis?.overall_level }}
          </n-tag>
          <h2>{{ weakDimensionItems.length ? `发现 ${weakDimensionItems.length} 个优先提升维度` : '六维基础较为均衡' }}</h2>
          <p>
            理论测试 {{ initialScore ?? '--' }} 分，当前资源难度为“{{ difficulty.label }}”，后续任务将根据实操反馈持续更新。
          </p>
        </div>
        <div class="hero-actions">
          <n-button secondary @click="router.push('/profile')">查看画像</n-button>
          <n-button type="primary" @click="router.push('/recognition')">
            开始实训
            <template #icon><ScanSearch :size="17" /></template>
          </n-button>
        </div>
      </section>

      <section class="diagnostic-grid">
        <article class="diagnostic-panel">
          <header>
            <BrainCircuit :size="20" />
            <div><span>01</span><h3>知识基础</h3></div>
          </header>
          <div class="dimension-bars">
            <div v-for="item in dimensions" :key="item.dimension_code" class="dimension-bar">
              <div><span>{{ dimensionLabels[item.dimension_code] || item.dimension_code }}</span><strong>{{ Math.round(item.score) }}</strong></div>
              <n-progress
                type="line"
                :percentage="item.score"
                :height="6"
                :show-indicator="false"
                :color="item.score < 60 ? '#bd7a20' : '#1f6b4f'"
                rail-color="#edf1ee"
              />
            </div>
          </div>
        </article>

        <article class="diagnostic-panel">
          <header>
            <TriangleAlert :size="20" />
            <div><span>02</span><h3>技能盲区</h3></div>
          </header>
          <div v-if="weakDimensionItems.length" class="weak-list">
            <div v-for="item in weakDimensionItems" :key="item.code">
              <span>{{ item.label }}</span>
              <strong>{{ Math.round(item.score) }} 分</strong>
            </div>
          </div>
          <div v-else class="panel-empty">暂无低于 60 分的能力维度</div>
          <div v-if="diagnosis?.weak_knowledge_points.length" class="knowledge-gaps">
            <n-tag v-for="point in diagnosis.weak_knowledge_points" :key="point" size="small" :bordered="false">
              {{ point }}
            </n-tag>
          </div>
        </article>

        <article class="diagnostic-panel">
          <header>
            <ScanSearch :size="20" />
            <div><span>03</span><h3>易混淆药材</h3></div>
          </header>
          <div v-if="confusionPoints.length" class="confusion-list">
            <div v-for="point in confusionPoints" :key="`${point.knowledge_point}-${point.created_at}`">
              <strong>{{ point.knowledge_point }}</strong>
              <n-tag size="small" :bordered="false" type="warning">{{ point.severity }}</n-tag>
            </div>
          </div>
          <div v-else class="panel-empty">
            完成饮片识别后，系统将在此沉淀需要重点辨析的药材。
          </div>
        </article>

        <article class="diagnostic-panel difficulty-panel">
          <header>
            <BookOpenCheck :size="20" />
            <div><span>04</span><h3>资源难度</h3></div>
          </header>
          <div class="difficulty-value">
            <n-tag :type="difficulty.tone" :bordered="false">{{ difficulty.label }}</n-tag>
            <p>{{ difficulty.note }}</p>
          </div>
          <div class="resource-types">
            <span v-for="type in diagnosis?.recommended_resource_types || []" :key="type">
              {{ taskTypeLabels[type] || type }}
            </span>
          </div>
        </article>
      </section>

      <section class="radar-band">
        <div>
          <span class="eyebrow">六维能力图谱</span>
          <h2>诊断证据分布</h2>
          <p>画像信息、理论测试与后续实操反馈共同更新各维度得分。</p>
        </div>
        <DimensionRadar :dimensions="dimensions" />
      </section>
    </n-spin>
  </div>
</template>

<style scoped>
.diagnosis-alert {
  margin-bottom: 16px;
}

.diagnosis-hero {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr) auto;
  align-items: center;
  gap: 26px;
  min-height: 164px;
  padding: 26px 28px;
  background: #eef5f1;
  border-top: 1px solid #d5e4da;
  border-bottom: 1px solid #d5e4da;
  border-left: 4px solid var(--primary);
}

.score-block {
  display: grid;
  grid-template-columns: auto auto;
  align-items: baseline;
  width: 126px;
}

.score-block > span {
  grid-column: 1 / -1;
  color: var(--muted);
  font-size: 12px;
}

.score-block strong {
  color: var(--primary-strong);
  font-size: 52px;
  line-height: 1.1;
}

.score-block small {
  color: var(--muted);
  font-size: 12px;
}

.diagnosis-copy h2 {
  margin: 8px 0 5px;
  color: var(--ink);
  font-size: 21px;
  line-height: 1.4;
}

.diagnosis-copy p {
  max-width: 700px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 9px;
}

.diagnostic-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 20px;
}

.diagnostic-panel {
  min-width: 0;
  min-height: 280px;
  padding: 18px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.diagnostic-panel header {
  display: flex;
  align-items: center;
  gap: 11px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line);
}

.diagnostic-panel header > svg {
  color: var(--primary);
}

.diagnostic-panel header div {
  display: grid;
}

.diagnostic-panel header span {
  color: var(--subtle);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 9px;
}

.diagnostic-panel h3 {
  color: var(--ink);
  font-size: 15px;
}

.dimension-bars,
.weak-list,
.confusion-list {
  display: grid;
  gap: 11px;
  margin-top: 16px;
}

.dimension-bar {
  display: grid;
  gap: 5px;
}

.dimension-bar > div,
.weak-list > div,
.confusion-list > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.dimension-bar span,
.weak-list span {
  color: var(--muted);
  font-size: 11px;
}

.dimension-bar strong,
.weak-list strong,
.confusion-list strong {
  color: var(--ink);
  font-size: 11px;
}

.knowledge-gaps,
.resource-types {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}

.panel-empty {
  display: grid;
  min-height: 160px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
  place-items: center;
  text-align: center;
}

.difficulty-value {
  display: grid;
  gap: 12px;
  margin-top: 18px;
}

.difficulty-value .n-tag {
  width: fit-content;
}

.difficulty-value p {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
}

.resource-types span {
  color: var(--primary-strong);
  font-size: 11px;
}

.radar-band {
  display: grid;
  grid-template-columns: minmax(260px, 0.7fr) minmax(420px, 1.3fr);
  align-items: center;
  gap: 26px;
  margin-top: 20px;
  padding: 24px 28px;
  background: #fff;
  border: 1px solid var(--line);
}

.radar-band h2 {
  margin: 5px 0 7px;
  color: var(--ink);
  font-size: 20px;
}

.radar-band p {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
}

@media (max-width: 1180px) {
  .diagnostic-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 820px) {
  .diagnosis-hero {
    grid-template-columns: 120px minmax(0, 1fr);
  }

  .hero-actions {
    grid-column: 1 / -1;
  }

  .radar-band {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .diagnosis-hero,
  .diagnostic-grid {
    grid-template-columns: 1fr;
  }

  .hero-actions {
    grid-column: auto;
    align-items: stretch;
    flex-direction: column;
  }

  .diagnostic-panel {
    min-height: auto;
  }

  .radar-band {
    padding-inline: 16px;
  }
}
</style>
