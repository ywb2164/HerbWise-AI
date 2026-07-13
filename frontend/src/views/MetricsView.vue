<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NAlert, NButton, NProgress, NSpin, NTag } from 'naive-ui'
import {
  Activity,
  Bot,
  CheckCircle2,
  Database,
  FileCheck2,
  RefreshCw,
  ScanSearch,
  ShieldCheck,
  UsersRound,
} from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../services/api'
import type { CapabilityStatus, MetricsOverview, QualityMetric } from '../types/api'
import { getErrorMessage } from '../utils/format'

const loading = ref(true)
const errorText = ref('')
const overview = ref<MetricsOverview | null>(null)
const capabilities = ref<CapabilityStatus | null>(null)
const quality = ref<Record<string, QualityMetric | null>>({
  hallucination: null,
  adaptation: null,
  coverage: null,
})

const successRate = computed(() => {
  if (!overview.value?.task_count) return 0
  return Math.round((overview.value.successful_task_count / overview.value.task_count) * 100)
})
const reviewCoverage = computed(() => {
  if (!overview.value?.resource_count) return 0
  return Math.round((overview.value.review_count / overview.value.resource_count) * 100)
})
const approvalRate = computed(() => {
  if (!overview.value?.resource_count) return 0
  return Math.round((overview.value.approved_resource_count / overview.value.resource_count) * 100)
})

function metricValue(item: QualityMetric | null): string {
  if (item?.metric_value === null || item?.metric_value === undefined) return '--'
  const value = item.metric_value <= 1 ? item.metric_value * 100 : item.metric_value
  return `${value.toFixed(1)}%`
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  const results = await Promise.allSettled([
    api.getMetricsOverview(),
    api.getCapabilities(),
    api.getQualityMetric('hallucination'),
    api.getQualityMetric('adaptation'),
    api.getQualityMetric('coverage'),
  ])
  if (results[0].status === 'fulfilled') overview.value = results[0].value
  if (results[1].status === 'fulfilled') capabilities.value = results[1].value
  if (results[2].status === 'fulfilled') quality.value.hallucination = results[2].value
  if (results[3].status === 'fulfilled') quality.value.adaptation = results[3].value
  if (results[4].status === 'fulfilled') quality.value.coverage = results[4].value
  const failed = results.find(result => result.status === 'rejected')
  if (failed?.status === 'rejected') errorText.value = getErrorMessage(failed.reason, '部分指标加载失败')
  loading.value = false
}

onMounted(load)
</script>

<template>
  <div class="page metrics-page">
    <PageHeader title="测试指标大屏" eyebrow="结果沉淀" meta="识别、资源与证据链运行指标">
      <template #actions>
        <n-button secondary @click="load">
          刷新指标
          <template #icon><RefreshCw :size="17" /></template>
        </n-button>
      </template>
    </PageHeader>

    <n-alert v-if="errorText" type="warning" :bordered="false" class="metrics-alert">{{ errorText }}</n-alert>

    <n-spin :show="loading">
      <section class="metrics-summary">
        <article>
          <UsersRound :size="20" />
          <span>学习者画像</span>
          <strong>{{ overview?.learner_count ?? '--' }}</strong>
        </article>
        <article>
          <Database :size="20" />
          <span>药材知识</span>
          <strong>{{ overview?.medicine_count ?? '--' }}</strong>
        </article>
        <article>
          <Activity :size="20" />
          <span>智能体任务</span>
          <strong>{{ overview?.task_count ?? '--' }}</strong>
        </article>
        <article>
          <FileCheck2 :size="20" />
          <span>个性化资源</span>
          <strong>{{ overview?.resource_count ?? '--' }}</strong>
        </article>
        <article>
          <ShieldCheck :size="20" />
          <span>审核记录</span>
          <strong>{{ overview?.review_count ?? '--' }}</strong>
        </article>
        <article>
          <ScanSearch :size="20" />
          <span>知识来源</span>
          <strong>{{ overview?.knowledge_source_count ?? '--' }}</strong>
        </article>
      </section>

      <section class="operations-band">
        <div class="operations-heading">
          <span class="eyebrow">业务运行</span>
          <h2>核心闭环指标</h2>
        </div>
        <div class="operation-item">
          <div><span>任务成功率</span><strong>{{ successRate }}%</strong></div>
          <n-progress type="line" :percentage="successRate" :height="8" :show-indicator="false" color="#1f6b4f" rail-color="#e8eeea" />
          <small>{{ overview?.successful_task_count || 0 }} 成功 / {{ overview?.failed_task_count || 0 }} 失败</small>
        </div>
        <div class="operation-item">
          <div><span>资源审核覆盖</span><strong>{{ reviewCoverage }}%</strong></div>
          <n-progress type="line" :percentage="Math.min(reviewCoverage, 100)" :height="8" :show-indicator="false" color="#2f6f8f" rail-color="#e8eeea" />
          <small>{{ overview?.review_count || 0 }} 次审核</small>
        </div>
        <div class="operation-item">
          <div><span>资源通过率</span><strong>{{ approvalRate }}%</strong></div>
          <n-progress type="line" :percentage="approvalRate" :height="8" :show-indicator="false" color="#bd7a20" rail-color="#e8eeea" />
          <small>{{ overview?.approved_resource_count || 0 }} 份已通过</small>
        </div>
      </section>

      <section class="metrics-detail-grid">
        <article class="quality-panel surface">
          <header><div><span>内容质量</span><h2>审核评估指标</h2></div><CheckCircle2 :size="20" /></header>
          <div class="quality-list">
            <div>
              <span>幻觉风险控制</span>
              <strong>{{ metricValue(quality.hallucination) }}</strong>
              <small>样本 {{ quality.hallucination?.sample_count || 0 }}</small>
            </div>
            <div>
              <span>画像适配度</span>
              <strong>{{ metricValue(quality.adaptation) }}</strong>
              <small>样本 {{ quality.adaptation?.sample_count || 0 }}</small>
            </div>
            <div>
              <span>知识覆盖度</span>
              <strong>{{ metricValue(quality.coverage) }}</strong>
              <small>样本 {{ quality.coverage?.sample_count || 0 }}</small>
            </div>
          </div>
          <p class="sample-note">尚未形成有效样本的指标以“--”显示。</p>
        </article>

        <article class="capability-panel surface">
          <header><div><span>服务能力</span><h2>模型与引擎状态</h2></div><Bot :size="20" /></header>
          <div class="capability-list">
            <div><span>本地视觉模型</span><n-tag size="small" :bordered="false" :type="capabilities?.local_model_configured ? 'success' : 'default'">{{ capabilities?.local_model_configured ? '已配置' : '未配置' }}</n-tag></div>
            <div><span>本地模型加载</span><n-tag size="small" :bordered="false" :type="capabilities?.local_model_loaded ? 'success' : 'default'">{{ capabilities?.local_model_loaded ? '已加载' : '待加载' }}</n-tag></div>
            <div><span>视觉复核模型</span><n-tag size="small" :bordered="false" :type="capabilities?.qwen_configured ? 'success' : 'default'">{{ capabilities?.qwen_configured ? '可用' : '未配置' }}</n-tag></div>
            <div><span>资源生成模型</span><n-tag size="small" :bordered="false" :type="capabilities?.generation_model_configured ? 'success' : 'default'">{{ capabilities?.generation_model_configured ? '可用' : '未配置' }}</n-tag></div>
            <div><span>内容审核模型</span><n-tag size="small" :bordered="false" :type="capabilities?.review_model_configured ? 'success' : 'default'">{{ capabilities?.review_model_configured ? '可用' : '未配置' }}</n-tag></div>
          </div>
        </article>
      </section>
    </n-spin>
  </div>
</template>

<style scoped>
.metrics-alert {
  margin-bottom: 16px;
}

.metrics-summary {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  border: 1px solid var(--line);
  background: #fff;
}

.metrics-summary article {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  align-items: center;
  gap: 4px 8px;
  min-height: 104px;
  padding: 16px;
  border-right: 1px solid var(--line);
}

.metrics-summary article:last-child {
  border-right: 0;
}

.metrics-summary svg {
  grid-row: 1 / span 2;
  color: var(--primary);
}

.metrics-summary span {
  color: var(--muted);
  font-size: 10px;
}

.metrics-summary strong {
  color: var(--ink);
  font-size: 24px;
  line-height: 1.1;
}

.operations-band {
  display: grid;
  grid-template-columns: minmax(180px, 0.7fr) repeat(3, minmax(180px, 1fr));
  gap: 24px;
  margin-top: 18px;
  padding: 22px 24px;
  color: #fff;
  background: #17211c;
}

.operations-heading h2 {
  margin-top: 6px;
  font-size: 18px;
}

.operations-heading .eyebrow {
  color: #8dc6a6;
}

.operation-item {
  display: grid;
  align-content: center;
  gap: 8px;
}

.operation-item > div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.operation-item span,
.operation-item small {
  color: #b9c5bd;
  font-size: 10px;
}

.operation-item strong {
  color: #fff;
  font-size: 15px;
}

.metrics-detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(340px, 0.85fr);
  gap: 18px;
  margin-top: 18px;
}

.quality-panel > header,
.capability-panel > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 68px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--line);
}

.quality-panel header div,
.capability-panel header div {
  display: grid;
  gap: 3px;
}

.quality-panel header span,
.capability-panel header span {
  color: var(--muted);
  font-size: 10px;
}

.quality-panel h2,
.capability-panel h2 {
  color: var(--ink);
  font-size: 15px;
}

.quality-panel header svg,
.capability-panel header svg {
  color: var(--primary);
}

.quality-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.quality-list > div {
  display: grid;
  gap: 7px;
  min-height: 140px;
  padding: 20px;
  border-right: 1px solid var(--line);
}

.quality-list > div:last-child {
  border-right: 0;
}

.quality-list span,
.quality-list small {
  color: var(--muted);
  font-size: 10px;
}

.quality-list strong {
  color: var(--primary-strong);
  font-size: 27px;
}

.sample-note {
  padding: 11px 18px;
  color: var(--subtle);
  background: var(--surface-soft);
  border-top: 1px solid var(--line);
  font-size: 10px;
}

.capability-list {
  display: grid;
}

.capability-list > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 54px;
  padding: 9px 18px;
  border-bottom: 1px solid var(--line);
}

.capability-list > div:last-child {
  border-bottom: 0;
}

.capability-list span {
  color: #435048;
  font-size: 12px;
}

@media (max-width: 1180px) {
  .metrics-summary {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .metrics-summary article:nth-child(3) {
    border-right: 0;
  }

  .metrics-summary article:nth-child(-n + 3) {
    border-bottom: 1px solid var(--line);
  }

  .operations-band {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .operations-heading {
    grid-column: 1 / -1;
  }
}

@media (max-width: 820px) {
  .metrics-detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .metrics-summary,
  .operations-band,
  .quality-list {
    grid-template-columns: 1fr;
  }

  .metrics-summary article,
  .quality-list > div {
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }

  .operations-heading {
    grid-column: auto;
  }
}
</style>
