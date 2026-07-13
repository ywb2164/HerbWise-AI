<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    eyebrow?: string
    meta?: string
  }>(),
  {
    eyebrow: '本草智策',
    meta: '',
  },
)
</script>

<template>
  <header class="page-header">
    <div class="page-heading">
      <span class="eyebrow">{{ eyebrow }}</span>
      <div class="title-line">
        <h1>{{ title }}</h1>
        <span v-if="meta" class="page-meta">{{ meta }}</span>
      </div>
    </div>
    <div v-if="$slots.actions" class="page-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
}

.page-heading {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.title-line {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 12px;
}

h1 {
  color: var(--ink);
  font-size: 27px;
  line-height: 1.25;
  font-weight: 720;
  letter-spacing: 0;
}

.page-meta {
  color: var(--muted);
  font-size: 13px;
}

.page-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
}

@media (max-width: 680px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
    margin-bottom: 18px;
  }

  h1 {
    font-size: 23px;
  }

  .page-actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
