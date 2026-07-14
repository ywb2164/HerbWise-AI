<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  NAlert,
  NButton,
  NEmpty,
  NInput,
  NInputNumber,
  NSelect,
  NSpin,
  NTag,
  useMessage,
} from 'naive-ui'
import { BookMarked, Database, Search, Sparkles } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import SourceBadge from '../components/SourceBadge.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type {
  MedicineFeature,
  MedicineItem,
  RetrievalResult,
  SimilarMedicine,
} from '../types/api'
import { formatPercent, getErrorMessage } from '../utils/format'

const auth = useAuthStore()
const message = useMessage()
const loadingList = ref(false)
const loadingDetail = ref(false)
const retrieving = ref(false)
const generatingResource = ref(false)
const errorText = ref('')
const keyword = ref('')
const medicines = ref<MedicineItem[]>([])
const selected = ref<MedicineItem | null>(null)
const features = ref<MedicineFeature[]>([])
const similarMedicines = ref<SimilarMedicine[]>([])
const retrieval = ref<RetrievalResult | null>(null)
const retrievalForm = reactive({
  taskType: 'identification',
  query: '',
  topK: 8,
})

const taskTypeOptions = [
  { label: '性状辨识', value: 'identification' },
  { label: '近似药区分', value: 'comparison' },
  { label: '质量控制', value: 'quality_control' },
  { label: '复习训练', value: 'review' },
]

const featureTypeLabels: Record<string, string> = {
  appearance: '外观',
  surface: '表面',
  texture: '质地',
  section: '断面',
  color: '色泽',
  smell: '气味',
  taste: '味道',
  processing: '炮制',
  quality_control: '质量控制',
  storage: '储藏',
  risk: '风险',
  training_tip: '训练提示',
}

async function loadMedicines(selectFirst = true): Promise<void> {
  loadingList.value = true
  errorText.value = ''
  try {
    const data = await api.listMedicines(keyword.value.trim())
    medicines.value = data.items
    if (selectFirst && medicines.value.length) await selectMedicine(medicines.value[0])
    if (!medicines.value.length) {
      selected.value = null
      features.value = []
      similarMedicines.value = []
    }
  } catch (error) {
    errorText.value = getErrorMessage(error, '药材列表加载失败')
  } finally {
    loadingList.value = false
  }
}

async function selectMedicine(item: MedicineItem): Promise<void> {
  selected.value = item
  retrieval.value = null
  loadingDetail.value = true
  try {
    const [detail, featureData, similarData] = await Promise.all([
      api.getMedicine(item.id),
      api.getMedicineFeatures(item.id),
      api.getSimilarMedicines(item.id),
    ])
    selected.value = detail
    features.value = featureData
    similarMedicines.value = similarData
  } catch (error) {
    message.error(getErrorMessage(error, '药材档案加载失败'))
  } finally {
    loadingDetail.value = false
  }
}

async function retrieveEvidence(): Promise<void> {
  if (!selected.value) return
  retrieving.value = true
  try {
    retrieval.value = await api.retrieveKnowledge({
      learner_id: auth.learnerId,
      medicine_name: selected.value.standard_name_zh,
      task_type: retrievalForm.taskType,
      query: retrievalForm.query.trim() || undefined,
      top_k: retrievalForm.topK,
    })
    message.success(`已返回 ${retrieval.value.evidences.length} 条证据`)
  } catch (error) {
    message.error(getErrorMessage(error, '知识证据检索失败'))
  } finally {
    retrieving.value = false
  }
}

async function generateKnowledgeResource(resourceType: string): Promise<void> {
  if (!selected.value) return
  generatingResource.value = true
  try {
    const job = await api.createResourceGenerationJob({
      learner_id: auth.learnerId,
      topic: selected.value.standard_name_zh,
      resource_type: resourceType,
      difficulty: 'basic',
      requires_citation: resourceType === 'detailed_comparison',
      additional_instruction: `请围绕${selected.value.standard_name_zh}生成学习材料。`,
    })
    message[job.resource_id ? 'success' : 'warning'](job.resource_id ? '学习资源已生成，可在资源库查看' : `资源作业状态：${job.status}`)
  } catch (error) {
    message.error(getErrorMessage(error, '学习资源生成失败'))
  } finally {
    generatingResource.value = false
  }
}

onMounted(() => loadMedicines(true))
</script>

<template>
  <div class="page knowledge-page">
    <PageHeader title="药材知识" :meta="`${medicines.length} 条结构化档案`">
      <template #actions>
        <n-input
          v-model:value="keyword"
          class="medicine-search"
          clearable
          placeholder="搜索药材名称"
          @keyup.enter="loadMedicines(true)"
        >
          <template #prefix><Search :size="17" /></template>
        </n-input>
        <n-button type="primary" :loading="loadingList" @click="loadMedicines(true)">搜索</n-button>
      </template>
    </PageHeader>

    <n-alert v-if="errorText" type="error" :bordered="false" class="knowledge-alert">{{ errorText }}</n-alert>

    <section class="knowledge-browser">
      <div class="surface medicine-list-panel">
        <div class="surface-header">
          <h2 class="surface-title">药材目录</h2>
          <Database :size="18" color="#2f6f8f" />
        </div>
        <n-spin :show="loadingList">
          <div v-if="medicines.length" class="medicine-list">
            <button
              v-for="item in medicines"
              :key="item.id"
              type="button"
              class="medicine-row"
              :class="{ active: selected?.id === item.id }"
              @click="selectMedicine(item)"
            >
              <span class="medicine-code">{{ item.medicine_code }}</span>
              <strong>{{ item.standard_name_zh }}</strong>
              <small>{{ item.standard_name_en || item.latin_name || '--' }}</small>
            </button>
          </div>
          <div v-else class="empty-state"><n-empty description="未找到药材" /></div>
        </n-spin>
      </div>

      <div class="surface medicine-detail-panel">
        <n-spin :show="loadingDetail">
          <template v-if="selected">
            <div class="medicine-heading">
              <div>
                <span class="eyebrow">{{ selected.medicine_code }}</span>
                <h2>{{ selected.standard_name_zh }}</h2>
                <p>{{ selected.standard_name_en || '--' }} <span v-if="selected.latin_name">· {{ selected.latin_name }}</span></p>
              </div>
              <div class="knowledge-actions"><n-button size="small" secondary :loading="generatingResource" @click="generateKnowledgeResource('knowledge_card')">为我讲解</n-button><n-button size="small" secondary :loading="generatingResource" @click="generateKnowledgeResource('comparison_card')">生成对比卡</n-button><SourceBadge source="mysql" :official="true" /></div>
            </div>

            <div class="medicine-facts">
              <dl>
                <div>
                  <dt>来源</dt>
                  <dd>{{ selected.source || '--' }}</dd>
                </div>
                <div>
                  <dt>性味</dt>
                  <dd>{{ selected.properties_flavor || '--' }}</dd>
                </div>
                <div>
                  <dt>归经</dt>
                  <dd>{{ selected.meridian_tropism || '--' }}</dd>
                </div>
              </dl>
              <p>{{ selected.description || '暂无药材描述。' }}</p>
            </div>

            <div class="feature-section">
              <div class="subsection-heading">
                <h3>性状特征</h3>
                <span>{{ features.length }} 项</span>
              </div>
              <div v-if="features.length" class="feature-list">
                <div v-for="item in features" :key="item.feature_id || `${item.feature_type}-${item.feature_name}`" class="feature-row">
                  <n-tag size="small" :bordered="false">{{ featureTypeLabels[item.feature_type] || item.feature_type }}</n-tag>
                  <strong>{{ item.feature_name }}</strong>
                  <p>{{ item.feature_value }}</p>
                </div>
              </div>
              <n-empty v-else size="small" description="暂无性状特征" />
            </div>

            <div class="similar-section">
              <div class="subsection-heading">
                <h3>近似药对比</h3>
                <span>{{ similarMedicines.length }} 项</span>
              </div>
              <div v-if="similarMedicines.length" class="similar-list">
                <div v-for="(item, index) in similarMedicines" :key="item.id || index" class="similar-row">
                  <BookMarked :size="17" />
                  <div>
                    <strong>{{ item.similar_name || `近似药 ${item.similar_medicine_id || index + 1}` }}</strong>
                    <span>{{ item.confusion_reason || '暂无混淆原因说明' }}</span>
                  </div>
                  <n-tag size="small" type="warning" :bordered="false">{{ item.risk_level || 'low' }}</n-tag>
                </div>
              </div>
              <n-empty v-else size="small" description="暂无近似药配置" />
            </div>
          </template>
          <div v-else class="empty-state"><n-empty description="请选择药材档案" /></div>
        </n-spin>
      </div>
    </section>

    <section class="surface retrieval-panel">
      <div class="surface-header">
        <div>
          <h2 class="surface-title">知识证据检索</h2>
          <span class="surface-caption">{{ selected?.standard_name_zh || '未选择药材' }}</span>
        </div>
        <SourceBadge :source="retrieval?.data_source || retrieval?.provider || 'mock'" :official="false" />
      </div>
      <div class="retrieval-form">
        <n-select v-model:value="retrievalForm.taskType" :options="taskTypeOptions" />
        <n-input v-model:value="retrievalForm.query" clearable placeholder="可选检索问题" @keyup.enter="retrieveEvidence">
          <template #prefix><Sparkles :size="16" /></template>
        </n-input>
        <n-input-number v-model:value="retrievalForm.topK" :min="1" :max="20" />
        <n-button type="primary" :disabled="!selected" :loading="retrieving" @click="retrieveEvidence">
          检索证据
          <template #icon><Search :size="17" /></template>
        </n-button>
      </div>

      <div v-if="retrieval" class="retrieval-result-meta">
        <span class="mono">{{ retrieval.retrieval_id }}</span>
        <span>返回 {{ retrieval.evidences.length }} 条</span>
        <span v-if="retrieval.latency_ms">{{ Math.round(retrieval.latency_ms) }} ms</span>
        <n-tag v-if="retrieval.fallback_used" size="small" type="warning" :bordered="false">已降级</n-tag>
        <n-tag v-if="retrieval.replay_used" size="small" type="info" :bordered="false">Replay</n-tag>
      </div>

      <div v-if="retrieval?.evidences.length" class="retrieval-evidence-list">
        <article v-for="(item, index) in retrieval.evidences" :key="item.evidence_id || index" class="retrieval-evidence">
          <span class="evidence-rank">{{ item.rank || index + 1 }}</span>
          <div>
            <div class="evidence-title">
              <h3>{{ item.document_name || item.citation || '检索证据' }}</h3>
              <strong>{{ formatPercent(item.score, 1) }}</strong>
            </div>
            <p>{{ item.content || '暂无证据摘要' }}</p>
            <div class="evidence-meta">
              <span>页码 {{ item.page_number ?? '未标注' }}</span>
              <span>Chunk {{ item.chunk_id || '未标注' }}</span>
              <span v-if="item.citation">{{ item.citation }}</span>
            </div>
          </div>
        </article>
      </div>
      <div v-else class="empty-state"><n-empty description="暂无检索证据" /></div>
    </section>
  </div>
</template>

<style scoped>
.medicine-search {
  width: min(260px, 60vw);
}

.knowledge-alert {
  margin-bottom: 18px;
}

.knowledge-browser {
  display: grid;
  grid-template-columns: 286px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.medicine-list-panel {
  position: sticky;
  top: 84px;
  max-height: calc(100vh - 108px);
  overflow: hidden;
}

.medicine-list {
  max-height: calc(100vh - 167px);
  overflow-y: auto;
}

.medicine-row {
  display: grid;
  width: 100%;
  min-height: 72px;
  padding: 12px 16px;
  color: var(--ink);
  background: #fff;
  border: 0;
  border-bottom: 1px solid var(--line);
  cursor: pointer;
  text-align: left;
}

.medicine-row:last-child {
  border-bottom: 0;
}

.medicine-row:hover {
  background: #f7faf8;
}

.medicine-row.active {
  background: var(--primary-soft);
  box-shadow: inset 3px 0 var(--primary);
}

.medicine-code {
  color: var(--subtle);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 9px;
  text-transform: uppercase;
}

.medicine-row strong {
  margin-top: 1px;
  font-size: 14px;
}

.medicine-row small {
  overflow: hidden;
  color: var(--muted);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.medicine-detail-panel {
  min-height: 540px;
}

.medicine-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 24px;
  background: #f2f7f4;
  border-bottom: 1px solid var(--line);
}

.knowledge-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.medicine-heading h2 {
  margin: 4px 0 2px;
  color: var(--ink);
  font-size: 27px;
  font-weight: 720;
}

.medicine-heading p {
  color: var(--muted);
  font-size: 12px;
}

.medicine-facts {
  padding: 20px 24px;
  border-bottom: 1px solid var(--line);
}

.medicine-facts dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin: 0;
}

.medicine-facts dl > div {
  min-width: 0;
  padding-right: 16px;
  border-right: 1px solid var(--line);
}

.medicine-facts dl > div:last-child {
  border-right: 0;
}

.medicine-facts dt,
.medicine-facts dd {
  margin: 0;
}

.medicine-facts dt {
  color: var(--muted);
  font-size: 10px;
}

.medicine-facts dd {
  margin-top: 4px;
  color: var(--ink);
  font-size: 13px;
  overflow-wrap: anywhere;
}

.medicine-facts > p {
  margin-top: 18px;
  color: #4d5b53;
  font-size: 13px;
  line-height: 1.75;
}

.feature-section,
.similar-section {
  padding: 20px 24px;
}

.feature-section {
  border-bottom: 1px solid var(--line);
}

.subsection-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.subsection-heading h3 {
  color: var(--ink);
  font-size: 14px;
  font-weight: 650;
}

.subsection-heading span {
  color: var(--subtle);
  font-size: 10px;
}

.feature-list,
.similar-list {
  display: grid;
}

.feature-row {
  display: grid;
  grid-template-columns: 92px 120px minmax(0, 1fr);
  align-items: start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--line);
}

.feature-row:last-child,
.similar-row:last-child {
  border-bottom: 0;
}

.feature-row strong {
  color: var(--ink);
  font-size: 12px;
}

.feature-row p {
  color: #56635c;
  font-size: 12px;
  line-height: 1.6;
}

.similar-row {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 11px 0;
  border-bottom: 1px solid var(--line);
}

.similar-row svg {
  color: var(--amber);
}

.similar-row > div {
  display: grid;
  gap: 2px;
}

.similar-row strong {
  color: var(--ink);
  font-size: 12px;
}

.similar-row span {
  color: var(--muted);
  font-size: 11px;
}

.retrieval-panel {
  margin-top: 20px;
}

.surface-caption {
  display: block;
  margin-top: 3px;
  color: var(--subtle);
  font-size: 11px;
}

.retrieval-form {
  display: grid;
  grid-template-columns: 190px minmax(240px, 1fr) 110px auto;
  gap: 10px;
  padding: 18px;
  border-bottom: 1px solid var(--line);
}

.retrieval-result-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 18px;
  padding: 12px 18px;
  color: var(--muted);
  background: var(--surface-soft);
  border-bottom: 1px solid var(--line);
  font-size: 11px;
}

.retrieval-evidence-list {
  padding: 0 18px;
}

.retrieval-evidence {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 14px;
  padding: 18px 0;
  border-bottom: 1px solid var(--line);
}

.retrieval-evidence:last-child {
  border-bottom: 0;
}

.evidence-rank {
  color: var(--blue);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 12px;
}

.evidence-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.evidence-title h3 {
  color: var(--ink);
  font-size: 14px;
  line-height: 1.4;
  font-weight: 650;
}

.evidence-title strong {
  color: var(--blue);
  font-size: 12px;
}

.retrieval-evidence p {
  margin-top: 7px;
  color: #4d5b53;
  font-size: 12px;
  line-height: 1.7;
}

.evidence-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 7px 16px;
  margin-top: 9px;
  color: var(--subtle);
  font-size: 10px;
}

@media (max-width: 980px) {
  .knowledge-browser {
    grid-template-columns: 1fr;
  }

  .medicine-list-panel {
    position: static;
    max-height: none;
  }

  .medicine-list {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    max-height: 280px;
  }

  .retrieval-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 680px) {
  .medicine-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .medicine-facts dl,
  .retrieval-form {
    grid-template-columns: 1fr;
  }

  .medicine-facts dl > div {
    padding: 0 0 10px;
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }

  .feature-row {
    grid-template-columns: 88px minmax(0, 1fr);
  }

  .feature-row p {
    grid-column: 1 / -1;
  }
}
</style>
