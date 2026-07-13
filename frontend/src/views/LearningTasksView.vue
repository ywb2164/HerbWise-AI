<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  NAlert,
  NButton,
  NInput,
  NRadio,
  NRadioGroup,
  NSelect,
  NSpin,
  NTag,
  useMessage,
} from 'naive-ui'
import { BookOpenCheck, CheckCircle2, MessageSquareMore, RefreshCw, Send, Sparkles } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import SourceBadge from '../components/SourceBadge.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type {
  DimensionCode,
  LearnerDimension,
  LearningAnswer,
  LearningPath,
  MedicineItem,
  ResourceItem,
  ReviewResult,
} from '../types/api'
import {
  dimensionLabels,
  formatDate,
  formatResourceStatus,
  getErrorMessage,
  levelLabels,
  taskTypeLabels,
} from '../utils/format'

interface PracticeQuestion {
  dimension: DimensionCode
  knowledgePoint: string
  stem: string
  options: Array<{ key: string; text: string }>
  correct: string
  explanation: string
}

const questionBank: Record<DimensionCode, PracticeQuestion> = {
  basic_knowledge: {
    dimension: 'basic_knowledge',
    knowledgePoint: '饮片性状鉴别要素',
    stem: '进行中药饮片性状鉴别时，以下哪组观察要素更完整？',
    options: [
      { key: 'A', text: '形状、表面、切面、质地、气味' },
      { key: 'B', text: '只看商品标签和价格' },
      { key: 'C', text: '只比较颜色深浅' },
    ],
    correct: 'A',
    explanation: '性状鉴别应联合多项可观察证据，避免依赖单一特征。',
  },
  character_identification: {
    dimension: 'character_identification',
    knowledgePoint: '切面纹理观察',
    stem: '观察饮片切面纹理时，哪项操作更规范？',
    options: [
      { key: 'A', text: '使用清晰新鲜切面并在中性光下观察' },
      { key: 'B', text: '隔着有色包装快速判断' },
      { key: 'C', text: '只读取文件名，不看图像' },
    ],
    correct: 'A',
    explanation: '切面应清晰、光照稳定，必要时保留尺度与拍摄条件。',
  },
  similar_medicine: {
    dimension: 'similar_medicine',
    knowledgePoint: '相似饮片复核',
    stem: '两个相似饮片候选置信度接近时，优先采取哪项措施？',
    options: [
      { key: 'A', text: '补充切面图并检索差异特征后复核' },
      { key: 'B', text: '无条件选择排序第一项' },
      { key: 'C', text: '隐藏候选和置信度' },
    ],
    correct: 'A',
    explanation: '候选接近时需要更多图像证据和辨析依据，不能省略复核。',
  },
  pharmacopoeia_rules: {
    dimension: 'pharmacopoeia_rules',
    knowledgePoint: '药典证据引用',
    stem: '形成药典依据时，哪种记录方式可追溯？',
    options: [
      { key: 'A', text: '记录版本、品名、条目位置和证据原文' },
      { key: 'B', text: '只写“网上查到”' },
      { key: 'C', text: '不记录来源，仅保留结论' },
    ],
    correct: 'A',
    explanation: '版本、条目位置和原文证据是后续复核的基本条件。',
  },
  clinical_quality_control: {
    dimension: 'clinical_quality_control',
    knowledgePoint: '异常饮片质量处置',
    stem: '饮片出现疑似霉变或虫蛀时，首要动作是？',
    options: [
      { key: 'A', text: '隔离、记录并进入质量复核' },
      { key: 'B', text: '与合格样品混放' },
      { key: 'C', text: '擦除异常后不留记录' },
    ],
    correct: 'A',
    explanation: '质量异常样本必须先隔离和留痕，再依据规范复核。',
  },
  practical_review: {
    dimension: 'practical_review',
    knowledgePoint: '实操结果复盘',
    stem: '一次完整的辨识复盘应至少包含什么？',
    options: [
      { key: 'A', text: '候选、置信度、证据、错误点与改进动作' },
      { key: 'B', text: '只保留最终药名' },
      { key: 'C', text: '只保留上传时间' },
    ],
    correct: 'A',
    explanation: '复盘需要保留决策过程和改进动作，才能持续更新画像。',
  },
}

const auth = useAuthStore()
const message = useMessage()
const loading = ref(true)
const errorText = ref('')
const path = ref<LearningPath | null>(null)
const dimensions = ref<LearnerDimension[]>([])
const answers = ref<LearningAnswer[]>([])
const medicines = ref<MedicineItem[]>([])
const selectedMedicine = ref<number | null>(null)
const selectedAnswer = ref('')
const submittingAnswer = ref(false)
const answerSubmitted = ref(false)
const followup = ref('')
const generating = ref(false)
const generatedResource = ref<ResourceItem | null>(null)
const review = ref<ReviewResult | null>(null)

const weakestDimension = computed<DimensionCode>(() => {
  const weakest = [...dimensions.value].sort((a, b) => a.score - b.score)[0]
  return (weakest?.dimension_code as DimensionCode) || 'basic_knowledge'
})
const practice = computed(() => questionBank[weakestDimension.value])
const practiceCorrect = computed(() => selectedAnswer.value === practice.value.correct)
const medicineOptions = computed(() =>
  medicines.value.map(item => ({ label: item.standard_name_zh, value: item.id })),
)
const currentMedicine = computed(() => medicines.value.find(item => item.id === selectedMedicine.value) || null)
const averageScore = computed(() => {
  if (!dimensions.value.length) return 0
  return dimensions.value.reduce((sum, item) => sum + item.score, 0) / dimensions.value.length
})
const difficulty = computed(() => (averageScore.value < 60 ? 'basic' : averageScore.value < 80 ? 'intermediate' : 'advanced'))

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  const results = await Promise.allSettled([
    api.getLearningPath(auth.learnerId),
    api.getDimensions(auth.learnerId),
    api.listLearningAnswers(auth.learnerId, 20),
    api.listMedicines('', 50),
  ])
  if (results[0].status === 'fulfilled') path.value = results[0].value
  if (results[1].status === 'fulfilled') dimensions.value = results[1].value
  if (results[2].status === 'fulfilled') answers.value = results[2].value.items
  if (results[3].status === 'fulfilled') {
    medicines.value = results[3].value.items
    selectedMedicine.value ||= medicines.value[0]?.id || null
  }
  const failed = results.find(result => result.status === 'rejected')
  if (failed?.status === 'rejected') errorText.value = getErrorMessage(failed.reason, '部分学习任务数据加载失败')
  loading.value = false
}

async function submitPractice(): Promise<void> {
  if (!selectedAnswer.value) return
  submittingAnswer.value = true
  errorText.value = ''
  try {
    const record = await api.submitLearningAnswer({
      learner_id: auth.learnerId,
      dimension_code: practice.value.dimension,
      knowledge_point: practice.value.knowledgePoint,
      answer: { value: selectedAnswer.value },
      is_correct: practiceCorrect.value,
      score: practiceCorrect.value ? 100 : 0,
      feedback: practice.value.explanation,
    })
    answers.value.unshift(record)
    path.value = await api.updateLearningPath(auth.learnerId)
    answerSubmitted.value = true
    message.success('练习结果已更新到学习路径')
  } catch (error) {
    errorText.value = getErrorMessage(error, '练习提交失败')
  } finally {
    submittingAnswer.value = false
  }
}

function resetPractice(): void {
  selectedAnswer.value = ''
  answerSubmitted.value = false
}

async function generateFollowup(): Promise<void> {
  if (!currentMedicine.value || !followup.value.trim()) return
  generating.value = true
  generatedResource.value = null
  review.value = null
  errorText.value = ''
  try {
    const retrieval = await api.retrieveKnowledge({
      learner_id: auth.learnerId,
      medicine_name: currentMedicine.value.standard_name_zh,
      task_type: 'dynamic_followup',
      query: followup.value.trim(),
      top_k: 5,
    })
    const resource = await api.generateResource({
      learner_id: auth.learnerId,
      medicine_name: currentMedicine.value.standard_name_zh,
      resource_type: 'guide',
      difficulty: difficulty.value,
      retrieval_id: retrieval.retrieval_id,
      evidence_ids: retrieval.evidences
        .map(item => item.evidence_id)
        .filter((id): id is string => Boolean(id)),
    })
    generatedResource.value = resource
    review.value = await api.reviewResource(resource.resource_id)
    message.success('针对性学习资源已生成并完成审核')
  } catch (error) {
    errorText.value = getErrorMessage(error, '动态追问处理失败')
  } finally {
    generating.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page learning-tasks-page">
    <PageHeader title="学习任务" eyebrow="个性化学习" :meta="`学习路径 v${path?.version || 1}`">
      <template #actions>
        <n-button secondary @click="load">
          刷新任务
          <template #icon><RefreshCw :size="17" /></template>
        </n-button>
      </template>
    </PageHeader>

    <n-alert v-if="errorText" type="warning" :bordered="false" closable class="task-alert" @close="errorText = ''">
      {{ errorText }}
    </n-alert>

    <n-spin :show="loading">
      <section class="path-band">
        <div>
          <span class="eyebrow">当前学习阶段</span>
          <h2>{{ levelLabels[path?.current_stage || 'foundation'] || path?.current_stage || '基础巩固' }}</h2>
        </div>
        <div class="recommended-types">
          <span>推荐资源</span>
          <n-tag v-for="type in path?.path.recommended_task_types || ['lecture', 'quiz']" :key="type" size="small" :bordered="false">
            {{ taskTypeLabels[type] || type }}
          </n-tag>
        </div>
        <div class="weakest-focus">
          <span>本轮重点</span>
          <strong>{{ dimensionLabels[weakestDimension] }}</strong>
        </div>
      </section>

      <section class="learning-workspace">
        <article class="practice-panel surface">
          <header>
            <div class="panel-icon"><CheckCircle2 :size="20" /></div>
            <div><span>分阶测试</span><h2>{{ dimensionLabels[practice.dimension] }}</h2></div>
          </header>
          <div class="practice-body">
            <h3>{{ practice.stem }}</h3>
            <n-radio-group v-model:value="selectedAnswer" class="practice-options" :disabled="answerSubmitted">
              <n-radio v-for="option in practice.options" :key="option.key" :value="option.key" class="practice-option">
                <b>{{ option.key }}</b><span>{{ option.text }}</span>
              </n-radio>
            </n-radio-group>
            <div v-if="answerSubmitted" class="practice-feedback" :class="{ correct: practiceCorrect }">
              <strong>{{ practiceCorrect ? '回答正确' : '需要继续巩固' }}</strong>
              <p>{{ practice.explanation }}</p>
            </div>
            <n-button v-if="!answerSubmitted" type="primary" block :disabled="!selectedAnswer" :loading="submittingAnswer" @click="submitPractice">
              提交答案
            </n-button>
            <n-button v-else secondary block @click="resetPractice">再次练习</n-button>
          </div>
        </article>

        <article class="followup-panel surface">
          <header>
            <div class="panel-icon blue"><MessageSquareMore :size="20" /></div>
            <div><span>动态追问</span><h2>检索依据并生成讲解</h2></div>
          </header>
          <div class="followup-form">
            <n-select v-model:value="selectedMedicine" :options="medicineOptions" filterable placeholder="选择药材" />
            <n-input
              v-model:value="followup"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 7 }"
              placeholder="输入需要进一步辨析的问题"
            />
            <n-button type="primary" block :disabled="!selectedMedicine || !followup.trim()" :loading="generating" @click="generateFollowup">
              生成针对性讲解
              <template #icon><Send :size="17" /></template>
            </n-button>
          </div>
          <div v-if="generatedResource" class="generated-followup">
            <div class="generated-title">
              <div><span>{{ taskTypeLabels[generatedResource.resource_type] || generatedResource.resource_type }}</span><strong>{{ generatedResource.title }}</strong></div>
              <SourceBadge :source="generatedResource.provider" />
            </div>
            <div class="generated-content">{{ generatedResource.content_markdown }}</div>
            <div v-if="review" class="review-line">
              <BookOpenCheck :size="17" />
              <span>内容审核</span>
              <strong>{{ formatResourceStatus(review.status) }}</strong>
            </div>
          </div>
        </article>
      </section>

      <section class="answer-history surface">
        <header>
          <div><Sparkles :size="19" /><h2>最近学习反馈</h2></div>
          <span>{{ answers.length }} 条记录</span>
        </header>
        <div v-if="answers.length" class="history-list">
          <div v-for="item in answers.slice(0, 8)" :key="item.id" class="history-row">
            <span class="history-state" :class="{ success: item.is_correct }" />
            <div><strong>{{ item.knowledge_point }}</strong><small>{{ dimensionLabels[item.dimension_code] }}</small></div>
            <b>{{ Math.round(item.score) }} 分</b>
            <time>{{ formatDate(item.submitted_at) }}</time>
          </div>
        </div>
        <div v-else class="history-empty">完成分阶测试或虚拟实训后，反馈会记录在这里。</div>
      </section>
    </n-spin>
  </div>
</template>

<style scoped>
.task-alert {
  margin-bottom: 16px;
}

.path-band {
  display: grid;
  grid-template-columns: minmax(190px, 0.7fr) minmax(300px, 1.3fr) minmax(160px, 0.6fr);
  align-items: center;
  gap: 24px;
  min-height: 116px;
  padding: 22px 26px;
  background: #eef5f1;
  border-top: 1px solid #d5e4da;
  border-bottom: 1px solid #d5e4da;
  border-left: 4px solid var(--primary);
}

.path-band h2 {
  margin-top: 5px;
  color: var(--ink);
  font-size: 20px;
}

.recommended-types {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
}

.recommended-types > span,
.weakest-focus > span {
  width: 100%;
  color: var(--muted);
  font-size: 10px;
}

.weakest-focus {
  display: grid;
  gap: 5px;
  text-align: right;
}

.weakest-focus strong {
  color: var(--primary-strong);
  font-size: 15px;
}

.learning-workspace {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 18px;
  margin-top: 20px;
  align-items: start;
}

.practice-panel > header,
.followup-panel > header,
.answer-history > header {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 70px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--line);
}

.panel-icon {
  display: grid;
  width: 38px;
  height: 38px;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 6px;
  place-items: center;
}

.panel-icon.blue {
  color: var(--blue);
  background: var(--blue-soft);
}

.practice-panel header > div:last-child,
.followup-panel header > div:last-child {
  display: grid;
  gap: 3px;
}

.practice-panel header span,
.followup-panel header span {
  color: var(--muted);
  font-size: 10px;
}

.practice-panel h2,
.followup-panel h2,
.answer-history h2 {
  color: var(--ink);
  font-size: 15px;
}

.practice-body,
.followup-form {
  display: grid;
  gap: 14px;
  padding: 20px;
}

.practice-body h3 {
  color: var(--ink);
  font-size: 15px;
  line-height: 1.7;
}

.practice-options {
  display: grid;
  gap: 8px;
}

.practice-option {
  min-height: 50px;
  margin: 0;
  padding: 12px;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  border-radius: 6px;
}

.practice-option:has(.n-radio--checked) {
  background: var(--primary-soft);
  border-color: #bcd8c8;
}

.practice-option :deep(.n-radio__label) {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  white-space: normal;
}

.practice-option b {
  color: var(--primary);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 11px;
}

.practice-option span {
  color: #35433b;
  font-size: 12px;
}

.practice-feedback {
  padding: 14px;
  color: #82591e;
  background: var(--amber-soft);
  border-left: 3px solid var(--amber);
}

.practice-feedback.correct {
  color: var(--primary-strong);
  background: var(--primary-soft);
  border-left-color: var(--primary);
}

.practice-feedback strong {
  font-size: 12px;
}

.practice-feedback p {
  margin-top: 5px;
  color: #56635b;
  font-size: 11px;
  line-height: 1.65;
}

.generated-followup {
  margin: 0 20px 20px;
  padding-top: 18px;
  border-top: 1px solid var(--line);
}

.generated-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.generated-title > div {
  display: grid;
  gap: 3px;
}

.generated-title span {
  color: var(--muted);
  font-size: 10px;
}

.generated-title strong {
  color: var(--ink);
  font-size: 14px;
}

.generated-content {
  max-height: 260px;
  margin-top: 12px;
  padding: 14px;
  overflow-y: auto;
  color: #435048;
  background: var(--surface-soft);
  font-size: 11px;
  line-height: 1.75;
  white-space: pre-wrap;
}

.review-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 11px;
  color: var(--muted);
  font-size: 11px;
}

.review-line svg,
.review-line strong {
  color: var(--primary);
}

.answer-history {
  margin-top: 18px;
}

.answer-history > header {
  justify-content: space-between;
}

.answer-history > header > div {
  display: flex;
  align-items: center;
  gap: 9px;
}

.answer-history > header svg {
  color: var(--primary);
}

.answer-history > header > span {
  color: var(--muted);
  font-size: 11px;
}

.history-list {
  display: grid;
}

.history-row {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) 70px 110px;
  align-items: center;
  gap: 12px;
  min-height: 60px;
  padding: 9px 18px;
  border-bottom: 1px solid var(--line);
}

.history-row:last-child {
  border-bottom: 0;
}

.history-state {
  width: 7px;
  height: 7px;
  background: var(--amber);
  border-radius: 50%;
}

.history-state.success {
  background: var(--primary);
}

.history-row > div {
  display: grid;
  gap: 2px;
}

.history-row strong {
  color: var(--ink);
  font-size: 12px;
}

.history-row small,
.history-row time {
  color: var(--subtle);
  font-size: 10px;
}

.history-row b {
  color: var(--primary);
  font-size: 11px;
}

.history-empty {
  display: grid;
  min-height: 140px;
  color: var(--muted);
  font-size: 12px;
  place-items: center;
}

@media (max-width: 980px) {
  .path-band,
  .learning-workspace {
    grid-template-columns: 1fr;
  }

  .weakest-focus {
    text-align: left;
  }
}

@media (max-width: 620px) {
  .history-row {
    grid-template-columns: 8px minmax(0, 1fr) 60px;
  }

  .history-row time {
    grid-column: 2 / -1;
  }
}
</style>
