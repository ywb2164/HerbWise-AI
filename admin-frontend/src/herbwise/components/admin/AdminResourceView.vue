<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, type Component } from 'vue'
import {
  NButton,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NPagination,
  NSelect,
  NSpace,
  NSpin,
  NSwitch,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { Pencil, Plus, RefreshCw, TestTube2, Trash2 } from '../../icons'
import type { AdminResourceDefinition } from '../../admin/resources'
import PageHeader from '../PageHeader.vue'
import { api } from '../../services/api'
import type { AdminRecord, JsonRecord } from '../../types/api'
import { formatDate, formatProvider, getErrorMessage } from '../../utils/format'

const props = defineProps<{ definition: AdminResourceDefinition }>()
const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const saving = ref(false)
const rows = ref<AdminRecord[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')
const drawerOpen = ref(false)
const editing = ref<AdminRecord | null>(null)
const form = reactive<Record<string, unknown>>({})
const formError = ref('')

const filteredRows = computed(() => {
  const query = keyword.value.trim().toLocaleLowerCase()
  if (!query) return rows.value
  return rows.value.filter((row) => JSON.stringify(row).toLocaleLowerCase().includes(query))
})

function cellValue(row: AdminRecord, key: string): unknown {
  return row[key]
}

const displayAliases: Record<string, string> = {
  mock: '规则引擎',
  'mock-default': 'builtin-rules',
  'mock-llm': '规则引擎',
  demo_seed_data: '内置初始数据',
  demo_case_1: 'builtin_case_1',
  demo_case_2: 'builtin_case_2',
  demo_case_3: 'builtin_case_3',
  'Demo recognition case': '内置视觉辨识用例',
  'Demo resource_generation case': '内置资源生成用例',
  'Demo review case': '内置内容复核用例',
  recognition: '视觉辨识',
  resource_generation: '资源生成',
  review: '内容复核',
  'Load Profile': '画像加载智能体',
  'Recognize Image': '饮片识别智能体',
  'Vision Review': '视觉复核智能体',
  'Retrieve Knowledge': '药典检索智能体',
  'Judge Result': '纠错裁判智能体',
  'Generate Resources': '资源生成智能体',
  'Review Resources': '审核纠偏智能体',
  'Update Learning Path': '学习路径智能体',
  'Save Trace': '证据链记录智能体',
  'Default mock resource prompt': '默认资源生成提示词',
  'Generate a clearly labelled mock learning resource.': '生成经过明确标注的规则型学习资源。',
}

function normalizeDisplayValue(value: unknown): unknown {
  if (typeof value === 'string') return displayAliases[value] ?? value.replace(/\bmock\b/gi, '规则')
  if (Array.isArray(value)) return value.map(normalizeDisplayValue)
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, item]) => [key, normalizeDisplayValue(item)]),
    )
  }
  return value
}

function renderCell(row: AdminRecord, key: string, kind = 'text') {
  const value = cellValue(row, key)
  if (key === 'provider') return formatProvider(value as string | null | undefined)
  const displayValue = normalizeDisplayValue(value)
  if (kind === 'boolean') {
    return h(
      NTag,
      { size: 'small', bordered: false, type: value ? 'success' : 'default' },
      { default: () => (value ? '启用' : '停用') },
    )
  }
  if (kind === 'status') {
    const active = ['active', 'success', 'pass', 'approved', 'running'].includes(String(value))
    return h(
      NTag,
      { size: 'small', bordered: false, type: active ? 'success' : 'warning' },
      { default: () => String(value ?? '--') },
    )
  }
  if (kind === 'datetime') return formatDate(value as string | null | undefined)
  if (kind === 'json') {
    const text = displayValue == null ? '--' : JSON.stringify(displayValue)
    return h('span', { class: 'admin-json-cell', title: text }, text)
  }
  if (kind === 'code') return h('code', { class: 'admin-code-cell' }, String(displayValue ?? '--'))
  return String(displayValue ?? '--')
}

function iconButton(
  icon: Component,
  label: string,
  onClick: () => void,
  type: 'default' | 'error' | 'primary' = 'default',
) {
  return h(
    NButton,
    {
      quaternary: true,
      circle: true,
      size: 'small',
      type,
      title: label,
      'aria-label': label,
      onClick,
    },
    { icon: () => h(icon, { size: 16 }) },
  )
}

const columns = computed<DataTableColumns<AdminRecord>>(() => {
  const base = props.definition.columns.map((column) => ({
    key: column.key,
    title: column.title,
    width: column.width,
    ellipsis: { tooltip: true },
    render: (row: AdminRecord) => renderCell(row, column.key, column.kind),
  }))
  if (props.definition.readOnly) return base
  return [
    ...base,
    {
      key: 'actions',
      title: '操作',
      width: props.definition.testable ? 132 : 96,
      fixed: 'right' as const,
      render: (row: AdminRecord) =>
        h(
          NSpace,
          { size: 2, wrap: false },
          {
            default: () => [
              ...(props.definition.testable
                ? [iconButton(TestTube2, '测试连接', () => void testRecord(row), 'primary')]
                : []),
              iconButton(Pencil, '编辑', () => openEdit(row)),
              iconButton(Trash2, '删除', () => confirmDelete(row), 'error'),
            ],
          },
        ),
    },
  ]
})

const scrollWidth = computed(
  () => props.definition.columns.reduce((sum, column) => sum + (column.width || 150), 0) + 140,
)

async function load(): Promise<void> {
  loading.value = true
  try {
    const result = await api.listAdminRecords<AdminRecord>(
      props.definition.resource,
      page.value,
      pageSize.value,
    )
    rows.value = result.items
    total.value = result.total
  } catch (error) {
    message.error(getErrorMessage(error, `${props.definition.title}加载失败`))
  } finally {
    loading.value = false
  }
}

function cloneDefault(value: unknown): unknown {
  if (value === undefined) return ''
  if (value !== null && typeof value === 'object') return JSON.parse(JSON.stringify(value))
  return value
}

function resetForm(record: AdminRecord | null): void {
  Object.keys(form).forEach((key) => delete form[key])
  for (const field of props.definition.fields) {
    const value = record ? record[field.key] : cloneDefault(field.defaultValue)
    form[field.key] =
      field.control === 'json'
        ? JSON.stringify(value === '' || value == null ? field.defaultValue ?? {} : value, null, 2)
        : value ?? ''
  }
  formError.value = ''
}

function openCreate(): void {
  editing.value = null
  resetForm(null)
  drawerOpen.value = true
}

function openEdit(record: AdminRecord): void {
  editing.value = record
  resetForm(record)
  drawerOpen.value = true
}

function preparePayload(): JsonRecord | null {
  formError.value = ''
  const data: JsonRecord = {}
  for (const field of props.definition.fields) {
    const value = form[field.key]
    if (field.required && (value === '' || value === null || value === undefined)) {
      formError.value = `请填写${field.label}`
      return null
    }
    if (field.control === 'json') {
      try {
        data[field.key] = JSON.parse(String(value || 'null')) as unknown
      } catch {
        formError.value = `${field.label}不是有效 JSON`
        return null
      }
    } else if (value !== '' || editing.value) {
      data[field.key] = value === '' ? null : value
    }
  }
  return data
}

async function submit(): Promise<void> {
  const data = preparePayload()
  if (!data) return
  saving.value = true
  try {
    if (editing.value) {
      await api.updateAdminRecord(props.definition.resource, editing.value.id, data)
    } else {
      await api.createAdminRecord(props.definition.resource, data)
    }
    drawerOpen.value = false
    message.success(`${props.definition.singular}已保存`)
    await load()
  } catch (error) {
    formError.value = getErrorMessage(error, `${props.definition.singular}保存失败`)
  } finally {
    saving.value = false
  }
}

function confirmDelete(record: AdminRecord): void {
  dialog.warning({
    title: `删除${props.definition.singular}`,
    content: `确认删除记录 #${record.id}？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.deleteAdminRecord(props.definition.resource, record.id)
        message.success('记录已删除')
        await load()
      } catch (error) {
        message.error(getErrorMessage(error, '删除失败'))
      }
    },
  })
}

async function testRecord(record: AdminRecord): Promise<void> {
  try {
    const result = await api.testAdminModel(record.id)
    message.success(`连接成功，耗时 ${result.elapsed_ms} ms`)
  } catch (error) {
    message.error(getErrorMessage(error, '模型连接失败'))
  }
}

function changePage(value: number): void {
  page.value = value
  void load()
}

function changePageSize(value: number): void {
  pageSize.value = value
  page.value = 1
  void load()
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <PageHeader :title="definition.title" eyebrow="系统管理" :meta="`共 ${total} 条记录`">
      <template #actions>
        <n-button secondary aria-label="刷新" @click="load">
          <template #icon><RefreshCw :size="17" /></template>
          刷新
        </n-button>
        <n-button v-if="!definition.readOnly" type="primary" @click="openCreate">
          <template #icon><Plus :size="17" /></template>
          新建{{ definition.singular }}
        </n-button>
      </template>
    </PageHeader>

    <section class="admin-table-section">
      <div class="admin-table-toolbar">
        <n-input v-model:value="keyword" clearable placeholder="筛选当前页" class="admin-search" />
        <span>第 {{ page }} 页</span>
      </div>
      <n-spin :show="loading">
        <n-data-table
          remote
          :columns="columns"
          :data="filteredRows"
          :row-key="(row: AdminRecord) => row.id"
          :scroll-x="scrollWidth"
          :bordered="false"
          size="small"
        />
      </n-spin>
      <div class="admin-pagination">
        <n-pagination
          :page="page"
          :page-size="pageSize"
          :item-count="total"
          show-size-picker
          :page-sizes="[10, 20, 50]"
          @update:page="changePage"
          @update:page-size="changePageSize"
        />
      </div>
    </section>

    <n-drawer v-model:show="drawerOpen" placement="right" width="min(560px, 100vw)">
      <n-drawer-content :title="editing ? `编辑${definition.singular}` : `新建${definition.singular}`" closable>
        <n-form :model="form" label-placement="top">
          <n-form-item
            v-for="field in definition.fields"
            :key="field.key"
            :label="field.label"
            :required="field.required"
          >
            <n-switch
              v-if="field.control === 'switch'"
              :value="form[field.key] as boolean"
              @update:value="(value: boolean) => form[field.key] = value"
            />
            <n-input-number
              v-else-if="field.control === 'number'"
              :value="form[field.key] as number | null"
              :placeholder="field.placeholder"
              clearable
              class="full-control"
              @update:value="(value: number | null) => form[field.key] = value"
            />
            <n-select
              v-else-if="field.control === 'select'"
              :value="form[field.key] as string | number | null"
              :options="field.options || []"
              :placeholder="field.placeholder"
              class="full-control"
              @update:value="(value: string | number | null) => form[field.key] = value"
            />
            <n-input
              v-else
              :value="form[field.key] as string"
              :type="field.control === 'textarea' || field.control === 'json' ? 'textarea' : 'text'"
              :autosize="field.control === 'json' ? { minRows: 5, maxRows: 14 } : field.control === 'textarea' ? { minRows: 3, maxRows: 10 } : undefined"
              :placeholder="field.placeholder"
              class="full-control"
              @update:value="(value: string) => form[field.key] = value"
            />
          </n-form-item>
        </n-form>
        <p v-if="formError" class="admin-form-error">{{ formError }}</p>
        <template #footer>
          <div class="drawer-footer">
            <n-button @click="drawerOpen = false">取消</n-button>
            <n-button type="primary" :loading="saving" @click="submit">保存</n-button>
          </div>
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<style scoped>
.admin-page {
  width: 100%;
  max-width: 1680px;
  margin: 0 auto;
  padding: 24px 26px 40px;
}

.admin-table-section {
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 6px;
}

.admin-table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 58px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
}

.admin-table-toolbar > span {
  color: var(--muted);
  font-size: 12px;
}

.admin-search {
  width: min(320px, 100%);
}

.admin-pagination {
  display: flex;
  justify-content: flex-end;
  padding: 14px;
  border-top: 1px solid var(--line);
}

.full-control {
  width: 100%;
}

.admin-form-error {
  color: var(--danger);
  font-size: 12px;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  width: 100%;
}

:deep(.admin-code-cell) {
  color: #315b73;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 11px;
}

:deep(.admin-json-cell) {
  display: block;
  overflow: hidden;
  color: var(--muted);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 760px) {
  .admin-page {
    padding: 18px 12px 30px;
  }

  .admin-table-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .admin-search {
    width: 100%;
  }

  .admin-pagination {
    overflow-x: auto;
    justify-content: flex-start;
  }
}
</style>
