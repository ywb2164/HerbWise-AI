<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NDrawer,
  NDrawerContent,
  NEmpty,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSelect,
  NSpin,
  NTag,
  useMessage,
} from 'naive-ui'
import { BookOpenText, Plus, RefreshCw, ShieldCheck, WandSparkles } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import SourceBadge from '../components/SourceBadge.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { ResourceItem, ReviewResult } from '../types/api'
import {
  formatDate,
  formatResourceStatus,
  getErrorMessage,
  taskTypeLabels,
} from '../utils/format'

const auth = useAuthStore()
const message = useMessage()
const loading = ref(false)
const generating = ref(false)
const reviewing = ref(false)
const showGenerate = ref(false)
const showDetail = ref(false)
const resources = ref<ResourceItem[]>([])
const selectedResource = ref<ResourceItem | null>(null)
const selectedReview = ref<ReviewResult | null>(null)
const form = reactive({
  medicineName: '黄芪',
  resourceType: 'lecture',
  difficulty: 'basic',
})

const resourceTypeOptions = [
  { label: '专题讲义', value: 'lecture' },
  { label: '学习指南', value: 'guide' },
  { label: '巩固测验', value: 'quiz' },
  { label: '近似药对比卡', value: 'comparison_card' },
  { label: '复习报告', value: 'review_report' },
  { label: '学习报告', value: 'learning_report' },
]

const difficultyOptions = [
  { label: '基础', value: 'basic' },
  { label: '进阶', value: 'intermediate' },
  { label: '高阶', value: 'advanced' },
]

const approvedCount = computed(() => resources.value.filter((item) => item.status === 'approved').length)
const pendingCount = computed(
  () => resources.value.filter((item) => ['generated', 'reviewing', 'needs_revision'].includes(item.status)).length,
)
const resourceTypes = computed(() => new Set(resources.value.map((item) => item.resource_type)).size)

function statusType(status: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
  if (status === 'approved') return 'success'
  if (['needs_revision', 'reviewing', 'generated'].includes(status)) return 'warning'
  if (status === 'rejected') return 'error'
  if (status === 'generating') return 'info'
  return 'default'
}

async function loadResources(): Promise<void> {
  loading.value = true
  try {
    resources.value = (await api.listResources(auth.learnerId)).items
  } catch (error) {
    message.error(getErrorMessage(error, '学习资源加载失败'))
  } finally {
    loading.value = false
  }
}

async function openResource(item: ResourceItem): Promise<void> {
  showDetail.value = true
  selectedReview.value = null
  try {
    selectedResource.value = await api.getResource(item.resource_id)
    try {
      selectedReview.value = await api.getResourceReview(item.resource_id)
    } catch {
      selectedReview.value = null
    }
  } catch (error) {
    message.error(getErrorMessage(error, '资源详情加载失败'))
  }
}

async function generateResource(): Promise<void> {
  if (!form.medicineName.trim()) {
    message.warning('请填写药材名称')
    return
  }
  generating.value = true
  try {
    const item = await api.generateResource({
      learner_id: auth.learnerId,
      medicine_name: form.medicineName.trim(),
      resource_type: form.resourceType,
      difficulty: form.difficulty,
      task_id: localStorage.getItem('herbwise.last_task_id') || undefined,
    })
    showGenerate.value = false
    await loadResources()
    await openResource(item)
    message.success('个性化资源已生成')
  } catch (error) {
    message.error(getErrorMessage(error, '资源生成失败'))
  } finally {
    generating.value = false
  }
}

async function reviewResource(): Promise<void> {
  if (!selectedResource.value) return
  reviewing.value = true
  try {
    selectedReview.value = await api.reviewResource(selectedResource.value.resource_id)
    selectedResource.value = await api.getResource(selectedResource.value.resource_id)
    await loadResources()
    message.success('资源审核已完成')
  } catch (error) {
    message.error(getErrorMessage(error, '资源审核失败'))
  } finally {
    reviewing.value = false
  }
}

onMounted(loadResources)
</script>

<template>
  <div class="page resources-page">
    <PageHeader title="学习资源" :meta="`学习者 ${auth.learnerId}`">
      <template #actions>
        <n-button secondary :loading="loading" @click="loadResources">
          刷新列表
          <template #icon><RefreshCw :size="17" /></template>
        </n-button>
        <n-button type="primary" @click="showGenerate = true">
          生成资源
          <template #icon><Plus :size="17" /></template>
        </n-button>
      </template>
    </PageHeader>

    <section class="resource-summary">
      <div>
        <span>资源总数</span>
        <strong>{{ resources.length }}</strong>
      </div>
      <div>
        <span>已审核通过</span>
        <strong>{{ approvedCount }}</strong>
      </div>
      <div>
        <span>待审核 / 修订</span>
        <strong>{{ pendingCount }}</strong>
      </div>
      <div>
        <span>资源类型</span>
        <strong>{{ resourceTypes }}</strong>
      </div>
    </section>

    <section class="surface resource-table-panel">
      <div class="surface-header">
        <div>
          <h2 class="surface-title">个性化资源库</h2>
          <span class="surface-caption">讲义、指南、测验与对比卡</span>
        </div>
        <SourceBadge source="mixed" :official="false" />
      </div>
      <n-spin :show="loading">
        <div v-if="resources.length" class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 34%">资源名称</th>
                <th>类型</th>
                <th>难度</th>
                <th>状态</th>
                <th>来源</th>
                <th>生成时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in resources" :key="item.resource_id" class="clickable" @click="openResource(item)">
                <td>
                  <div class="resource-cell">
                    <BookOpenText :size="17" />
                    <div>
                      <strong>{{ item.title }}</strong>
                      <span class="mono">{{ item.resource_id }}</span>
                    </div>
                  </div>
                </td>
                <td>{{ taskTypeLabels[item.resource_type] || item.resource_type }}</td>
                <td>{{ item.difficulty }}</td>
                <td>
                  <n-tag size="small" :type="statusType(item.status)" :bordered="false">
                    {{ formatResourceStatus(item.status) }}
                  </n-tag>
                </td>
                <td><SourceBadge :source="item.provider" :official="item.provider !== 'mock'" /></td>
                <td>{{ formatDate(item.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state">
          <n-empty description="暂无个性化资源">
            <template #extra><n-button type="primary" @click="showGenerate = true">生成第一份资源</n-button></template>
          </n-empty>
        </div>
      </n-spin>
    </section>
  </div>

  <n-modal
    v-model:show="showGenerate"
    preset="card"
    title="生成个性化资源"
    :bordered="false"
    :style="{ width: 'min(520px, calc(100vw - 32px))' }"
  >
    <n-form label-placement="top" :model="form">
      <n-form-item label="药材名称">
        <n-input v-model:value="form.medicineName" placeholder="例如：黄芪" />
      </n-form-item>
      <n-form-item label="资源类型">
        <n-select v-model:value="form.resourceType" :options="resourceTypeOptions" />
      </n-form-item>
      <n-form-item label="难度">
        <n-select v-model:value="form.difficulty" :options="difficultyOptions" />
      </n-form-item>
    </n-form>
    <template #footer>
      <div class="modal-actions">
        <n-button @click="showGenerate = false">取消</n-button>
        <n-button type="primary" :loading="generating" @click="generateResource">
          开始生成
          <template #icon><WandSparkles :size="17" /></template>
        </n-button>
      </div>
    </template>
  </n-modal>

  <n-drawer v-model:show="showDetail" placement="right" :width="680">
    <n-drawer-content :title="selectedResource?.title || '资源详情'" closable>
      <div v-if="selectedResource" class="resource-detail">
        <div class="detail-meta-row">
          <n-tag :type="statusType(selectedResource.status)" :bordered="false">
            {{ formatResourceStatus(selectedResource.status) }}
          </n-tag>
          <SourceBadge :source="selectedResource.provider" :official="selectedResource.provider !== 'mock'" />
          <span>{{ taskTypeLabels[selectedResource.resource_type] || selectedResource.resource_type }}</span>
          <span>{{ selectedResource.difficulty }}</span>
        </div>

        <dl class="resource-meta">
          <div><dt>资源 ID</dt><dd class="mono">{{ selectedResource.resource_id }}</dd></div>
          <div><dt>任务 ID</dt><dd class="mono">{{ selectedResource.task_id || '--' }}</dd></div>
          <div><dt>生成时间</dt><dd>{{ formatDate(selectedResource.created_at) }}</dd></div>
        </dl>

        <div class="content-prewrap detail-content">{{ selectedResource.content_markdown || '暂无文本内容' }}</div>

        <section class="review-section">
          <div class="review-heading">
            <div>
              <h3>质量审核</h3>
              <span>{{ selectedReview ? formatDate(selectedReview.reviewed_at) : '尚未审核' }}</span>
            </div>
            <n-button type="primary" secondary :loading="reviewing" @click="reviewResource">
              执行审核
              <template #icon><ShieldCheck :size="17" /></template>
            </n-button>
          </div>
          <template v-if="selectedReview">
            <div class="review-score-grid">
              <div><span>药典一致性</span><strong>{{ selectedReview.pharmacopoeia_consistency_score ?? '--' }}</strong></div>
              <div><span>术语准确性</span><strong>{{ selectedReview.terminology_accuracy_score ?? '--' }}</strong></div>
              <div><span>来源完整性</span><strong>{{ selectedReview.source_completeness_score ?? '--' }}</strong></div>
              <div><span>幻觉风险</span><strong>{{ selectedReview.hallucination_risk_score ?? '--' }}</strong></div>
            </div>
            <div v-if="selectedReview.issues.length || selectedReview.suggestions.length" class="review-notes">
              <p v-for="item in selectedReview.issues" :key="item">问题：{{ item }}</p>
              <p v-for="item in selectedReview.suggestions" :key="item">建议：{{ item }}</p>
            </div>
          </template>
          <n-empty v-else size="small" description="暂无审核记录" />
        </section>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.resource-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  margin-bottom: 20px;
  background: #fff;
  border: 1px solid var(--line);
}

.resource-summary > div {
  display: grid;
  gap: 3px;
  min-height: 92px;
  padding: 18px 22px;
  border-right: 1px solid var(--line);
}

.resource-summary > div:last-child {
  border-right: 0;
}

.resource-summary span {
  color: var(--muted);
  font-size: 11px;
}

.resource-summary strong {
  color: var(--ink);
  font-size: 27px;
  line-height: 1.2;
}

.surface-caption {
  display: block;
  margin-top: 3px;
  color: var(--subtle);
  font-size: 11px;
}

.resource-table-panel {
  min-height: 420px;
}

.resource-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.resource-cell svg {
  flex: 0 0 auto;
  color: var(--primary);
}

.resource-cell > div {
  display: grid;
  min-width: 0;
}

.resource-cell strong,
.resource-cell span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-cell strong {
  font-size: 13px;
}

.resource-cell span {
  color: var(--subtle);
  font-size: 9px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.resource-detail {
  display: grid;
  gap: 18px;
}

.detail-meta-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  color: var(--muted);
  font-size: 11px;
}

.resource-meta {
  display: grid;
  gap: 7px;
  margin: 0;
  padding: 14px 0;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}

.resource-meta > div {
  display: grid;
  grid-template-columns: 100px minmax(0, 1fr);
  gap: 12px;
}

.resource-meta dt,
.resource-meta dd {
  margin: 0;
  font-size: 11px;
}

.resource-meta dt {
  color: var(--muted);
}

.resource-meta dd {
  color: var(--ink);
  overflow-wrap: anywhere;
}

.detail-content {
  max-height: 44vh;
  overflow-y: auto;
}

.review-section {
  padding-top: 18px;
  border-top: 1px solid var(--line);
}

.review-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.review-heading h3 {
  color: var(--ink);
  font-size: 15px;
}

.review-heading span {
  color: var(--subtle);
  font-size: 10px;
}

.review-score-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border: 1px solid var(--line);
}

.review-score-grid > div {
  display: grid;
  gap: 3px;
  padding: 12px;
  border-right: 1px solid var(--line);
}

.review-score-grid > div:last-child {
  border-right: 0;
}

.review-score-grid span {
  color: var(--muted);
  font-size: 9px;
}

.review-score-grid strong {
  color: var(--primary);
  font-size: 18px;
}

.review-notes {
  display: grid;
  gap: 5px;
  margin-top: 12px;
  padding: 12px;
  color: #70531f;
  background: var(--amber-soft);
  font-size: 11px;
}

@media (max-width: 760px) {
  .resource-summary {
    grid-template-columns: repeat(2, 1fr);
  }

  .resource-summary > div:nth-child(2) {
    border-right: 0;
  }

  .resource-summary > div:nth-child(-n + 2) {
    border-bottom: 1px solid var(--line);
  }

  .review-score-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .review-score-grid > div:nth-child(2) {
    border-right: 0;
  }

  .review-score-grid > div:nth-child(-n + 2) {
    border-bottom: 1px solid var(--line);
  }
}
</style>
