<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NAlert, NButton, NRadio, NRadioGroup, NSpin, useMessage } from 'naive-ui'
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  Microscope,
  RotateCcw,
  ShieldCheck,
} from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import SourceBadge from '../components/SourceBadge.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { DimensionCode, KnowledgeEvidence } from '../types/api'
import { getErrorMessage } from '../utils/format'

interface Scenario {
  id: string
  title: string
  category: string
  medicine: string
  dimension: DimensionCode
  brief: string
  observation: string[]
  question: string
  options: Array<{ key: string; text: string }>
  correct: string
  explanation: string
  icon: typeof Microscope
}

const scenarios: Scenario[] = [
  {
    id: 'character-check',
    title: '黄芪饮片性状鉴别',
    category: '基础实操',
    medicine: '黄芪',
    dimension: 'character_identification',
    brief: '依据表面、切面与质地信息完成初步判断。',
    observation: ['饮片呈类圆形或椭圆形', '外表皮淡棕黄色', '切面皮部黄白色并见放射状纹理'],
    question: '哪组证据最能支持黄芪饮片的性状判断？',
    options: [
      { key: 'A', text: '皮部黄白、木部淡黄，并可见放射状纹理' },
      { key: 'B', text: '切面乌黑油润，具有强烈辛辣气味' },
      { key: 'C', text: '仅根据包装标签判断，不观察饮片本体' },
    ],
    correct: 'A',
    explanation: '应联合切面颜色、纹理和质地形成性状证据，不能只依赖标签或单一颜色。',
    icon: Microscope,
  },
  {
    id: 'similar-review',
    title: '相似饮片低置信度复核',
    category: '复核决策',
    medicine: '黄芪',
    dimension: 'similar_medicine',
    brief: '两个候选置信度接近，需要决定下一步复核动作。',
    observation: ['候选一置信度 0.63', '候选二置信度 0.59', '样本局部存在遮挡'],
    question: '此时最合适的处置是？',
    options: [
      { key: 'A', text: '补拍清晰切面，并检索相似饮片辨析依据后复核' },
      { key: 'B', text: '直接采用候选一，不记录不确定性' },
      { key: 'C', text: '删除置信度信息，仅保留最终药名' },
    ],
    correct: 'A',
    explanation: '低置信度且候选接近时，应补充图像和药典证据，再由复核与裁判模块形成结论。',
    icon: RotateCcw,
  },
  {
    id: 'quality-control',
    title: '饮片质量风险处置',
    category: '质量控制',
    medicine: '黄芪',
    dimension: 'clinical_quality_control',
    brief: '样本出现受潮和疑似霉点，需要给出质量控制动作。',
    observation: ['包装内壁有水汽', '局部可见异常斑点', '气味与合格对照样不同'],
    question: '第一步应如何处理？',
    options: [
      { key: 'A', text: '隔离样本、记录异常并进入质量复核' },
      { key: 'B', text: '与合格饮片混匀后继续使用' },
      { key: 'C', text: '只擦除表面斑点，不保留记录' },
    ],
    correct: 'A',
    explanation: '存在受潮或霉变风险时必须先隔离并留痕，再依据质量标准完成复核。',
    icon: ShieldCheck,
  },
]

const router = useRouter()
const auth = useAuthStore()
const message = useMessage()
const active = ref<Scenario | null>(null)
const answer = ref('')
const loadingEvidence = ref(false)
const submitting = ref(false)
const completed = ref(false)
const errorText = ref('')
const evidences = ref<KnowledgeEvidence[]>([])

const correct = computed(() => Boolean(active.value && answer.value === active.value.correct))

async function startScenario(scenario: Scenario): Promise<void> {
  active.value = scenario
  answer.value = ''
  completed.value = false
  evidences.value = []
  errorText.value = ''
  loadingEvidence.value = true
  try {
    const result = await api.retrieveKnowledge({
      learner_id: auth.learnerId,
      medicine_name: scenario.medicine,
      task_type: 'simulation_training',
      query: `${scenario.title} 性状 炮制 相似饮片 质量控制`,
      top_k: 4,
    })
    evidences.value = result.evidences
  } catch (error) {
    errorText.value = getErrorMessage(error, '知识依据暂时未能载入，可继续完成实训')
  } finally {
    loadingEvidence.value = false
  }
}

async function submit(): Promise<void> {
  if (!active.value || !answer.value) return
  submitting.value = true
  errorText.value = ''
  try {
    await api.submitLearningAnswer({
      learner_id: auth.learnerId,
      dimension_code: active.value.dimension,
      knowledge_point: active.value.title,
      answer: { value: answer.value, scenario_id: active.value.id },
      is_correct: correct.value,
      score: correct.value ? 100 : 0,
      feedback: active.value.explanation,
    })
    await api.updateLearningPath(auth.learnerId)
    completed.value = true
    message.success('实训结果已写入学习画像')
  } catch (error) {
    errorText.value = getErrorMessage(error, '实训结果提交失败')
  } finally {
    submitting.value = false
  }
}

function backToScenarios(): void {
  active.value = null
  answer.value = ''
  completed.value = false
  evidences.value = []
  errorText.value = ''
}
</script>

<template>
  <div class="page simulation-page">
    <PageHeader title="虚拟仿真实训" eyebrow="视觉实训" :meta="active?.category || '任务场景'">
      <template #actions>
        <n-button v-if="active" secondary @click="backToScenarios">
          返回任务列表
          <template #icon><ArrowLeft :size="17" /></template>
        </n-button>
      </template>
    </PageHeader>

    <n-alert v-if="errorText" type="warning" :bordered="false" closable class="simulation-alert" @close="errorText = ''">
      {{ errorText }}
    </n-alert>

    <section v-if="!active" class="scenario-grid">
      <article v-for="scenario in scenarios" :key="scenario.id" class="scenario-card">
        <div class="scenario-icon"><component :is="scenario.icon" :size="22" /></div>
        <span>{{ scenario.category }}</span>
        <h2>{{ scenario.title }}</h2>
        <p>{{ scenario.brief }}</p>
        <n-button secondary block @click="startScenario(scenario)">
          进入任务
          <template #icon><ArrowRight :size="16" /></template>
        </n-button>
      </article>
    </section>

    <section v-else class="simulation-workspace">
      <div class="sample-panel">
        <div class="sample-image">
          <img src="/images/herbal-workbench.png" :alt="`${active.medicine}实训样本`" />
          <span>训练样本</span>
        </div>
        <div class="observation-panel">
          <span class="eyebrow">观察记录</span>
          <h2>{{ active.title }}</h2>
          <ol>
            <li v-for="item in active.observation" :key="item">{{ item }}</li>
          </ol>
        </div>
      </div>

      <div class="decision-workspace">
        <section class="decision-panel surface">
          <header>
            <ClipboardCheck :size="20" />
            <div><span>实训决策</span><strong>{{ active.question }}</strong></div>
          </header>
          <n-radio-group v-model:value="answer" class="simulation-options" :disabled="completed">
            <n-radio v-for="option in active.options" :key="option.key" :value="option.key" class="simulation-option">
              <b>{{ option.key }}</b>
              <span>{{ option.text }}</span>
            </n-radio>
          </n-radio-group>
          <div v-if="completed" class="feedback-panel" :class="{ correct }">
            <CheckCircle2 v-if="correct" :size="20" />
            <RotateCcw v-else :size="20" />
            <div>
              <strong>{{ correct ? '判断正确' : '本次判断需要复核' }}</strong>
              <p>{{ active.explanation }}</p>
            </div>
          </div>
          <n-button
            v-if="!completed"
            type="primary"
            size="large"
            block
            :disabled="!answer"
            :loading="submitting"
            @click="submit"
          >
            提交实训结果
          </n-button>
          <div v-else class="completion-actions">
            <n-button secondary @click="backToScenarios">选择其他任务</n-button>
            <n-button type="primary" @click="router.push('/learning-tasks')">
              下一步任务
              <template #icon><ArrowRight :size="17" /></template>
            </n-button>
          </div>
        </section>

        <section class="evidence-panel surface">
          <header>
            <div><span>药典知识依据</span><strong>{{ active.medicine }}</strong></div>
            <SourceBadge source="knowledge" />
          </header>
          <n-spin :show="loadingEvidence">
            <div v-if="evidences.length" class="simulation-evidence-list">
              <article v-for="(item, index) in evidences" :key="item.evidence_id || index">
                <span>{{ String(index + 1).padStart(2, '0') }}</span>
                <div>
                  <strong>{{ item.document_name || item.citation || '知识条目' }}</strong>
                  <p>{{ item.content || '暂无摘要' }}</p>
                </div>
              </article>
            </div>
            <div v-else class="evidence-empty">暂无可展示的检索证据</div>
          </n-spin>
        </section>
      </div>
    </section>
  </div>
</template>

<style scoped>
.simulation-alert {
  margin-bottom: 16px;
}

.scenario-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.scenario-card {
  display: grid;
  grid-template-rows: auto auto auto 1fr auto;
  gap: 11px;
  min-height: 300px;
  padding: 22px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.scenario-card:hover {
  border-color: #b9cfc1;
  box-shadow: var(--shadow-soft);
}

.scenario-icon {
  display: grid;
  width: 42px;
  height: 42px;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 6px;
  place-items: center;
}

.scenario-card > span {
  color: var(--primary);
  font-size: 11px;
  font-weight: 700;
}

.scenario-card h2 {
  color: var(--ink);
  font-size: 17px;
  line-height: 1.5;
}

.scenario-card p {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.75;
}

.simulation-workspace {
  display: grid;
  gap: 18px;
}

.sample-panel {
  display: grid;
  grid-template-columns: minmax(320px, 0.9fr) minmax(360px, 1.1fr);
  min-height: 300px;
  overflow: hidden;
  background: #17211c;
}

.sample-image {
  position: relative;
  min-height: 300px;
}

.sample-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sample-image > span {
  position: absolute;
  bottom: 14px;
  left: 14px;
  padding: 5px 8px;
  color: #fff;
  background: rgba(23, 33, 28, 0.82);
  border-radius: 4px;
  font-size: 10px;
}

.observation-panel {
  display: grid;
  align-content: center;
  gap: 10px;
  padding: 30px;
  color: #fff;
}

.observation-panel .eyebrow {
  color: #8dc6a6;
}

.observation-panel h2 {
  font-size: 21px;
}

.observation-panel ol {
  display: grid;
  gap: 9px;
  margin: 6px 0 0;
  padding-left: 20px;
  color: #dce6df;
  font-size: 12px;
  line-height: 1.7;
}

.decision-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(340px, 0.9fr);
  gap: 18px;
  align-items: start;
}

.decision-panel,
.evidence-panel {
  padding: 20px;
}

.decision-panel > header,
.evidence-panel > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);
}

.decision-panel > header {
  justify-content: flex-start;
}

.decision-panel > header svg {
  color: var(--primary);
}

.decision-panel header div,
.evidence-panel header div {
  display: grid;
  gap: 3px;
}

.decision-panel header span,
.evidence-panel header span {
  color: var(--muted);
  font-size: 10px;
}

.decision-panel header strong,
.evidence-panel header strong {
  color: var(--ink);
  font-size: 14px;
  line-height: 1.5;
}

.simulation-options {
  display: grid;
  gap: 9px;
  margin: 18px 0;
}

.simulation-option {
  min-height: 54px;
  margin: 0;
  padding: 13px;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  border-radius: 6px;
}

.simulation-option:has(.n-radio--checked) {
  background: var(--primary-soft);
  border-color: #bcd8c8;
}

.simulation-option :deep(.n-radio__label) {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  white-space: normal;
}

.simulation-option b {
  color: var(--primary);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 11px;
}

.simulation-option span {
  color: #35433b;
  font-size: 12px;
  line-height: 1.6;
}

.feedback-panel {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 10px;
  margin: 16px 0;
  padding: 15px;
  color: var(--amber);
  background: var(--amber-soft);
  border: 1px solid #ead5aa;
}

.feedback-panel.correct {
  color: var(--primary);
  background: var(--primary-soft);
  border-color: #cbe0d3;
}

.feedback-panel strong {
  font-size: 13px;
}

.feedback-panel p {
  margin-top: 4px;
  color: #56635b;
  font-size: 11px;
  line-height: 1.7;
}

.completion-actions {
  display: flex;
  justify-content: flex-end;
  gap: 9px;
}

.simulation-evidence-list {
  display: grid;
}

.simulation-evidence-list article {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 10px;
  padding: 15px 0;
  border-bottom: 1px solid var(--line);
}

.simulation-evidence-list article > span {
  color: var(--subtle);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 9px;
}

.simulation-evidence-list strong {
  color: var(--ink);
  font-size: 12px;
}

.simulation-evidence-list p {
  display: -webkit-box;
  margin-top: 5px;
  overflow: hidden;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.evidence-empty {
  display: grid;
  min-height: 180px;
  color: var(--muted);
  font-size: 12px;
  place-items: center;
}

@media (max-width: 980px) {
  .scenario-grid {
    grid-template-columns: 1fr;
  }

  .scenario-card {
    min-height: 240px;
  }

  .decision-workspace {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .sample-panel {
    grid-template-columns: 1fr;
  }

  .sample-image {
    min-height: 230px;
  }

  .observation-panel {
    padding: 22px;
  }

  .completion-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
