<script setup lang="ts">
import { computed } from 'vue'
import { NEmpty } from 'naive-ui'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import type { LearnerDimension } from '../types/api'
import { dimensionLabels } from '../utils/format'

use([CanvasRenderer, RadarChart, TooltipComponent])

const props = withDefaults(
  defineProps<{
    dimensions: LearnerDimension[]
    compact?: boolean
  }>(),
  { compact: false },
)

const option = computed(() => ({
  animationDuration: 450,
  color: ['#1f6b4f'],
  tooltip: {
    trigger: 'item',
    valueFormatter: (value: number) => `${value} 分`,
  },
  radar: {
    center: ['50%', '52%'],
    radius: props.compact ? '62%' : '68%',
    indicator: props.dimensions.map((item) => ({
      name: dimensionLabels[item.dimension_code] || item.dimension_code,
      max: 100,
    })),
    axisName: {
      color: '#526159',
      fontSize: props.compact ? 10 : 12,
      lineHeight: 16,
    },
    splitNumber: 4,
    splitArea: {
      areaStyle: { color: ['#ffffff', '#f6f9f7'] },
    },
    splitLine: { lineStyle: { color: '#dce5df' } },
    axisLine: { lineStyle: { color: '#d3ddd6' } },
  },
  series: [
    {
      type: 'radar',
      symbol: 'circle',
      symbolSize: 5,
      lineStyle: { width: 2 },
      areaStyle: { color: 'rgba(31, 107, 79, 0.16)' },
      data: [
        {
          value: props.dimensions.map((item) => item.score),
          name: '能力得分',
        },
      ],
    },
  ],
}))
</script>

<template>
  <div class="radar-wrap" :class="{ compact }">
    <v-chart v-if="dimensions.length" :option="option" autoresize />
    <n-empty v-else size="small" description="暂无能力维度" />
  </div>
</template>

<style scoped>
.radar-wrap {
  width: 100%;
  height: 340px;
}

.radar-wrap.compact {
  height: 250px;
}

.radar-wrap > div {
  width: 100%;
  height: 100%;
}
</style>
