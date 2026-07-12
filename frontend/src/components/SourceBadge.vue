<script setup lang="ts">
import { computed } from 'vue'
import { NTag } from 'naive-ui'

const props = withDefaults(
  defineProps<{
    source?: string | null
    official?: boolean | null
  }>(),
  {
    source: '',
    official: null,
  },
)

const normalized = computed(() => (props.source || 'unknown').toLowerCase())
const label = computed(() => {
  const labels: Record<string, string> = {
    mock: '规则样本',
    replay: 'Replay 回放',
    real: '真实调用',
    ragflow: 'RAGFlow',
    hybrid: '混合检索',
    mysql: '结构化知识',
    local: '本地模型',
    qwen: 'Qwen-VL',
    openai: 'OpenAI 兼容',
    openai_compatible: 'OpenAI 兼容',
    anthropic: 'Anthropic 兼容',
    anthropic_compatible: 'Anthropic 兼容',
    mixed: '混合来源',
    fallback: '降级结果',
    unknown: '来源未知',
  }
  return labels[normalized.value] || props.source || '来源未知'
})

const type = computed<'success' | 'info' | 'warning' | 'default'>(() => {
  if (props.official === false || ['mock', 'replay', 'fallback'].includes(normalized.value)) return 'warning'
  if (
    [
      'real',
      'ragflow',
      'local',
      'qwen',
      'openai',
      'openai_compatible',
      'anthropic',
      'anthropic_compatible',
    ].includes(normalized.value)
  ) return 'success'
  if (['hybrid', 'mysql', 'mixed'].includes(normalized.value)) return 'info'
  return 'default'
})
</script>

<template>
  <n-tag :type="type" size="small" :bordered="false">{{ label }}</n-tag>
</template>
