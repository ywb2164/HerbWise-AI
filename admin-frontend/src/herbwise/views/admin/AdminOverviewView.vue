<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NEmpty, NProgress, NSpin, NTag, useMessage } from 'naive-ui'
import {
  Bot,
  BrainCircuit,
  CheckCircle2,
  Database,
  FileStack,
  ListChecks,
  RefreshCw,
} from '../../icons'
import MetricTile from '../../components/MetricTile.vue'
import PageHeader from '../../components/PageHeader.vue'
import { api } from '../../services/api'
import type { AdminRecord, MetricsOverview } from '../../types/api'
import { formatDate, formatDuration, formatProvider, getErrorMessage } from '../../utils/format'

interface OverviewTask extends AdminRecord {
  task_id: string
  learner_id: string
  task_type: string
  status: string
  progress: number
  created_at?: string
}

interface OverviewLog extends AdminRecord {
  node_name: string
  provider: string
  model_name?: string | null
  status: string
  elapsed_ms?: number | null
  created_at?: string
}

const router = useRouter()
const message = useMessage()
const loading = ref(false)
const metrics = ref<MetricsOverview | null>(null)
const tasks = ref<OverviewTask[]>([])
const logs = ref<OverviewLog[]>([])
const modelCount = ref(0)
const agentCount = ref(0)

const successRate = computed(() => {
  if (!metrics.value?.task_count) return 0
  return Math.round((metrics.value.successful_task_count / metrics.value.task_count) * 100)
})

async function load(): Promise<void> {
  loading.value = true
  try {
    const [overview, taskPage, logPage, modelPage, agentPage] = await Promise.all([
      api.getMetricsOverview(),
      api.listAdminRecords<OverviewTask>('task-records', 1, 6),
      api.listAdminRecords<OverviewLog>('agent-logs', 1, 8),
      api.listAdminRecords<AdminRecord>('model-configs', 1, 1),
      api.listAdminRecords<AdminRecord>('agent-configs', 1, 1),
    ])
    metrics.value = overview
    tasks.value = taskPage.items
    logs.value = logPage.items
    modelCount.value = modelPage.total
    agentCount.value = agentPage.total
  } catch (error) {
    message.error(getErrorMessage(error, '管理总览加载失败'))
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="overview-page">
    <PageHeader title="管理总览" eyebrow="本草智策" meta="业务、智能体与模型运行状态">
      <template #actions>
        <n-button secondary @click="load">
          <template #icon><RefreshCw :size="17" /></template>
          刷新
        </n-button>
      </template>
    </PageHeader>

    <n-spin :show="loading">
      <section class="overview-metrics">
        <MetricTile label="学习者" :value="metrics?.learner_count || 0" tone="green">
          <template #icon><BrainCircuit :size="21" /></template>
        </MetricTile>
        <MetricTile label="药材知识" :value="metrics?.medicine_count || 0" tone="blue">
          <template #icon><Database :size="21" /></template>
        </MetricTile>
        <MetricTile label="智能体任务" :value="metrics?.task_count || 0" :note="`成功率 ${successRate}%`" tone="amber">
          <template #icon><ListChecks :size="21" /></template>
        </MetricTile>
        <MetricTile label="学习资源" :value="metrics?.resource_count || 0" :note="`${metrics?.approved_resource_count || 0} 条已通过`">
          <template #icon><FileStack :size="21" /></template>
        </MetricTile>
        <MetricTile label="模型配置" :value="modelCount" tone="blue">
          <template #icon><Bot :size="21" /></template>
        </MetricTile>
        <MetricTile label="智能体配置" :value="agentCount" tone="green">
          <template #icon><CheckCircle2 :size="21" /></template>
        </MetricTile>
      </section>

      <section class="overview-grid">
        <div class="overview-surface">
          <div class="overview-surface-header">
            <div><span>任务队列</span><strong>最近运行</strong></div>
            <n-button text type="primary" @click="router.push('/function/request')">全部记录</n-button>
          </div>
          <div v-if="tasks.length" class="task-list">
            <div v-for="task in tasks" :key="task.id" class="task-row">
              <div class="task-state" :class="task.status" />
              <div class="task-copy">
                <strong>{{ task.task_type }}</strong>
                <span>{{ task.learner_id }} · {{ formatDate(task.created_at) }}</span>
              </div>
              <div class="task-progress">
                <span>{{ task.progress }}%</span>
                <n-progress type="line" :percentage="task.progress" :height="5" :show-indicator="false" />
              </div>
              <n-tag size="small" :bordered="false" :type="task.status === 'success' ? 'success' : task.status === 'failed' ? 'error' : 'warning'">
                {{ task.status }}
              </n-tag>
            </div>
          </div>
          <n-empty v-else description="暂无任务记录" class="overview-empty" />
        </div>

        <div class="overview-surface">
          <div class="overview-surface-header">
            <div><span>执行节点</span><strong>智能体活动</strong></div>
            <n-button text type="primary" @click="router.push('/alova/scenes')">配置管理</n-button>
          </div>
          <div v-if="logs.length" class="log-list">
            <div v-for="log in logs" :key="log.id" class="log-row">
              <span class="log-index">{{ String(log.id).padStart(2, '0') }}</span>
              <div>
                <strong>{{ log.node_name }}</strong>
                <small>{{ formatProvider(log.provider) }} · {{ log.model_name || '规则引擎' }}</small>
              </div>
              <span>{{ formatDuration(log.elapsed_ms) }}</span>
              <n-tag size="small" :bordered="false" :type="log.status === 'success' ? 'success' : 'warning'">
                {{ log.status }}
              </n-tag>
            </div>
          </div>
          <n-empty v-else description="暂无节点记录" class="overview-empty" />
        </div>
      </section>
    </n-spin>
  </div>
</template>

<style scoped>
.overview-page {
  width: 100%;
  max-width: 1680px;
  margin: 0 auto;
  padding: 24px 26px 40px;
}

.overview-metrics {
  display: grid;
  grid-template-columns: repeat(6, minmax(160px, 1fr));
  gap: 14px;
}

.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(380px, 0.85fr);
  gap: 16px;
  margin-top: 18px;
}

.overview-surface {
  min-width: 0;
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
}

.overview-surface-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 64px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
}

.overview-surface-header > div {
  display: grid;
}

.overview-surface-header span {
  color: var(--muted);
  font-size: 11px;
}

.overview-surface-header strong {
  color: var(--ink);
  font-size: 15px;
}

.task-list,
.log-list {
  display: grid;
}

.task-row {
  display: grid;
  grid-template-columns: 8px minmax(150px, 1fr) minmax(120px, 0.7fr) 72px;
  align-items: center;
  gap: 12px;
  min-height: 67px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--line);
}

.task-row:last-child,
.log-row:last-child {
  border-bottom: 0;
}

.task-state {
  width: 7px;
  height: 7px;
  background: var(--amber);
  border-radius: 50%;
}

.task-state.success { background: var(--primary); }
.task-state.failed { background: var(--danger); }

.task-copy,
.log-row > div {
  display: grid;
  min-width: 0;
}

.task-copy strong,
.log-row strong {
  overflow: hidden;
  color: var(--ink);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-copy span,
.log-row small {
  overflow: hidden;
  color: var(--muted);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-progress {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 10px;
}

.log-row {
  display: grid;
  grid-template-columns: 30px minmax(140px, 1fr) 64px 72px;
  align-items: center;
  gap: 10px;
  min-height: 50px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--line);
}

.log-index,
.log-row > span:nth-child(3) {
  color: var(--muted);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 10px;
}

.overview-empty {
  min-height: 280px;
}

@media (max-width: 1420px) {
  .overview-metrics { grid-template-columns: repeat(3, minmax(180px, 1fr)); }
}

@media (max-width: 1000px) {
  .overview-grid { grid-template-columns: 1fr; }
}

@media (max-width: 760px) {
  .overview-page { padding: 18px 12px 30px; }
  .overview-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .task-row { grid-template-columns: 8px minmax(0, 1fr) 68px; }
  .task-progress { display: none; }
}

@media (max-width: 460px) {
  .overview-metrics { grid-template-columns: 1fr; }
  .log-row { grid-template-columns: 24px minmax(0, 1fr) 68px; }
  .log-row > span:nth-child(3) { display: none; }
}
</style>
