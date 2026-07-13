<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NEmpty, NSpin, NTabPane, NTabs, NTag, useMessage } from 'naive-ui'
import {
  Activity,
  Bot,
  CheckCircle2,
  Database,
  RefreshCw,
  ShieldCheck,
} from 'lucide-vue-next'
import MetricTile from '../components/MetricTile.vue'
import PageHeader from '../components/PageHeader.vue'
import SourceBadge from '../components/SourceBadge.vue'
import { api } from '../services/api'
import type {
  AgentLog,
  MetricsOverview,
  QualityMetric,
  TaskEvent,
  TraceRecord,
} from '../types/api'
import { formatDate, formatDuration, formatPercent, getErrorMessage } from '../utils/format'

const message = useMessage()
const loading = ref(false)
const detailLoading = ref(false)
const metrics = ref<MetricsOverview | null>(null)
const qualityMetrics = ref<QualityMetric[]>([])
const traces = ref<TraceRecord[]>([])
const selectedTrace = ref<TraceRecord | null>(null)
const events = ref<TaskEvent[]>([])
const logs = ref<AgentLog[]>([])

const metricLabels: Record<string, string> = {
  hallucination: '幻觉率',
  adaptation: '个性化适配度',
  coverage: '知识覆盖率',
}

const successfulRate = computed(() => {
  if (!metrics.value?.task_count) return '--'
  return formatPercent(metrics.value.successful_task_count / metrics.value.task_count, 0)
})

const traceCandidate = computed(() => selectedTrace.value?.trace_data.recognition_result?.candidate || null)
const traceEvidenceCount = computed(() => selectedTrace.value?.trace_data.knowledge_evidence?.length || 0)
const traceResourceCount = computed(() => selectedTrace.value?.trace_data.generated_resources?.length || 0)

async function selectTrace(item: TraceRecord): Promise<void> {
  selectedTrace.value = item
  events.value = []
  logs.value = []
  detailLoading.value = true
  const [eventResult, logResult] = await Promise.allSettled([
    api.getTaskEvents(item.task_id),
    api.getTaskLogs(item.task_id),
  ])
  if (eventResult.status === 'fulfilled') events.value = eventResult.value
  if (logResult.status === 'fulfilled') logs.value = logResult.value
  detailLoading.value = false
}

async function loadData(): Promise<void> {
  loading.value = true
  const [overviewResult, hallucinationResult, adaptationResult, coverageResult, traceResult] =
    await Promise.allSettled([
      api.getMetricsOverview(),
      api.getQualityMetric('hallucination'),
      api.getQualityMetric('adaptation'),
      api.getQualityMetric('coverage'),
      api.listTraces(),
    ])

  if (overviewResult.status === 'fulfilled') metrics.value = overviewResult.value
  qualityMetrics.value = [hallucinationResult, adaptationResult, coverageResult]
    .filter((item): item is PromiseFulfilledResult<QualityMetric> => item.status === 'fulfilled')
    .map((item) => item.value)

  if (traceResult.status === 'fulfilled') {
    traces.value = traceResult.value.items
    const lastTaskId = localStorage.getItem('herbwise.last_task_id')
    const preferred = traces.value.find((item) => item.task_id === lastTaskId) || traces.value[0]
    if (preferred) await selectTrace(preferred)
  } else {
    message.error(getErrorMessage(traceResult.reason, '追踪记录加载失败'))
  }
  loading.value = false
}

onMounted(loadData)
</script>

<template>
  <div class="page traces-page">
    <PageHeader title="运行追踪" :meta="`${traces.length} 条 Trace`">
      <template #actions>
        <n-button secondary :loading="loading" @click="loadData">
          刷新追踪
          <template #icon><RefreshCw :size="17" /></template>
        </n-button>
      </template>
    </PageHeader>

    <section class="metric-grid">
      <MetricTile label="智能体任务" :value="metrics?.task_count ?? '--'" tone="green">
        <template #icon><Bot :size="21" /></template>
      </MetricTile>
      <MetricTile label="任务成功率" :value="successfulRate" tone="blue">
        <template #icon><CheckCircle2 :size="21" /></template>
      </MetricTile>
      <MetricTile label="知识来源" :value="metrics?.knowledge_source_count ?? '--'" tone="neutral">
        <template #icon><Database :size="21" /></template>
      </MetricTile>
      <MetricTile label="资源审核" :value="metrics?.review_count ?? '--'" tone="amber">
        <template #icon><ShieldCheck :size="21" /></template>
      </MetricTile>
    </section>

    <section class="quality-band">
      <div class="quality-heading">
        <Activity :size="20" />
        <div>
          <strong>质量评估指标</strong>
          <span>当前版本为内部评估口径</span>
        </div>
        <SourceBadge source="mock" :official="false" />
      </div>
      <div v-for="item in qualityMetrics" :key="item.metric_code" class="quality-item">
        <span>{{ metricLabels[item.metric_code] || item.metric_code }}</span>
        <strong>{{ item.metric_value === null ? '待评测' : formatPercent(item.metric_value, 1) }}</strong>
        <small>{{ item.sample_count }} 个样本</small>
      </div>
    </section>

    <n-spin :show="loading">
      <section class="trace-workspace">
        <div class="surface trace-list-panel">
          <div class="surface-header">
            <h2 class="surface-title">Trace 记录</h2>
            <span class="trace-count">{{ traces.length }}</span>
          </div>
          <div v-if="traces.length" class="trace-list">
            <button
              v-for="item in traces"
              :key="item.trace_id"
              type="button"
              class="trace-row"
              :class="{ active: selectedTrace?.trace_id === item.trace_id }"
              @click="selectTrace(item)"
            >
              <span class="trace-status-dot" />
              <div>
                <strong>{{ item.trace_id }}</strong>
                <span class="mono">{{ item.task_id }}</span>
                <small>{{ formatDate(item.created_at) }}</small>
              </div>
            </button>
          </div>
          <div v-else class="empty-state"><n-empty description="暂无 Trace 记录" /></div>
        </div>

        <div class="surface trace-detail-panel">
          <template v-if="selectedTrace">
            <div class="trace-detail-heading">
              <div>
                <span class="eyebrow">{{ selectedTrace.trace_id }}</span>
                <h2>{{ traceCandidate?.herb_name || '智能体任务证据链' }}</h2>
                <span class="mono">{{ selectedTrace.task_id }}</span>
              </div>
              <div>
                <SourceBadge :source="String(selectedTrace.trace_data.judge_result?.data_source || 'mock')" :official="false" />
                <n-tag type="success" :bordered="false">{{ String(selectedTrace.trace_data.judge_result?.status || 'success') }}</n-tag>
              </div>
            </div>

            <n-spin :show="detailLoading" size="small">
              <n-tabs type="line" animated class="trace-tabs">
                <n-tab-pane name="events" :tab="`任务事件 (${events.length})`">
                  <div v-if="events.length" class="event-timeline">
                    <div v-for="item in events" :key="`${item.node}-${item.timestamp}-${item.event}`" class="event-row">
                      <span class="event-line-dot" :class="item.status" />
                      <div class="event-main">
                        <div>
                          <strong>{{ item.node }}</strong>
                          <n-tag size="small" :type="item.status === 'failed' ? 'error' : 'success'" :bordered="false">
                            {{ item.event }}
                          </n-tag>
                        </div>
                        <p>{{ item.summary }}</p>
                      </div>
                      <div class="event-time">
                        <span>{{ formatDuration(item.elapsed_ms) }}</span>
                        <small>{{ formatDate(item.timestamp) }}</small>
                      </div>
                    </div>
                  </div>
                  <div v-else class="empty-state"><n-empty description="暂无任务事件" /></div>
                </n-tab-pane>

                <n-tab-pane name="logs" :tab="`Agent 日志 (${logs.length})`">
                  <div v-if="logs.length" class="table-scroll">
                    <table class="data-table log-table">
                      <thead>
                        <tr>
                          <th>节点</th>
                          <th>Provider</th>
                          <th>模型</th>
                          <th>耗时</th>
                          <th>输出摘要</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(item, index) in logs" :key="`${item.node}-${index}`">
                          <td>{{ item.node }}</td>
                          <td><SourceBadge :source="item.provider || 'mock'" :official="item.provider !== 'mock'" /></td>
                          <td>{{ item.model_name || '--' }}</td>
                          <td>{{ formatDuration(item.elapsed_ms) }}</td>
                          <td>{{ item.output_summary || '--' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div v-else class="empty-state"><n-empty description="暂无 Agent 日志" /></div>
                </n-tab-pane>

                <n-tab-pane name="evidence" tab="证据摘要">
                  <div class="trace-summary-grid">
                    <div>
                      <span>识别结果</span>
                      <strong>{{ traceCandidate?.herb_name || '--' }}</strong>
                      <small>{{ formatPercent(traceCandidate?.confidence, 1) }}</small>
                    </div>
                    <div>
                      <span>知识证据</span>
                      <strong>{{ traceEvidenceCount }}</strong>
                      <small>条</small>
                    </div>
                    <div>
                      <span>生成资源</span>
                      <strong>{{ traceResourceCount }}</strong>
                      <small>份</small>
                    </div>
                    <div>
                      <span>学习路径</span>
                      <strong>V{{ selectedTrace.trace_data.path_update?.version || '--' }}</strong>
                      <small>{{ selectedTrace.trace_data.path_update?.current_stage || '--' }}</small>
                    </div>
                  </div>

                  <dl class="trace-facts">
                    <div><dt>识别记录</dt><dd class="mono">{{ selectedTrace.trace_data.recognition_id || '--' }}</dd></div>
                    <div><dt>检索记录</dt><dd class="mono">{{ selectedTrace.trace_data.retrieval_id || '--' }}</dd></div>
                    <div><dt>资源审核</dt><dd>{{ selectedTrace.trace_data.review_result?.status || '--' }}</dd></div>
                    <div><dt>人工复核</dt><dd>{{ selectedTrace.trace_data.judge_result?.manual_review_required ? '需要' : '不需要' }}</dd></div>
                  </dl>

                  <details class="raw-trace">
                    <summary>完整 Trace JSON</summary>
                    <pre>{{ JSON.stringify(selectedTrace.trace_data, null, 2) }}</pre>
                  </details>
                </n-tab-pane>
              </n-tabs>
            </n-spin>
          </template>
          <div v-else class="empty-state"><n-empty description="请选择 Trace 记录" /></div>
        </div>
      </section>
    </n-spin>
  </div>
</template>

<style scoped>
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.quality-band {
  display: grid;
  grid-template-columns: minmax(280px, 1.5fr) repeat(3, minmax(130px, 0.7fr));
  margin-top: 18px;
  background: #fff;
  border: 1px solid var(--line);
}

.quality-heading,
.quality-item {
  min-height: 82px;
  padding: 15px 18px;
  border-right: 1px solid var(--line);
}

.quality-heading {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
}

.quality-heading svg {
  color: var(--blue);
}

.quality-heading > div {
  display: grid;
}

.quality-heading strong {
  color: var(--ink);
  font-size: 13px;
}

.quality-heading span {
  color: var(--muted);
  font-size: 10px;
}

.quality-item {
  display: grid;
  align-content: center;
  gap: 1px;
}

.quality-item:last-child {
  border-right: 0;
}

.quality-item span,
.quality-item small {
  color: var(--muted);
  font-size: 10px;
}

.quality-item strong {
  color: var(--ink);
  font-size: 17px;
}

.trace-workspace {
  display: grid;
  grid-template-columns: 330px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
  margin-top: 20px;
}

.trace-list-panel {
  max-height: 760px;
  overflow: hidden;
}

.trace-count {
  color: var(--muted);
  font-size: 11px;
}

.trace-list {
  max-height: 700px;
  overflow-y: auto;
}

.trace-row {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr);
  align-items: start;
  gap: 10px;
  width: 100%;
  min-height: 78px;
  padding: 14px 16px;
  color: var(--ink);
  background: #fff;
  border: 0;
  border-bottom: 1px solid var(--line);
  cursor: pointer;
  text-align: left;
}

.trace-row:hover {
  background: #f7faf8;
}

.trace-row.active {
  background: var(--primary-soft);
  box-shadow: inset 3px 0 var(--primary);
}

.trace-status-dot {
  width: 7px;
  height: 7px;
  margin-top: 5px;
  background: var(--primary);
  border-radius: 50%;
}

.trace-row > div {
  display: grid;
  min-width: 0;
}

.trace-row strong,
.trace-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trace-row strong {
  color: var(--ink);
  font-size: 12px;
}

.trace-row span,
.trace-row small {
  color: var(--muted);
  font-size: 9px;
}

.trace-detail-panel {
  min-height: 610px;
}

.trace-detail-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 104px;
  padding: 20px 22px;
  background: #f2f7f4;
  border-bottom: 1px solid var(--line);
}

.trace-detail-heading h2 {
  margin: 4px 0 2px;
  color: var(--ink);
  font-size: 20px;
  font-weight: 700;
}

.trace-detail-heading .mono {
  color: var(--muted);
  font-size: 9px;
}

.trace-detail-heading > div:last-child {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.trace-tabs {
  padding: 0 18px 18px;
}

.event-timeline {
  display: grid;
  padding: 2px 0;
}

.event-row {
  position: relative;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) 110px;
  gap: 10px;
  min-height: 64px;
  padding: 11px 0;
  border-bottom: 1px solid var(--line);
}

.event-line-dot {
  width: 9px;
  height: 9px;
  margin-top: 5px;
  background: var(--primary);
  border: 2px solid #d8e9df;
  border-radius: 50%;
}

.event-line-dot.failed {
  background: var(--danger);
  border-color: #f3d8d4;
}

.event-main {
  min-width: 0;
}

.event-main > div {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.event-main strong {
  color: var(--ink);
  font-size: 12px;
}

.event-main p {
  margin-top: 3px;
  color: var(--muted);
  font-size: 10px;
  line-height: 1.5;
}

.event-time {
  display: grid;
  align-content: start;
  justify-items: end;
  color: var(--muted);
  font-size: 10px;
}

.event-time small {
  color: var(--subtle);
  font-size: 9px;
}

.log-table {
  min-width: 760px;
}

.trace-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border: 1px solid var(--line);
}

.trace-summary-grid > div {
  display: grid;
  gap: 2px;
  min-height: 94px;
  padding: 16px;
  border-right: 1px solid var(--line);
}

.trace-summary-grid > div:last-child {
  border-right: 0;
}

.trace-summary-grid span,
.trace-summary-grid small {
  color: var(--muted);
  font-size: 10px;
}

.trace-summary-grid strong {
  overflow: hidden;
  color: var(--ink);
  font-size: 19px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trace-facts {
  display: grid;
  gap: 8px;
  margin: 18px 0;
  padding: 16px 0;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}

.trace-facts > div {
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
  gap: 12px;
}

.trace-facts dt,
.trace-facts dd {
  margin: 0;
  font-size: 11px;
}

.trace-facts dt {
  color: var(--muted);
}

.trace-facts dd {
  color: var(--ink);
  overflow-wrap: anywhere;
}

.raw-trace {
  color: var(--ink);
  font-size: 12px;
}

.raw-trace summary {
  cursor: pointer;
  font-weight: 650;
}

.raw-trace pre {
  max-height: 360px;
  margin: 12px 0 0;
  padding: 14px;
  overflow: auto;
  color: #38463e;
  background: #f5f7f5;
  border: 1px solid var(--line);
  border-radius: 6px;
  font-size: 10px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

@media (max-width: 1180px) {
  .metric-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .quality-band {
    grid-template-columns: repeat(3, 1fr);
  }

  .quality-heading {
    grid-column: 1 / -1;
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }
}

@media (max-width: 920px) {
  .trace-workspace {
    grid-template-columns: 1fr;
  }

  .trace-list-panel {
    max-height: 330px;
  }

  .trace-list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    max-height: 270px;
  }
}

@media (max-width: 620px) {
  .metric-grid,
  .quality-band,
  .trace-list,
  .trace-summary-grid {
    grid-template-columns: 1fr;
  }

  .quality-heading {
    grid-column: auto;
  }

  .quality-item,
  .trace-summary-grid > div {
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }

  .trace-detail-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .event-row {
    grid-template-columns: 16px minmax(0, 1fr);
  }

  .event-time {
    grid-column: 2;
    justify-items: start;
  }
}
</style>
