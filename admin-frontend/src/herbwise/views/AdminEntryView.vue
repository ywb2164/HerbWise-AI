<script setup lang="ts">
import { onMounted } from 'vue';
import { portalLoginUrl } from '../auth-handoff';

onMounted(() => window.location.replace(portalLoginUrl()));
</script>

<template>
  <main class="entry-page">
    <NSpin size="large" />
    <strong>正在返回统一登录入口</strong>
  </main>
</template>

<style scoped>
.entry-page {
  display: grid;
  min-height: 100vh;
  color: #52635a;
  background: #eef3f0;
  place-content: center;
  justify-items: center;
  gap: 16px;
}
</style>
