<script setup lang="ts">
import { Sprout } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    compact?: boolean
    linked?: boolean
    inverse?: boolean
    to?: string
  }>(),
  {
    compact: false,
    linked: true,
    inverse: false,
    to: '/dashboard',
  },
)
</script>

<template>
  <component
    :is="linked ? 'router-link' : 'div'"
    :to="linked ? to : undefined"
    class="app-logo"
    :class="{ compact, inverse }"
    aria-label="本草智策"
  >
    <span class="logo-mark" aria-hidden="true">
      <Sprout :size="22" :stroke-width="2" />
      <i />
    </span>
    <span v-if="!compact" class="logo-copy">
      <strong>本草智策</strong>
      <small>HERBWISE AI · 智鉴本草</small>
    </span>
  </component>
</template>

<style scoped>
.app-logo {
  display: inline-flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
  color: var(--ink);
  text-decoration: none;
}

.logo-mark {
  position: relative;
  display: grid;
  flex: 0 0 40px;
  width: 40px;
  height: 40px;
  color: #fff;
  background: #0b654b;
  border: 1px solid #064936;
  border-radius: 8px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
  place-items: center;
}

.logo-mark i {
  position: absolute;
  right: 5px;
  bottom: 5px;
  width: 5px;
  height: 5px;
  background: #d6a84a;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 50%;
}

.logo-copy {
  display: grid;
  gap: 1px;
  min-width: 0;
}

.logo-copy strong {
  color: inherit;
  font-size: 18px;
  line-height: 1.25;
  font-weight: 740;
  white-space: nowrap;
}

.logo-copy small {
  color: var(--muted);
  font-size: 8px;
  line-height: 1.2;
  font-weight: 700;
  white-space: nowrap;
}

.app-logo.compact .logo-mark {
  width: 36px;
  height: 36px;
  flex-basis: 36px;
}

.app-logo.inverse {
  color: #fff;
}

.app-logo.inverse .logo-copy small {
  color: rgba(255, 255, 255, 0.7);
}
</style>
