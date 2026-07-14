<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { BookOpenText, RefreshCw } from 'lucide-vue-next'
import { NButton, NEmpty, NModal, NSpin, NTag, useMessage } from 'naive-ui'
import MarkdownArticle from '../components/MarkdownArticle.vue'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { ResourceItem } from '../types/api'
import { formatDate, getErrorMessage } from '../utils/format'
import { learningDimension, learningDifficulty, learningResourceType, learningText } from '../utils/learningDisplay'

const auth = useAuthStore()
const route = useRoute()
const message = useMessage()
const loading = ref(false)
const showDetail = ref(false)
const resources = ref<ResourceItem[]>([])
const selectedResource = ref<ResourceItem | null>(null)

const resourceCount = computed(() => resources.value.length)

async function loadResources(): Promise<void> {
  loading.value = true
  try { resources.value = (await api.listResources(auth.learnerId)).items }
  catch (error) { message.error(getErrorMessage(error, '学习资源加载失败，请稍后重试。')) }
  finally { loading.value = false }
}

async function openResource(item: ResourceItem): Promise<void> {
  try { selectedResource.value = await api.getResource(item.resource_id); showDetail.value = true }
  catch (error) { message.error(getErrorMessage(error, '学习资料暂时无法打开，请稍后重试。')) }
}

onMounted(async () => {
  await loadResources()
  const resourceId = typeof route.query.resource === 'string' ? route.query.resource : ''
  const resource = resources.value.find(item => item.resource_id === resourceId)
  if (resource) await openResource(resource)
})
</script>

<template>
  <div class="page resources-page">
    <PageHeader title="学习资源" :meta="`已为你整理 ${resourceCount} 份可学习资料`">
      <template #actions><n-button secondary :loading="loading" @click="loadResources"><template #icon><RefreshCw :size="17" /></template>刷新资料</n-button></template>
    </PageHeader>
    <n-spin :show="loading">
      <section v-if="resources.length" class="resource-grid">
        <article v-for="item in resources" :key="item.resource_id" class="surface resource-card">
          <BookOpenText :size="20" />
          <div class="resource-copy"><n-tag size="small" :bordered="false">{{ learningResourceType(item.resource_type) }}</n-tag><h2>{{ learningText(item.title) }}</h2><p>{{ learningText(item.personalization_reason) || '为你当前的学习目标准备。' }}</p><small>{{ item.target_knowledge_points?.join('、') || learningDimension(item.target_dimensions?.[0]) }} · 约 {{ item.estimated_minutes || 10 }} 分钟 · {{ formatDate(item.created_at) }}</small><span v-if="item.status === 'degraded'" class="resource-note">该资料使用基础模板生成</span></div>
          <n-button type="primary" secondary @click="openResource(item)">开始学习</n-button>
        </article>
      </section>
      <n-empty v-else description="还没有可学习的资源"><template #extra><span>完成学习任务后，系统会为你准备对应资料。</span></template></n-empty>
    </n-spin>
  </div>
  <n-modal v-model:show="showDetail" preset="card" :title="learningText(selectedResource?.title) || '学习资料'" :style="{ width: 'min(920px, calc(100vw - 32px))' }">
    <section v-if="selectedResource" class="resource-detail">
      <div class="detail-meta"><n-tag :bordered="false">{{ learningResourceType(selectedResource.resource_type) }}</n-tag><span>{{ learningDifficulty(selectedResource.difficulty) }} · 约 {{ selectedResource.estimated_minutes || 10 }} 分钟</span></div>
      <section v-if="selectedResource.learning_objectives?.length" class="detail-section"><h3>学习目标</h3><ul><li v-for="item in selectedResource.learning_objectives" :key="item">{{ item }}</li></ul></section>
      <MarkdownArticle :content="selectedResource.content_markdown" />
      <section v-if="selectedResource.target_knowledge_points?.length" class="detail-section"><h3>关键知识点</h3><n-tag v-for="item in selectedResource.target_knowledge_points" :key="item" :bordered="false">{{ item }}</n-tag></section>
      <section v-if="selectedResource.citations?.length" class="detail-section"><h3>参考资料</h3><p v-for="citation in selectedResource.citations" :key="citation.evidence_id">{{ citation.citation }}</p></section>
    </section>
  </n-modal>
</template>

<style scoped>
.resource-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(290px,1fr)); gap:16px; }.resource-card{display:grid;grid-template-columns:24px minmax(0,1fr);gap:13px;padding:20px}.resource-card>svg{color:var(--primary)}.resource-copy{display:grid;gap:8px}.resource-copy h2{margin:0;color:var(--ink);font-size:17px}.resource-copy p,.resource-copy small{margin:0;color:var(--muted);font-size:12px;line-height:1.7}.resource-card>.n-button{grid-column:2;justify-self:start}.resource-note{color:#8a5c20;font-size:12px}.resource-detail{max-height:72vh;overflow:auto;padding-right:8px}.detail-meta{display:flex;gap:10px;align-items:center;margin-bottom:18px;color:var(--muted);font-size:13px}.detail-section{margin:20px 0}.detail-section h3{color:var(--ink);font-size:16px}.detail-section ul{padding-left:20px}.detail-section p{color:var(--muted);font-size:13px;line-height:1.7}.detail-section .n-tag{margin-right:7px}
</style>
