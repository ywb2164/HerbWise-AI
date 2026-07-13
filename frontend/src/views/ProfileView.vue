<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NAlert, NButton, NEmpty, NProgress, NSpin, NTag, useMessage } from 'naive-ui'
import { AlertTriangle, CheckCircle2, History, RefreshCw, Target, UserRound } from 'lucide-vue-next'
import DimensionRadar from '../components/DimensionRadar.vue'
import PageHeader from '../components/PageHeader.vue'
import SourceBadge from '../components/SourceBadge.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { LearnerDimension, LearnerProfile, LearningPath, ProfileHistoryItem, WeakPoint } from '../types/api'
import {
  dimensionLabels,
  formatDate,
  getErrorMessage,
  levelLabels,
  taskTypeLabels,
} from '../utils/format'

const auth = useAuthStore()
const message = useMessage()
const loading = ref(true)
const updating = ref(false)
const errorText = ref('')
const profile = ref<LearnerProfile | null>(null)
const dimensions = ref<LearnerDimension[]>([])
const weakPoints = ref<WeakPoint[]>([])
const learningPath = ref<LearningPath | null>(null)
const profileHistory = ref<ProfileHistoryItem[]>([])

const historyLabels: Record<string, string> = {
  profile_created: '画像已建立',
  profile_updated: '画像信息已更新',
  dimension_updated: '能力维度已更新',
  initial_test_submitted: '理论测试已提交',
  learning_path_updated: '学习路径已更新',
}

const averageScore = computed(() => {
  if (!dimensions.value.length) return 0
  return Math.round(dimensions.value.reduce((sum, item) => sum + item.score, 0) / dimensions.value.length)
})

const activeWeakPoints = computed(() => weakPoints.value.filter((item) => !item.is_resolved))

async function loadProfile(): Promise<void> {
  loading.value = true
  errorText.value = ''
  const learnerId = auth.learnerId
  const results = await Promise.allSettled([
    api.getProfile(learnerId),
    api.getDimensions(learnerId),
    api.getWeakPoints(learnerId),
    api.getLearningPath(learnerId),
    api.getProfileHistory(learnerId),
  ])
  if (results[0].status === 'fulfilled') profile.value = results[0].value
  if (results[1].status === 'fulfilled') dimensions.value = results[1].value
  if (results[2].status === 'fulfilled') weakPoints.value = results[2].value
  if (results[3].status === 'fulfilled') learningPath.value = results[3].value
  if (results[4].status === 'fulfilled') profileHistory.value = results[4].value
  const rejected = results.find((item) => item.status === 'rejected')
  if (rejected?.status === 'rejected') errorText.value = getErrorMessage(rejected.reason, '学情数据加载失败')
  loading.value = false
}

async function updatePath(): Promise<void> {
  updating.value = true
  try {
    learningPath.value = await api.updateLearningPath(auth.learnerId)
    message.success('学习路径已生成新版本')
  } catch (error) {
    message.error(getErrorMessage(error, '学习路径更新失败'))
  } finally {
    updating.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <div class="page">
    <PageHeader title="学情画像" :meta="`学习者 ${auth.learnerId}`">
      <template #actions>
        <n-button secondary :loading="loading" @click="loadProfile">
          刷新画像
          <template #icon><RefreshCw :size="17" /></template>
        </n-button>
        <n-button type="primary" :loading="updating" @click="updatePath">
          更新学习路径
          <template #icon><Target :size="17" /></template>
        </n-button>
      </template>
    </PageHeader>

    <n-alert v-if="errorText" type="warning" :bordered="false" class="profile-alert">{{ errorText }}</n-alert>

    <n-spin :show="loading">
      <div class="section-stack">
        <section class="profile-band">
          <div class="profile-identity">
            <div class="profile-avatar"><UserRound :size="25" /></div>
            <div>
              <span class="eyebrow">{{ profile?.identity_type || '学生' }}</span>
              <h2>{{ profile?.name || auth.user?.display_name || '学习者' }}</h2>
              <p>{{ profile?.professional_background || profile?.education_background || '中药材辨识学习者' }}</p>
            </div>
          </div>
          <div class="profile-summary-grid">
            <div>
              <span>综合等级</span>
              <strong>{{ levelLabels[profile?.overall_level || 'basic'] || profile?.overall_level || '--' }}</strong>
            </div>
            <div>
              <span>六维均分</span>
              <strong>{{ averageScore }}</strong>
            </div>
            <div>
              <span>待加强项</span>
              <strong>{{ activeWeakPoints.length }}</strong>
            </div>
            <div>
              <span>路径版本</span>
              <strong>V{{ learningPath?.version || 0 }}</strong>
            </div>
          </div>
        </section>

        <section class="page-grid profile-grid">
          <div class="surface">
            <div class="surface-header">
              <div>
                <h2 class="surface-title">六维能力分布</h2>
                <span class="surface-caption">更新于 {{ formatDate(profile?.updated_at) }}</span>
              </div>
              <SourceBadge source="mixed" />
            </div>
            <div class="surface-body radar-body"><DimensionRadar :dimensions="dimensions" /></div>
          </div>

          <div class="surface">
            <div class="surface-header">
              <div>
                <h2 class="surface-title">维度得分</h2>
                <span class="surface-caption">100 分制</span>
              </div>
            </div>
            <div v-if="dimensions.length" class="score-list">
              <div v-for="item in dimensions" :key="item.dimension_code" class="score-row">
                <div class="score-row-head">
                  <span>{{ dimensionLabels[item.dimension_code] || item.dimension_code }}</span>
                  <div>
                    <n-tag
                      size="small"
                      :type="item.score < 60 ? 'warning' : item.score >= 85 ? 'success' : 'default'"
                      :bordered="false"
                    >
                      {{ levelLabels[item.level] || item.level }}
                    </n-tag>
                    <strong>{{ Math.round(item.score) }}</strong>
                  </div>
                </div>
                <n-progress
                  type="line"
                  :percentage="item.score"
                  :height="8"
                  :show-indicator="false"
                  :color="item.score < 60 ? '#bd7a20' : item.score >= 85 ? '#2f6f8f' : '#1f6b4f'"
                  rail-color="#edf1ee"
                />
              </div>
            </div>
            <div v-else class="empty-state"><n-empty description="暂无维度评估" /></div>
          </div>
        </section>

        <section class="page-grid two-column">
          <div class="surface">
            <div class="surface-header">
              <div>
                <h2 class="surface-title">待加强知识点</h2>
                <span class="surface-caption">{{ activeWeakPoints.length }} 项未解决</span>
              </div>
              <AlertTriangle :size="19" color="#bd7a20" />
            </div>
            <div v-if="activeWeakPoints.length" class="weak-list">
              <div v-for="item in activeWeakPoints" :key="`${item.dimension_code}-${item.knowledge_point}`" class="weak-row">
                <span class="weak-indicator" :class="item.severity" />
                <div>
                  <strong>{{ item.knowledge_point }}</strong>
                  <span>{{ dimensionLabels[item.dimension_code] || item.dimension_code }}</span>
                </div>
                <n-tag size="small" type="warning" :bordered="false">{{ item.severity }}</n-tag>
              </div>
            </div>
            <div v-else class="empty-state">
              <n-empty description="当前无未解决薄弱点">
                <template #icon><CheckCircle2 :size="34" color="#1f6b4f" /></template>
              </n-empty>
            </div>
          </div>

          <div class="surface">
            <div class="surface-header">
              <div>
                <h2 class="surface-title">个性化学习路径</h2>
                <span class="surface-caption">{{ levelLabels[learningPath?.current_stage || 'foundation'] || learningPath?.current_stage }}</span>
              </div>
              <n-tag type="success" size="small" :bordered="false">{{ learningPath?.status || 'active' }}</n-tag>
            </div>
            <div v-if="learningPath" class="path-content">
              <div class="path-stage-line">
                <div
                  v-for="(stage, index) in [
                    { code: 'foundation', label: '基础巩固' },
                    { code: 'consolidation', label: '进阶巩固' },
                    { code: 'advanced', label: '高阶实践' },
                  ]"
                  :key="stage.code"
                  class="stage-item"
                  :class="{ active: stage.code === learningPath.current_stage }"
                >
                  <span>{{ index + 1 }}</span>
                  <strong>{{ stage.label }}</strong>
                </div>
              </div>
              <div class="recommended-tasks">
                <span class="detail-label">推荐任务</span>
                <div>
                  <n-tag
                    v-for="task in learningPath.path.recommended_task_types || []"
                    :key="task"
                    :bordered="false"
                  >
                    {{ taskTypeLabels[task] || task }}
                  </n-tag>
                </div>
              </div>
              <dl class="path-meta">
                <div>
                  <dt>路径规则</dt>
                  <dd>{{ learningPath.path.rule_version || '--' }}</dd>
                </div>
                <div>
                  <dt>生成原因</dt>
                  <dd>{{ learningPath.reason || '--' }}</dd>
                </div>
                <div>
                  <dt>更新时间</dt>
                  <dd>{{ formatDate(learningPath.updated_at) }}</dd>
                </div>
              </dl>
            </div>
            <div v-else class="empty-state"><n-empty description="暂无学习路径" /></div>
          </div>
        </section>

        <section class="goal-band">
          <Target :size="23" />
          <div>
            <span>学习目标</span>
            <strong>{{ profile?.learning_goal || '完成中药材性状辨识与近似药区分训练' }}</strong>
          </div>
          <span>{{ profile?.learning_preference || '结构化学习' }}</span>
        </section>

        <section class="surface history-surface">
          <div class="surface-header">
            <div>
              <h2 class="surface-title">画像更新记录</h2>
              <span class="surface-caption">测试、实训与学习路径的可追溯变化</span>
            </div>
            <History :size="19" color="#1f6b4f" />
          </div>
          <div v-if="profileHistory.length" class="profile-history-list">
            <div v-for="(item, index) in profileHistory.slice(0, 8)" :key="`${item.event_type}-${item.created_at}-${index}`">
              <span class="history-dot" />
              <div>
                <strong>{{ historyLabels[item.event_type] || item.event_type }}</strong>
                <small>{{ item.source_task_id ? `任务 ${item.source_task_id}` : '学习画像' }}</small>
              </div>
              <time>{{ formatDate(item.created_at) }}</time>
            </div>
          </div>
          <div v-else class="empty-state"><n-empty description="暂无画像更新记录" /></div>
        </section>
      </div>
    </n-spin>
  </div>
</template>

<style scoped>
.profile-alert {
  margin-bottom: 18px;
}

.profile-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  min-height: 132px;
  padding: 24px 28px;
  background: #eff6f2;
  border: 1px solid #d5e5da;
}

.profile-identity {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.profile-avatar {
  display: grid;
  flex: 0 0 52px;
  width: 52px;
  height: 52px;
  color: #fff;
  background: var(--primary);
  border-radius: 8px;
  place-items: center;
}

.profile-identity h2 {
  margin: 3px 0 2px;
  color: var(--ink);
  font-size: 22px;
  font-weight: 700;
}

.profile-identity p {
  overflow: hidden;
  max-width: 440px;
  color: var(--muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(86px, 1fr));
  border-left: 1px solid #ccdcd1;
}

.profile-summary-grid > div {
  display: grid;
  gap: 3px;
  min-width: 92px;
  padding: 5px 18px;
  border-right: 1px solid #d8e5dc;
}

.profile-summary-grid > div:last-child {
  border-right: 0;
}

.profile-summary-grid span {
  color: var(--muted);
  font-size: 10px;
}

.profile-summary-grid strong {
  color: var(--ink);
  font-size: 19px;
}

.profile-grid {
  grid-template-columns: minmax(420px, 0.9fr) minmax(420px, 1.1fr);
}

.surface-caption {
  display: block;
  margin-top: 3px;
  color: var(--subtle);
  font-size: 11px;
}

.radar-body {
  padding-block: 4px 8px;
}

.score-list {
  display: grid;
  gap: 17px;
  padding: 20px;
}

.score-row {
  display: grid;
  gap: 7px;
}

.score-row-head,
.score-row-head > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.score-row-head > span {
  color: #4b5a52;
  font-size: 13px;
}

.score-row-head strong {
  min-width: 28px;
  color: var(--ink);
  font-size: 13px;
  text-align: right;
}

.weak-list {
  display: grid;
}

.weak-row {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 62px;
  padding: 10px 18px;
  border-bottom: 1px solid var(--line);
}

.weak-row:last-child {
  border-bottom: 0;
}

.weak-indicator {
  width: 7px;
  height: 28px;
  background: var(--amber);
  border-radius: 3px;
}

.weak-indicator.high,
.weak-indicator.severe {
  background: var(--danger);
}

.weak-row > div {
  display: grid;
  gap: 2px;
}

.weak-row strong {
  color: var(--ink);
  font-size: 13px;
}

.weak-row span {
  color: var(--muted);
  font-size: 11px;
}

.path-content {
  padding: 20px;
}

.path-stage-line {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.stage-item {
  display: grid;
  justify-items: center;
  gap: 8px;
  min-width: 0;
  padding: 12px 8px;
  color: var(--subtle);
  background: var(--surface-soft);
  border: 1px solid var(--line);
  border-radius: 6px;
}

.stage-item span {
  display: grid;
  width: 24px;
  height: 24px;
  border: 1px solid var(--line-strong);
  border-radius: 50%;
  font-size: 10px;
  place-items: center;
}

.stage-item strong {
  font-size: 11px;
  font-weight: 620;
  text-align: center;
}

.stage-item.active {
  color: var(--primary-strong);
  background: var(--primary-soft);
  border-color: #c9dfd2;
}

.stage-item.active span {
  color: #fff;
  background: var(--primary);
  border-color: var(--primary);
}

.recommended-tasks {
  display: grid;
  gap: 9px;
  margin-top: 20px;
}

.recommended-tasks > div {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.detail-label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 650;
}

.path-meta {
  display: grid;
  gap: 8px;
  margin: 18px 0 0;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}

.path-meta > div {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
  gap: 10px;
}

.path-meta dt,
.path-meta dd {
  margin: 0;
  font-size: 11px;
}

.path-meta dt {
  color: var(--muted);
}

.path-meta dd {
  color: var(--ink);
  overflow-wrap: anywhere;
}

.goal-band {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 18px 22px;
  color: var(--blue);
  background: var(--blue-soft);
  border-left: 4px solid var(--blue);
}

.goal-band > div {
  display: grid;
  gap: 2px;
}

.goal-band span {
  color: #60747f;
  font-size: 11px;
}

.goal-band strong {
  color: #284e61;
  font-size: 13px;
}

.profile-history-list {
  display: grid;
}

.profile-history-list > div {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr) 120px;
  align-items: center;
  gap: 10px;
  min-height: 58px;
  padding: 9px 18px;
  border-bottom: 1px solid var(--line);
}

.profile-history-list > div:last-child {
  border-bottom: 0;
}

.history-dot {
  width: 8px;
  height: 8px;
  background: var(--primary);
  border-radius: 50%;
}

.profile-history-list > div > div {
  display: grid;
  gap: 2px;
}

.profile-history-list strong {
  color: var(--ink);
  font-size: 12px;
}

.profile-history-list small,
.profile-history-list time {
  color: var(--subtle);
  font-size: 10px;
}

.profile-history-list time {
  text-align: right;
}

@media (max-width: 1200px) {
  .profile-band {
    align-items: flex-start;
    flex-direction: column;
  }

  .profile-summary-grid {
    width: 100%;
    border-top: 1px solid #ccdcd1;
    border-left: 0;
    padding-top: 16px;
  }
}

@media (max-width: 760px) {
  .profile-band {
    padding: 20px;
  }

  .profile-summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .profile-summary-grid > div {
    padding: 8px;
    border-bottom: 1px solid #d8e5dc;
  }

  .profile-grid {
    grid-template-columns: 1fr;
  }

  .goal-band {
    grid-template-columns: 28px minmax(0, 1fr);
  }

  .goal-band > span {
    grid-column: 2;
  }

  .profile-history-list > div {
    grid-template-columns: 14px minmax(0, 1fr);
  }

  .profile-history-list time {
    grid-column: 2;
    text-align: left;
  }
}
</style>
