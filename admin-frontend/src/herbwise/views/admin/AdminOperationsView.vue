<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import {
  NButton,
  NDataTable,
  NSpin,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { RefreshCw } from '../../icons'
import PageHeader from '../../components/PageHeader.vue'
import { api } from '../../services/api'
import type { AdminRecord } from '../../types/api'
import { formatDate, formatDuration, formatProvider, formatRuntimeText, getErrorMessage } from '../../utils/format'

interface AdminTaskRecord extends AdminRecord {
  task_id: string
  learner_id: string
  task_type: string
  status: string
  current_node?: string | null
  progress: number
  error_message?: string | null
  created_at?: string
}

interface AdminAgentLog extends AdminRecord {
  task_id: string
  node_name: string
  provider: string
  model_name?: string | null
  status: string
  elapsed_ms?: number | null
  output_summary?: string | null
  error_message?: string | null
  created_at?: string
}

const message = useMessage()
const loading = ref(false)
const tasks = ref<AdminTaskRecord[]>([])
const logs = ref<AdminAgentLog[]>([])

function statusTag(value: string) {
  const type = value === 'success' ? 'success' : value === 'failed' ? 'error' : 'warning'
  return h(NTag, { size: 'small', bordered: false, type }, { default: () => value })
}

const taskColumns: DataTableColumns<AdminTaskRecord> = [
  {
    key: 'task_id',
    title: '任务 ID',
    width: 210,
    ellipsis: { tooltip: true },
    render: (row) => formatRuntimeText(row.task_id),
  },
  { key: 'learner_id', title: '学习者', width: 120 },
  { key: 'task_type', title: '任务类型', width: 130 },
  { key: 'current_node', title: '当前节点', width: 150, render: (row) => row.current_node || '--' },
  { key: 'progress', title: '进度', width: 90, render: (row) => `${row.progress}%` },
  { key: 'status', title: '状态', width: 100, render: (row) => statusTag(row.status) },
  { key: 'created_at', title: '创建时间', width: 170, render: (row) => formatDate(row.created_at) },
  { key: 'error_message', title: '错误', width: 240, ellipsis: { tooltip: true }, render: (row) => row.error_message || '--' },
]

const logColumns: DataTableColumns<AdminAgentLog> = [
  {
    key: 'task_id',
    title: '任务 ID',
    width: 200,
    ellipsis: { tooltip: true },
    render: (row) => formatRuntimeText(row.task_id),
  },
  { key: 'node_name', title: '节点', width: 170 },
  { key: 'provider', title: '服务', width: 150, render: (row) => formatProvider(row.provider) },
  { key: 'model_name', title: '模型', width: 180, ellipsis: { tooltip: true }, render: (row) => row.model_name || '--' },
  { key: 'status', title: '状态', width: 100, render: (row) => statusTag(row.status) },
  { key: 'elapsed_ms', title: '耗时', width: 100, render: (row) => formatDuration(row.elapsed_ms) },
  {
    key: 'output_summary',
    title: '输出摘要',
    width: 300,
    ellipsis: { tooltip: true },
    render: (row) => formatRuntimeText(row.output_summary),
  },
  { key: 'created_at', title: '记录时间', width: 170, render: (row) => formatDate(row.created_at) },
]

async function load(): Promise<void> {
  loading.value = true
  try {
    const [taskPage, logPage] = await Promise.all([
      api.listAdminRecords<AdminTaskRecord>('task-records', 1, 50),
      api.listAdminRecords<AdminAgentLog>('agent-logs', 1, 50),
    ])
    tasks.value = taskPage.items
    logs.value = logPage.items
  } catch (error) {
    message.error(getErrorMessage(error, '运行记录加载失败'))
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="operations-page">
    <PageHeader title="运行日志" eyebrow="系统运维" :meta="`${tasks.length} 个任务 · ${logs.length} 条节点记录`">
      <template #actions>
        <n-button secondary @click="load">
          <template #icon><RefreshCw :size="17" /></template>
          刷新
        </n-button>
      </template>
    </PageHeader>

    <n-spin :show="loading">
      <section class="operations-table">
        <n-tabs type="line" animated pane-class="operations-pane">
          <n-tab-pane name="tasks" tab="任务记录">
            <n-data-table :columns="taskColumns" :data="tasks" :scroll-x="1320" :bordered="false" size="small" />
          </n-tab-pane>
          <n-tab-pane name="logs" tab="节点日志">
            <n-data-table :columns="logColumns" :data="logs" :scroll-x="1370" :bordered="false" size="small" />
          </n-tab-pane>
        </n-tabs>
      </section>
    </n-spin>
  </div>
</template>

<style scoped>
.operations-page {
  width: 100%;
  max-width: 1680px;
  margin: 0 auto;
  padding: 24px 26px 40px;
}

.operations-table {
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
}

.operations-table :deep(.n-tabs-nav) {
  padding: 0 16px;
}

.operations-table :deep(.operations-pane) {
  padding: 0;
}

@media (max-width: 760px) {
  .operations-page {
    padding: 18px 12px 30px;
  }
}
</style>
