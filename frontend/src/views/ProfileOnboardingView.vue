<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  NAlert,
  NButton,
  NForm,
  NFormItem,
  NInput,
  NRadio,
  NRadioGroup,
  NSelect,
  NSpin,
  NStep,
  NSteps,
  NTag,
  useMessage,
} from 'naive-ui'
import { ArrowLeft, ArrowRight, Check, ClipboardCheck, UserRound } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { InitialQuestion, LearnerProfile, ProfilePayload } from '../types/api'
import { dimensionLabels, getErrorMessage, isHttpStatus } from '../utils/format'

interface QuestionCopy {
  stem: string
  options: Record<string, string>
}

const questionCatalog: Record<string, QuestionCopy> = {
  initial_1_1: {
    stem: '黄芪的法定植物来源主要是下列哪一组？',
    options: { A: '蒙古黄芪或膜荚黄芪的干燥根', B: '伞形科植物当归的干燥根' },
  },
  initial_1_2: {
    stem: '中药饮片性状鉴别通常首先关注哪些信息？',
    options: { A: '形状、大小、表面、断面、气味', B: '只关注包装上的商品名称' },
  },
  initial_2_1: {
    stem: '黄芪饮片常见的断面特征是？',
    options: { A: '皮部黄白、木部淡黄并有放射状纹理', B: '断面乌黑且有强烈油腻光泽' },
  },
  initial_2_2: {
    stem: '观察饮片切面纹理时，较规范的做法是？',
    options: { A: '在自然或中性光下观察新鲜切面', B: '隔着有色包装凭印象判断' },
  },
  initial_3_1: {
    stem: '区分外形相近饮片时，最可靠的处理是？',
    options: { A: '联合表面、切面、质地和气味进行比对', B: '只凭颜色深浅直接下结论' },
  },
  initial_3_2: {
    stem: '候选药材置信度接近且性状相似时，应当？',
    options: { A: '进入复核并检索相似饮片辨析依据', B: '选择排序第一项且不保留证据' },
  },
  initial_4_1: {
    stem: '引用药典依据时，哪项记录最重要？',
    options: { A: '版本、品名、条目位置和原文证据', B: '只记录网络搜索结果标题' },
  },
  initial_4_2: {
    stem: '饮片结论与现行药典描述不一致时，应当？',
    options: { A: '标记冲突并进入人工复核', B: '删除药典证据以保留原结论' },
  },
  initial_5_1: {
    stem: '发现饮片受潮、霉变或虫蛀迹象时，正确做法是？',
    options: { A: '隔离样品并记录质量风险', B: '与合格样品混放后继续使用' },
  },
  initial_5_2: {
    stem: '质量控制结论应优先建立在什么基础上？',
    options: { A: '可追溯检测或性状证据', B: '未经核验的经验性描述' },
  },
  initial_6_1: {
    stem: '拍摄饮片用于识别时，哪种方式更合适？',
    options: { A: '主体清晰、光线均匀并保留尺度参照', B: '强反光、严重遮挡且画面模糊' },
  },
  initial_6_2: {
    stem: '完成一次实操辨识后，复盘应包含？',
    options: { A: '候选、置信度、依据、错误点和改进动作', B: '只保留最终药名' },
  },
}

const router = useRouter()
const auth = useAuthStore()
const message = useMessage()
const currentStep = ref(1)
const loading = ref(true)
const saving = ref(false)
const submitting = ref(false)
const errorText = ref('')
const existingProfile = ref<LearnerProfile | null>(null)
const questions = ref<InitialQuestion[]>([])
const answers = reactive<Record<number, string>>({})

const form = reactive({
  name: auth.user?.display_name || auth.user?.username || '',
  identityType: 'pharmacy_student',
  educationLevel: '本科',
  major: '中药学',
  professionalDirection: '中药鉴定与质量评价',
  practiceExperience: '接触过基础饮片辨识',
  learningGoal: '',
  resourcePreference: '图文讲义与辨析卡',
  learningRhythm: '每次 20-30 分钟',
})

const identityOptions = [
  { label: '中药学学生', value: 'pharmacy_student' },
  { label: '药学相关学生', value: 'pharmacy_related_student' },
  { label: '中药从业人员', value: 'practitioner' },
  { label: '质量检验人员', value: 'quality_inspector' },
  { label: '继续教育学习者', value: 'continuing_learner' },
]
const educationOptions = ['中专', '大专', '本科', '硕士及以上', '在职继续教育'].map(value => ({
  label: value,
  value,
}))
const directionOptions = ['中药鉴定与质量评价', '中药炮制', '中药调剂', '临床中药学', '药材生产与流通'].map(
  value => ({ label: value, value }),
)
const experienceOptions = ['尚无实操经验', '接触过基础饮片辨识', '完成过课程实训', '有岗位实操经验'].map(value => ({
  label: value,
  value,
}))
const resourceOptions = ['图文讲义与辨析卡', '实操指南与任务单', '分阶测试与即时反馈', '综合报告与复盘'].map(value => ({
  label: value,
  value,
}))
const rhythmOptions = ['每次 10-15 分钟', '每次 20-30 分钟', '每次 45-60 分钟'].map(value => ({
  label: value,
  value,
}))

const answeredCount = computed(() => questions.value.filter(question => answers[question.id]).length)
const canContinueBasic = computed(() => Boolean(form.name.trim() && form.major.trim()))
const canContinueExperience = computed(() => Boolean(form.learningGoal.trim()))
const allAnswered = computed(() => Boolean(questions.value.length && answeredCount.value === questions.value.length))

function questionCopy(question: InitialQuestion): QuestionCopy {
  return (
    questionCatalog[question.question_code] || {
      stem: `${dimensionLabels[question.dimension_code] || '专业能力'}：请选择更符合规范的处理方式。`,
      options: { A: '依据标准流程核验并保留证据', B: '跳过核验直接形成结论' },
    }
  )
}

function profilePayload(): ProfilePayload {
  return {
    learner_id: auth.learnerId,
    user_id: auth.user?.id,
    name: form.name.trim(),
    identity_type: form.identityType,
    education_background: `${form.educationLevel} · ${form.major.trim()}`.slice(0, 255),
    professional_background: `${form.professionalDirection} · 实操经验：${form.practiceExperience}`.slice(0, 255),
    learning_goal: form.learningGoal.trim(),
    learning_preference: `${form.resourcePreference} · ${form.learningRhythm}`.slice(0, 64),
  }
}

function hydrateProfile(profile: LearnerProfile): void {
  form.name = profile.name || form.name
  form.identityType = profile.identity_type || form.identityType
  const [educationLevel, major] = (profile.education_background || '').split(' · ')
  if (educationLevel) form.educationLevel = educationLevel
  if (major) form.major = major
  const [direction, experience] = (profile.professional_background || '').split(' · 实操经验：')
  if (direction) form.professionalDirection = direction
  if (experience) form.practiceExperience = experience
  form.learningGoal = profile.learning_goal || ''
  const [preference, rhythm] = (profile.learning_preference || '').split(' · ')
  if (preference) form.resourcePreference = preference
  if (rhythm) form.learningRhythm = rhythm
}

async function saveProfile(): Promise<void> {
  const payload = profilePayload()
  if (existingProfile.value) {
    existingProfile.value = await api.updateProfile(auth.learnerId, {
      name: payload.name,
      identity_type: payload.identity_type,
      education_background: payload.education_background,
      professional_background: payload.professional_background,
      learning_goal: payload.learning_goal,
      learning_preference: payload.learning_preference,
    })
  } else {
    existingProfile.value = await api.createProfile(payload)
  }
}

async function nextStep(): Promise<void> {
  errorText.value = ''
  if (currentStep.value === 1) {
    if (!canContinueBasic.value) {
      errorText.value = '请补全姓名和专业背景'
      return
    }
    currentStep.value = 2
    return
  }
  if (!canContinueExperience.value) {
    errorText.value = '请填写本阶段的学习目标'
    return
  }
  saving.value = true
  try {
    await saveProfile()
    if (!questions.value.length) questions.value = await api.getInitialQuestions()
    currentStep.value = 3
    message.success('画像信息已保存')
  } catch (error) {
    errorText.value = getErrorMessage(error, '画像保存失败')
  } finally {
    saving.value = false
  }
}

async function submitAssessment(): Promise<void> {
  if (!allAnswered.value) {
    errorText.value = `还有 ${questions.value.length - answeredCount.value} 道题未完成`
    return
  }
  submitting.value = true
  errorText.value = ''
  try {
    await saveProfile()
    const result = await api.submitInitialTest(
      auth.learnerId,
      questions.value.map(question => ({ question_id: question.id, answer: answers[question.id] })),
    )
    sessionStorage.setItem('herbwise.last_diagnosis', JSON.stringify(result.diagnosis))
    sessionStorage.setItem('herbwise.last_initial_score', String(result.total_score))
    message.success('学习画像已构建')
    await router.replace({ path: '/diagnosis', query: { fresh: '1' } })
  } catch (error) {
    errorText.value = getErrorMessage(error, '理论测试提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    existingProfile.value = await api.getProfile(auth.learnerId)
    hydrateProfile(existingProfile.value)
  } catch (error) {
    if (!isHttpStatus(error, 404)) errorText.value = getErrorMessage(error, '画像信息加载失败')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page onboarding-page">
    <PageHeader title="构建学习画像" eyebrow="学习准备" :meta="`学习者 ${auth.learnerId}`">
      <template #actions>
        <n-button v-if="existingProfile" secondary @click="router.push('/diagnosis')">
          当前诊断
          <template #icon><ClipboardCheck :size="17" /></template>
        </n-button>
      </template>
    </PageHeader>

    <section class="onboarding-progress" aria-label="画像构建进度">
      <n-steps :current="currentStep" size="small">
        <n-step title="身份与背景" />
        <n-step title="经验与目标" />
        <n-step title="理论测试" />
      </n-steps>
    </section>

    <n-alert v-if="errorText" type="error" :bordered="false" closable class="form-alert" @close="errorText = ''">
      {{ errorText }}
    </n-alert>

    <n-spin :show="loading">
      <section v-if="currentStep === 1" class="onboarding-form surface">
        <div class="form-intro">
          <span class="step-number">01</span>
          <div>
            <h2>身份与专业背景</h2>
            <p>用于确定知识起点和专业语境</p>
          </div>
          <UserRound :size="24" />
        </div>
        <n-form :model="form" label-placement="top" size="large" class="form-grid">
          <n-form-item label="姓名或称呼" required>
            <n-input v-model:value="form.name" maxlength="128" placeholder="请输入姓名或称呼" />
          </n-form-item>
          <n-form-item label="身份角色" required>
            <n-select v-model:value="form.identityType" :options="identityOptions" />
          </n-form-item>
          <n-form-item label="教育阶段" required>
            <n-select v-model:value="form.educationLevel" :options="educationOptions" />
          </n-form-item>
          <n-form-item label="专业或方向" required>
            <n-input v-model:value="form.major" maxlength="100" placeholder="如：中药学" />
          </n-form-item>
        </n-form>
      </section>

      <section v-else-if="currentStep === 2" class="onboarding-form surface">
        <div class="form-intro">
          <span class="step-number">02</span>
          <div>
            <h2>实操经验与学习目标</h2>
            <p>用于匹配任务难度和资源形式</p>
          </div>
          <n-tag size="small" :bordered="false" type="success">画像采集</n-tag>
        </div>
        <n-form :model="form" label-placement="top" size="large" class="form-grid">
          <n-form-item label="专业方向" required>
            <n-select v-model:value="form.professionalDirection" :options="directionOptions" />
          </n-form-item>
          <n-form-item label="实操经验" required>
            <n-select v-model:value="form.practiceExperience" :options="experienceOptions" />
          </n-form-item>
          <n-form-item label="偏好资源" required>
            <n-select v-model:value="form.resourcePreference" :options="resourceOptions" />
          </n-form-item>
          <n-form-item label="学习节奏" required>
            <n-select v-model:value="form.learningRhythm" :options="rhythmOptions" />
          </n-form-item>
          <n-form-item label="学习目标" required class="wide-field">
            <n-input
              v-model:value="form.learningGoal"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 5 }"
              placeholder="例如：能够独立辨析常见相似饮片，并掌握药典性状依据"
            />
          </n-form-item>
        </n-form>
      </section>

      <section v-else class="assessment-layout">
        <aside class="assessment-summary surface">
          <span class="step-number">03</span>
          <h2>理论基础测试</h2>
          <strong>{{ answeredCount }} / {{ questions.length }}</strong>
          <div class="dimension-summary">
            <span v-for="code in [...new Set(questions.map(item => item.dimension_code))]" :key="code">
              {{ dimensionLabels[code] || code }}
            </span>
          </div>
        </aside>
        <div class="question-list">
          <article v-for="(question, index) in questions" :key="question.id" class="question-item surface">
            <header>
              <span>{{ String(index + 1).padStart(2, '0') }}</span>
              <n-tag size="small" :bordered="false">{{ dimensionLabels[question.dimension_code] }}</n-tag>
            </header>
            <h3>{{ questionCopy(question).stem }}</h3>
            <n-radio-group v-model:value="answers[question.id]" class="answer-options">
              <n-radio v-for="option in question.options" :key="option.key" :value="option.key" class="answer-option">
                <span class="option-key">{{ option.key }}</span>
                <span>{{ questionCopy(question).options[option.key] || option.text }}</span>
              </n-radio>
            </n-radio-group>
          </article>
        </div>
      </section>
    </n-spin>

    <footer class="onboarding-actions">
      <n-button v-if="currentStep > 1" secondary size="large" @click="currentStep -= 1">
        上一步
        <template #icon><ArrowLeft :size="18" /></template>
      </n-button>
      <span v-else />
      <n-button v-if="currentStep < 3" type="primary" size="large" :loading="saving" @click="nextStep">
        下一步
        <template #icon><ArrowRight :size="18" /></template>
      </n-button>
      <n-button v-else type="primary" size="large" :loading="submitting" :disabled="!allAnswered" @click="submitAssessment">
        完成画像
        <template #icon><Check :size="18" /></template>
      </n-button>
    </footer>
  </div>
</template>

<style scoped>
.onboarding-page {
  max-width: 1180px;
}

.onboarding-progress {
  padding: 18px 22px;
  background: #fff;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}

.form-alert {
  margin-top: 16px;
}

.onboarding-form {
  margin-top: 20px;
}

.form-intro {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  min-height: 92px;
  padding: 18px 22px;
  border-bottom: 1px solid var(--line);
}

.step-number {
  color: var(--primary);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 14px;
  font-weight: 700;
}

.form-intro h2,
.assessment-summary h2 {
  color: var(--ink);
  font-size: 18px;
  line-height: 1.4;
}

.form-intro p {
  margin-top: 3px;
  color: var(--muted);
  font-size: 12px;
}

.form-intro > svg {
  color: var(--primary);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 20px;
  padding: 24px 22px 8px;
}

.wide-field {
  grid-column: 1 / -1;
}

.assessment-layout {
  display: grid;
  grid-template-columns: 230px minmax(0, 1fr);
  align-items: start;
  gap: 18px;
  margin-top: 20px;
}

.assessment-summary {
  position: sticky;
  top: 84px;
  display: grid;
  gap: 12px;
  padding: 22px;
}

.assessment-summary > strong {
  color: var(--primary-strong);
  font-size: 34px;
  line-height: 1;
}

.dimension-summary {
  display: grid;
  gap: 7px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}

.dimension-summary span {
  color: var(--muted);
  font-size: 11px;
}

.question-list {
  display: grid;
  gap: 12px;
}

.question-item {
  padding: 20px;
}

.question-item header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.question-item header > span {
  color: var(--subtle);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 11px;
}

.question-item h3 {
  margin: 12px 0 16px;
  color: var(--ink);
  font-size: 15px;
  line-height: 1.65;
  font-weight: 650;
}

.answer-options {
  display: grid;
  gap: 8px;
}

.answer-option {
  display: flex;
  min-height: 48px;
  margin: 0;
  padding: 11px 13px;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  border-radius: 6px;
}

.answer-option:has(.n-radio--checked) {
  background: var(--primary-soft);
  border-color: #bcd8c8;
}

.answer-option :deep(.n-radio__label) {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
  white-space: normal;
}

.option-key {
  color: var(--primary);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 11px;
  font-weight: 700;
}

.onboarding-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid var(--line);
}

@media (max-width: 820px) {
  .assessment-layout {
    grid-template-columns: 1fr;
  }

  .assessment-summary {
    position: static;
  }

  .dimension-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 620px) {
  .onboarding-progress {
    padding-inline: 8px;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .wide-field {
    grid-column: auto;
  }

  .form-intro {
    grid-template-columns: 36px minmax(0, 1fr);
  }

  .form-intro > svg,
  .form-intro > .n-tag {
    display: none;
  }

  .dimension-summary {
    grid-template-columns: 1fr;
  }

  .onboarding-actions > .n-button {
    min-width: 0;
    flex: 1;
  }
}
</style>
