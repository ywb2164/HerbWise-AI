import axios from 'axios'

export const dimensionLabels: Record<string, string> = {
  basic_knowledge: '基础知识',
  character_identification: '性状辨识',
  similar_medicine: '近似药区分',
  pharmacopoeia_rules: '药典规范',
  clinical_quality_control: '临床质量控制',
  practical_review: '实践复核',
}

export const levelLabels: Record<string, string> = {
  weak: '待加强',
  basic: '基础',
  proficient: '熟练',
  excellent: '优秀',
  foundation: '基础巩固',
  consolidation: '进阶巩固',
  advanced: '高阶实践',
}

export const taskTypeLabels: Record<string, string> = {
  lecture: '专题讲义',
  guide: '学习指南',
  quiz: '巩固测验',
  comparison_card: '近似药对比卡',
  review_report: '复习报告',
  learning_report: '学习报告',
  simplified_explanation: '简化讲解',
  quality_control_task: '质量控制任务',
  low_confidence_review: '低置信度复核',
}

export const resourceStatusLabels: Record<string, string> = {
  generating: '生成中',
  generated: '已生成',
  reviewing: '审核中',
  approved: '已通过',
  needs_revision: '待修订',
  rejected: '已驳回',
  archived: '已归档',
  pass: '通过',
  reject: '驳回',
  manual_review: '人工复核',
}

export function formatResourceStatus(value?: string | null): string {
  if (!value) return '--'
  return resourceStatusLabels[value.toLocaleLowerCase()] || value
}

export const providerLabels: Record<string, string> = {
  mock: '规则引擎',
  openai: 'OpenAI 兼容',
  openai_compatible: 'OpenAI 兼容',
  anthropic: 'Anthropic 兼容',
  anthropic_compatible: 'Anthropic 兼容',
  qwen: '通义千问',
  local: '本地模型',
  hybrid: '混合服务',
}

export function formatProvider(value?: string | null): string {
  if (!value) return '--'
  return providerLabels[value.toLocaleLowerCase()] || value
}

const runtimeTextLabels: Record<string, string> = {
  mock: '规则一致',
  'Mock vision result': '规则视觉结果',
  'mock node completed': '规则节点执行完成',
  task_seed_demo: 'task_seed_initial',
}

export function formatRuntimeText(value?: string | null, fallback = '--'): string {
  if (!value) return fallback
  return runtimeTextLabels[value] || value
}

export function formatDate(value?: string | null): string {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

export function formatPercent(value?: number | null, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  const normalized = value <= 1 ? value * 100 : value
  return `${normalized.toFixed(digits)}%`
}

export function formatDuration(value?: number | null): string {
  if (value === null || value === undefined) return '--'
  return value < 1000 ? `${Math.round(value)} ms` : `${(value / 1000).toFixed(2)} s`
}

export function getErrorMessage(error: unknown, fallback = '请求失败'): string {
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as { message?: string; detail?: string } | undefined
    return payload?.message || payload?.detail || error.message || fallback
  }
  if (error instanceof Error) return error.message
  return fallback
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
