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
  success: '已完成',
  failed: '失败',
  running: '运行中',
  pending: '等待中',
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
  cloud_vision: '云端多模态',
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
  'Neither vision provider returned a usable candidate': '视觉模型未返回可用的药材候选。',
  'Qwen provider unavailable or returned no candidate': '本地 YOLO 已完成识别，当前未启用云端视觉复核。',
  'Local provider unavailable or returned no candidate': '云端视觉已完成识别，本地 YOLO 未返回候选。',
  'mock node completed': '规则节点执行完成',
  'load_profile completed': '画像加载完成',
  'recognize_image completed': '图像识别完成',
  'vision_review completed': '视觉复核完成',
  'retrieve_knowledge completed': '知识检索完成',
  'judge_result completed': '纠错裁判完成',
  'generate_resources completed': '资源生成完成',
  'review_resources completed': '内容审核完成',
  'update_learning_path completed': '路径更新完成',
  'save_trace completed': '证据归档完成',
}

export function formatRuntimeText(value?: string | null, fallback = '--'): string {
  if (!value) return fallback
  return runtimeTextLabels[value] || value
}

const recommendationLabels: Record<string, string> = {
  'Complete a foundation review task': '完成基础知识复习任务',
  'Complete a consolidation task': '完成相似饮片巩固任务',
  'Complete a quality-control review task': '完成质量控制复核任务',
}

export function formatRecommendation(value?: string | null): string {
  if (!value) return '完成个性化巩固任务'
  return recommendationLabels[value] || value
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

const resourceReferenceErrorLabels: Record<string, string> = {
  PLAN_NOT_FOUND: '学习计划已更新，请刷新后查看最新安排。',
  PLAN_ITEM_NOT_FOUND: '原学习任务已更新，请刷新最新学习计划。',
  PLAN_ITEM_FORBIDDEN: '该学习任务不属于当前学习档案，请刷新后重试。',
  TASK_NOT_FOUND: '学习任务已更新，请刷新今日学习。',
  PLAN_ITEM_TASK_MISMATCH: '学习任务关联已更新，请刷新后重新开始。',
}

export function getApiErrorCode(error: unknown): string | undefined {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { error_code?: string } | undefined)?.error_code
  }
  if (error instanceof Error && 'errorCode' in error) return (error as Error & { errorCode?: string }).errorCode
  return undefined
}

export function getErrorMessage(error: unknown, fallback = '请求失败'): string {
  const errorCode = getApiErrorCode(error)
  if (errorCode && resourceReferenceErrorLabels[errorCode]) return resourceReferenceErrorLabels[errorCode]
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as { message?: string; detail?: string } | undefined
    return payload?.message || payload?.detail || error.message || fallback
  }
  if (error instanceof Error) return error.message
  return fallback
}

export function isHttpStatus(error: unknown, status: number): boolean {
  return axios.isAxiosError(error) && error.response?.status === status
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
