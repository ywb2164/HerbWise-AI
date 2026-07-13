<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  note?: string
  tone?: 'green' | 'blue' | 'amber' | 'neutral'
}>()
</script>

<template>
  <div class="metric-tile" :class="tone || 'neutral'">
    <div class="metric-icon"><slot name="icon" /></div>
    <div class="metric-copy">
      <span>{{ label }}</span>
      <strong>{{ value }}</strong>
      <small v-if="note">{{ note }}</small>
    </div>
  </div>
</template>

<style scoped>
.metric-tile {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 13px;
  min-height: 112px;
  padding: 18px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
}

.metric-icon {
  display: grid;
  width: 42px;
  height: 42px;
  color: #536159;
  background: #eef1ef;
  border-radius: 7px;
  place-items: center;
}

.metric-tile.green .metric-icon {
  color: var(--primary);
  background: var(--primary-soft);
}

.metric-tile.blue .metric-icon {
  color: var(--blue);
  background: var(--blue-soft);
}

.metric-tile.amber .metric-icon {
  color: var(--amber);
  background: var(--amber-soft);
}

.metric-copy {
  display: grid;
  align-content: start;
  gap: 2px;
  min-width: 0;
}

.metric-copy span {
  color: var(--muted);
  font-size: 12px;
}

.metric-copy strong {
  color: var(--ink);
  font-size: 26px;
  line-height: 1.25;
  font-weight: 720;
}

.metric-copy small {
  color: var(--subtle);
  font-size: 11px;
}
</style>
