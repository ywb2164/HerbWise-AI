const dimensions: Record<string, string> = {
  basic_knowledge: '基础知识',
  character_identification: '性状辨识',
  trait_identification: '性状辨识',
  similar_medicine: '相似药材辨析',
  pharmacopoeia_rules: '药典规范',
  clinical_quality_control: '质量控制',
  practical_review: '实践复核',
}

const difficulties: Record<string, string> = {
  basic: '基础', intermediate: '进阶', advanced: '提高',
}

const taskStatuses: Record<string, string> = {
  pending: '待开始', in_progress: '进行中', completed: '已完成', submitted: '已提交', expired: '已过期', cancelled: '已取消',
}

const resourceTypes: Record<string, string> = {
  practice_guide: '练习指导', error_explanation: '错题讲解', knowledge_card: '知识卡片', comparison_card: '对比学习卡', review_summary: '复习总结', quality_control_case: '质量控制案例', professional_guide: '专业学习指导', detailed_comparison: '详细对比',
}

const planStages: Record<string, string> = {
  adaptive_plan: '个性化学习', consolidation: '巩固提升', foundation: '基础巩固', advanced: '进阶提升',
}

const legacyText: Record<string, string> = {
  'Basic Knowledge practice': '基础知识巩固练习',
  'Strengthen basic knowledge through targeted practice.': '通过针对性练习巩固基础知识。',
  'Focus on the weakest dimension: basic_knowledge.': '当前基础知识维度相对薄弱，建议优先完成本次练习。',
  'lowest profile dimension': '当前相对薄弱的能力维度',
}

export function learningDimension(value?: string | null): string { return dimensions[value || ''] || value || '学习能力' }
export function learningDifficulty(value?: string | null): string { return difficulties[value || ''] || value || '未分级' }
export function learningTaskStatus(value?: string | null): string { return taskStatuses[value || ''] || value || '待安排' }
export function learningResourceType(value?: string | null): string { return resourceTypes[value || ''] || value || '学习资料' }
export function learningPlanStage(value?: string | null): string { return planStages[value || ''] || value || '个性化学习' }

export function learningText(value?: string | null): string {
  if (!value) return ''
  return legacyText[value] || value.replace(/basic_knowledge/g, '基础知识').replace(/consolidation/g, '巩固提升')
}
