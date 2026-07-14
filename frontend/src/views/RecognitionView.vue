<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  NAlert,
  NButton,
  NEmpty,
  NProgress,
  NSpin,
  NTabPane,
  NTabs,
  NTag,
  NTooltip,
  useMessage,
} from 'naive-ui'
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  Circle,
  ImagePlus,
  LoaderCircle,
  Play,
  RefreshCw,
  ScanSearch,
  UploadCloud,
} from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import { useModelSettingsStore } from '../stores/model-settings'
import type {
  AgentTask,
  CapabilityStatus,
  RecognitionCandidate,
  RecognitionEvidence,
  RecognitionRecord,
  TaskEvent,
  VisionRecognitionResult,
} from '../types/api'
import {
  formatDate,
  formatDuration,
  formatPercent,
  formatRuntimeText,
  getErrorMessage,
  isHttpStatus,
} from '../utils/format'

type NodeState = 'pending' | 'running' | 'success' | 'failed'
type CaptureMode = 'upload' | 'camera' | 'simulation'
type PipelineStatus = { status?: string; confidence?: number }

const router = useRouter()
const auth = useAuthStore()
const modelSettings = useModelSettingsStore()
const message = useMessage()
const selectedFile = ref<File | null>(null)
const previewUrl = ref('')
const objectUrl = ref('')
const captureMode = ref<CaptureMode>('upload')
const cameraStarting = ref(false)
const cameraFrozen = ref(false)
const videoElement = ref<HTMLVideoElement | null>(null)
const cameraStream = ref<MediaStream | null>(null)
const imageNaturalWidth = ref(0)
const imageNaturalHeight = ref(0)
const capabilities = ref<CapabilityStatus | null>(null)
const capabilitiesLoading = ref(true)
const starting = ref(false)
const loadingTask = ref(false)
const dragActive = ref(false)
const errorText = ref('')
const agentErrorText = ref('')
const task = ref<AgentTask | null>(null)
const recognitionRecord = ref<RecognitionRecord | null>(null)
const events = ref<TaskEvent[]>([])
const announcedTaskId = ref('')
let pollTimer: ReturnType<typeof setTimeout> | null = null

const workflowNodes = [
  { code: 'upload_image', label: '图片上传', progress: 20 },
  { code: 'recognize_image', label: '智能辨识', progress: 50 },
  { code: 'normalize_name', label: '名称与知识核验', progress: 80 },
  { code: 'persist_recognition', label: '识别完成', progress: 100 },
]

const fusionResult = computed(
  () => recognitionRecord.value?.fusion_result || null,
)
const finalIdentification = computed<PipelineStatus | null>(
  () => (fusionResult.value?.final_identification || recognitionRecord.value?.final_identification || null) as PipelineStatus | null,
)
const knowledgeMatch = computed<PipelineStatus | null>(
  () => (fusionResult.value?.knowledge_match || recognitionRecord.value?.knowledge_match || null) as PipelineStatus | null,
)
const knowledgeVerification = computed<PipelineStatus | null>(
  () => (fusionResult.value?.knowledge_verification || recognitionRecord.value?.knowledge_verification || null) as PipelineStatus | null,
)
const yoloReference = computed<VisionRecognitionResult | null>(
  () => (fusionResult.value?.yolo_reference || recognitionRecord.value?.yolo_reference || null) as VisionRecognitionResult | null,
)
const candidate = computed<RecognitionCandidate | null>(() => {
  const result = fusionResult.value?.final_candidate
  if (result) return result
  if (!recognitionRecord.value?.final_name) return null
  return {
    medicine_id: recognitionRecord.value.final_medicine_id,
    herb_name: recognitionRecord.value.final_name,
    confidence: recognitionRecord.value.confidence || 0,
  }
})
const localVisionResult = computed<VisionRecognitionResult | null>(() => {
  const result = fusionResult.value?.local_result || recognitionRecord.value?.local_result || recognitionRecord.value?.yolo_reference
  if (result) return result
  return null
})
const cloudVisionResult = computed<VisionRecognitionResult | null>(() => {
  const result = fusionResult.value?.qwen_result || recognitionRecord.value?.qwen_result
  if (result) return result
  return null
})
const topCandidates = computed(() => {
  const local = localVisionResult.value?.top_candidates || []
  if (local.length) return local
  const cloud = cloudVisionResult.value?.top_candidates || []
  if (cloud.length) return cloud
  return []
})
const cloudCandidates = computed(() => cloudVisionResult.value?.top_candidates || [])
const characterEvidence = computed<RecognitionEvidence[]>(() => cloudVisionResult.value?.character_evidence || [])
const qualityEvidence = computed<RecognitionEvidence[]>(() => cloudVisionResult.value?.quality_control_evidence || [])
const traceabilityAdvice = computed(() => cloudVisionResult.value?.traceability_advice || [])
const visionEvidenceCount = computed(() => characterEvidence.value.length + qualityEvidence.value.length)
const manualReviewRequired = computed(
  () =>
    Boolean(fusionResult.value?.manual_review_required) ||
    Boolean(recognitionRecord.value?.manual_review_required) ||
    Boolean(candidate.value && (candidate.value.confidence || 0) < 0.5),
)
const terminal = computed(() => Boolean(recognitionRecord.value))
const recognitionProgress = computed(() => recognitionRecord.value ? 100 : (starting.value ? 50 : 0))
const agentStatus = computed(() => {
  if (task.value) return task.value.status === 'success' ? 'completed' : task.value.status === 'queued' ? 'pending' : task.value.status
  return recognitionRecord.value?.agent_status || 'not_started'
})
const agentStatusText = computed(() => ({
  not_started: '未启动', pending: '等待生成', running: '正在生成', completed: '已完成', failed: '生成失败', skipped: '未启用',
}[agentStatus.value] || agentStatus.value))
const localReady = computed(() => Boolean(capabilities.value?.local_model_configured))
const cloudReady = computed(() => Boolean(capabilities.value?.qwen_configured || modelSettings.configured))
const cloudStatusText = computed(() => {
  if (cloudReady.value) return '已就绪'
  return modelSettings.configured ? '待接入视觉' : '未配置'
})
const capabilityHint = computed(() => {
  if (capabilitiesLoading.value) return '正在检查视觉模型状态'
  if (!cloudReady.value) return '智能辨识服务暂未配置。'
  if (!localReady.value) return '辅助参考暂不可用，但不影响本次智能辨识。'
  return ''
})
const canStart = computed(() =>
  Boolean(
    selectedFile.value &&
      !starting.value &&
      !capabilitiesLoading.value &&
      cloudReady.value,
  ),
)
const previewAspect = computed(() =>
  imageNaturalWidth.value && imageNaturalHeight.value
    ? `${imageNaturalWidth.value} / ${imageNaturalHeight.value}`
    : '4 / 3',
)
const boxedCandidates = computed(() => {
  if (!previewUrl.value) return []
  const localCandidates = localVisionResult.value?.top_candidates || []
  const source = localCandidates.length ? localCandidates : topCandidates.value
  const boxed: RecognitionCandidate[] = []
  for (const item of source) {
    if (!Array.isArray(item.bbox) || item.bbox.length !== 4) continue
    if (boxed.some(existing => bboxIntersectionOverUnion(existing.bbox || [], item.bbox || []) >= 0.85)) continue
    boxed.push(item)
  }
  return boxed
})

function bboxIntersectionOverUnion(left: number[], right: number[]): number {
  if (left.length !== 4 || right.length !== 4) return 0
  const intersectionWidth = Math.max(0, Math.min(left[2], right[2]) - Math.max(left[0], right[0]))
  const intersectionHeight = Math.max(0, Math.min(left[3], right[3]) - Math.max(left[1], right[1]))
  const intersection = intersectionWidth * intersectionHeight
  const leftArea = Math.max(0, left[2] - left[0]) * Math.max(0, left[3] - left[1])
  const rightArea = Math.max(0, right[2] - right[0]) * Math.max(0, right[3] - right[1])
  const union = leftArea + rightArea - intersection
  return union > 0 ? intersection / union : 0
}

function candidatePrimaryName(item: RecognitionCandidate): string {
  return item.herb_name || item.english_name || item.raw_name || item.training_class_name || '未知'
}

function candidateSecondaryName(item: RecognitionCandidate): string {
  const primary = candidatePrimaryName(item)
  const secondary = item.english_name || item.raw_name || item.training_class_name || ''
  return secondary === primary ? '' : secondary
}

function detectionBoxStyle(item: RecognitionCandidate): Record<string, string> {
  const [x1, y1, x2, y2] = item.bbox || [0, 0, 0, 0]
  const normalized = Math.max(x1, y1, x2, y2) <= 1
  const width = normalized ? 1 : imageNaturalWidth.value || Math.max(x2, 1)
  const height = normalized ? 1 : imageNaturalHeight.value || Math.max(y2, 1)
  return {
    left: `${Math.max(0, (x1 / width) * 100)}%`,
    top: `${Math.max(0, (y1 / height) * 100)}%`,
    width: `${Math.max(0, ((x2 - x1) / width) * 100)}%`,
    height: `${Math.max(0, ((y2 - y1) / height) * 100)}%`,
  }
}

function onPreviewLoad(event: Event): void {
  const image = event.target as HTMLImageElement
  imageNaturalWidth.value = image.naturalWidth
  imageNaturalHeight.value = image.naturalHeight
}

function latestNodeEvent(code: string): TaskEvent | undefined {
  return [...events.value].reverse().find((event) => event.node === code)
}

function nodeState(code: string): NodeState {
  if (recognitionRecord.value?.recognition_status === 'completed') return 'success'
  if (starting.value && code === 'recognize_image') return 'running'
  if (selectedFile.value && code === 'upload_image') return 'success'
  const latest = latestNodeEvent(code)
  if (latest?.status === 'failed') return 'failed'
  if (latest?.event === 'node_completed' || latest?.status === 'success') return 'success'
  if (task.value?.current_node === code && !terminal.value) return 'running'
  return 'pending'
}

function clearPolling(): void {
  if (pollTimer) window.clearTimeout(pollTimer)
  pollTimer = null
}

function releaseObjectUrl(): void {
  if (objectUrl.value) URL.revokeObjectURL(objectUrl.value)
  objectUrl.value = ''
}

function stopCamera(): void {
  cameraStream.value?.getTracks().forEach(track => track.stop())
  cameraStream.value = null
  if (videoElement.value) videoElement.value.srcObject = null
}

async function startCamera(): Promise<void> {
  stopCamera()
  cameraStarting.value = true
  errorText.value = ''
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 1280 },
        height: { ideal: 960 },
      },
    })
    cameraStream.value = stream
    if (videoElement.value) {
      videoElement.value.srcObject = stream
      await videoElement.value.play()
    }
  } catch (error) {
    errorText.value = getErrorMessage(error, '无法打开摄像头，请检查浏览器权限')
  } finally {
    cameraStarting.value = false
  }
}

async function captureFrame(): Promise<void> {
  const video = videoElement.value
  if (!video?.videoWidth || !video.videoHeight) {
    errorText.value = '摄像头画面尚未就绪'
    return
  }
  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const context = canvas.getContext('2d')
  if (!context) {
    errorText.value = '浏览器无法处理当前画面'
    return
  }
  context.drawImage(video, 0, 0, canvas.width, canvas.height)
  const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.92))
  if (!blob) {
    errorText.value = '画面锁帧失败'
    return
  }
  imageNaturalWidth.value = canvas.width
  imageNaturalHeight.value = canvas.height
  selectImage(new File([blob], `camera-${Date.now()}.jpg`, { type: 'image/jpeg' }))
  cameraFrozen.value = true
  stopCamera()
  message.success('画面已锁定')
}

async function resumeCamera(): Promise<void> {
  cameraFrozen.value = false
  selectedFile.value = null
  previewUrl.value = ''
  releaseObjectUrl()
  imageNaturalWidth.value = 0
  imageNaturalHeight.value = 0
  await nextTick()
  await startCamera()
}

function selectImage(file: File, fixedPreview = ''): void {
  errorText.value = ''
  const allowed = ['image/jpeg', 'image/png', 'image/webp']
  if (!allowed.includes(file.type)) {
    errorText.value = '仅支持 JPG、PNG 或 WebP 图片'
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    errorText.value = '图片大小不能超过 10 MB'
    return
  }
  releaseObjectUrl()
  selectedFile.value = file
  if (fixedPreview) {
    previewUrl.value = fixedPreview
  } else {
    objectUrl.value = URL.createObjectURL(file)
    previewUrl.value = objectUrl.value
  }
}

function onFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) selectImage(file)
  input.value = ''
}

function onDrop(event: DragEvent): void {
  dragActive.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) selectImage(file)
}

async function useSampleImage(): Promise<void> {
  try {
    const response = await fetch('/images/herbal-workbench.png')
    const blob = await response.blob()
    selectImage(new File([blob], '本草辨识示例.png', { type: 'image/png' }), '/images/herbal-workbench.png')
    message.success('已加载示例图片')
  } catch (error) {
    errorText.value = getErrorMessage(error, '示例图片加载失败')
  }
}

async function loadTask(taskId: string, continuePolling = true): Promise<void> {
  clearPolling()
  loadingTask.value = true
  try {
    const [taskData, eventData] = await Promise.all([api.getTask(taskId), api.getTaskEvents(taskId)])
    task.value = taskData
    events.value = eventData
    const taskError = taskData.error_message
      ? '学习建议暂时生成失败，不影响识别结果。'
      : ''
    agentErrorText.value = taskError

    if (!['success', 'failed'].includes(taskData.status) && continuePolling) {
      pollTimer = window.setTimeout(() => void loadTask(taskId), 700)
    } else if (taskData.status === 'success' && announcedTaskId.value !== taskId) {
      announcedTaskId.value = taskId
      message.success('学习建议已生成')
    } else if (taskData.status === 'failed' && announcedTaskId.value !== taskId) {
      announcedTaskId.value = taskId
      message.warning(taskError || '学习建议暂时生成失败，不影响识别结果。')
    }
  } catch (error) {
    if (isHttpStatus(error, 404)) {
      task.value = null
      events.value = []
      agentErrorText.value = ''
      return
    }
    agentErrorText.value = getErrorMessage(error, '学习建议状态加载失败')
  } finally {
    loadingTask.value = false
  }
}

async function startTask(): Promise<void> {
  if (!selectedFile.value) {
    errorText.value = '请先选择药材图片'
    return
  }
  if (!cloudReady.value) {
    errorText.value = capabilityHint.value || '智能辨识服务暂时不可用。'
    return
  }
  starting.value = true
  errorText.value = ''
  clearPolling()
  task.value = null
  recognitionRecord.value = null
  events.value = []
  announcedTaskId.value = ''
  try {
    const uploaded = await api.uploadFile(selectedFile.value)
    recognitionRecord.value = await api.recognizeUploadedFile({
      learner_id: auth.learnerId,
      file_id: uploaded.file_id,
      vision_mode: 'qwen',
    })
    message.success('识别完成')
    if (recognitionRecord.value.agent_task_id) {
      await loadTask(recognitionRecord.value.agent_task_id)
    }
  } catch (error) {
    errorText.value = getErrorMessage(error, '智能辨识服务暂时不可用。')
  } finally {
    starting.value = false
  }
}

async function startAgentAdvice(): Promise<void> {
  if (!recognitionRecord.value?.recognition_id) return
  agentErrorText.value = ''
  try {
    const created = await api.createRecognitionAdvice(recognitionRecord.value.recognition_id)
    recognitionRecord.value = {
      ...recognitionRecord.value,
      agent_status: created.agent_status,
      agent_task_id: created.agent_task_id,
    }
    if (created.agent_task_id) await loadTask(created.agent_task_id)
  } catch (error) {
    agentErrorText.value = getErrorMessage(error, '学习建议暂时生成失败，不影响识别结果。')
  }
}

function newTask(): void {
  clearPolling()
  task.value = null
  recognitionRecord.value = null
  events.value = []
  errorText.value = ''
  agentErrorText.value = ''
}

watch(captureMode, async mode => {
  if (mode === 'simulation') {
    stopCamera()
    await router.push('/simulation')
    return
  }
  if (mode === 'camera') {
    cameraFrozen.value = false
    imageNaturalWidth.value = 0
    imageNaturalHeight.value = 0
    await nextTick()
    await startCamera()
  } else {
    stopCamera()
  }
})

onMounted(async () => {
  await modelSettings.load('vision').catch(() => undefined)
  capabilitiesLoading.value = true
  try {
    const status = await api.getCapabilities()
    capabilities.value = status
  } catch {
    errorText.value = '视觉模型状态读取失败，请检查后端服务'
  } finally {
    capabilitiesLoading.value = false
  }
})

onBeforeUnmount(() => {
  clearPolling()
  stopCamera()
  releaseObjectUrl()
})
</script>

<template>
  <div class="page recognition-page">
    <PageHeader
      title="药材辨识"
      :meta="task ? `任务 ${task.task_id}` : `学习者 ${auth.learnerId}`"
    >
      <template #actions>
        <n-button secondary @click="useSampleImage">
          载入示例
          <template #icon><ImagePlus :size="17" /></template>
        </n-button>
        <n-button v-if="recognitionRecord" secondary @click="newTask">
          新建辨识
          <template #icon><RefreshCw :size="17" /></template>
        </n-button>
      </template>
    </PageHeader>

    <n-alert type="info" :bordered="false" class="safety-alert">
      辨识结果用于教学训练与学习反馈，不作为临床诊断或用药依据。
    </n-alert>

    <n-alert v-if="errorText" type="error" :bordered="false" closable class="task-alert" @close="errorText = ''">
      {{ errorText }}
    </n-alert>

    <section class="recognition-workspace">
      <div class="surface capture-panel">
        <div class="surface-header">
          <h2 class="surface-title">辨识样本</h2>
          <span v-if="selectedFile" class="file-size">{{ (selectedFile.size / 1024 / 1024).toFixed(2) }} MB</span>
        </div>
        <div class="surface-body capture-body">
          <div class="capture-source">
            <span>样本来源</span>
            <n-radio-group v-model:value="captureMode" name="capture-mode" :disabled="starting">
              <n-radio-button value="upload">上传图片</n-radio-button>
              <n-radio-button value="camera">摄像头</n-radio-button>
              <n-radio-button value="simulation">虚拟实训</n-radio-button>
            </n-radio-group>
          </div>

          <label
            v-if="captureMode === 'upload'"
            class="upload-zone"
            :class="{ active: dragActive, filled: previewUrl }"
            :style="{ aspectRatio: previewAspect }"
            @dragenter.prevent="dragActive = true"
            @dragover.prevent="dragActive = true"
            @dragleave.prevent="dragActive = false"
            @drop.prevent="onDrop"
          >
            <input type="file" accept="image/jpeg,image/png,image/webp" @change="onFileChange" />
            <img v-if="previewUrl" :src="previewUrl" alt="待辨识药材图片" @load="onPreviewLoad" />
            <span
              v-for="(item, index) in boxedCandidates"
              :key="`${item.herb_name}-${index}`"
              class="detection-box"
              :class="{ 'low-confidence': (item.confidence || 0) < 0.5 }"
              :style="detectionBoxStyle(item)"
            >
              <b>检测 {{ formatPercent(item.confidence) }}</b>
            </span>
            <span v-if="!previewUrl" class="upload-placeholder">
              <UploadCloud :size="34" :stroke-width="1.6" />
              <strong>选择药材图片</strong>
              <small>JPG / PNG / WebP · 不超过 10 MB</small>
            </span>
            <span v-if="previewUrl" class="replace-label">更换图片</span>
          </label>

          <div v-else class="camera-zone" :class="{ frozen: cameraFrozen }" :style="{ aspectRatio: previewAspect }">
            <img v-if="cameraFrozen && previewUrl" :src="previewUrl" alt="摄像头锁帧图片" @load="onPreviewLoad" />
            <video v-else ref="videoElement" autoplay muted playsinline />
            <n-spin v-if="cameraStarting" class="camera-loading" size="large" />
            <div class="camera-controls">
              <n-button v-if="!cameraFrozen" type="primary" :disabled="cameraStarting" @click="captureFrame">
                锁定画面
                <template #icon><Camera :size="17" /></template>
              </n-button>
              <n-button v-else secondary @click="resumeCamera">
                重新拍摄
                <template #icon><RefreshCw :size="17" /></template>
              </n-button>
            </div>
          </div>

          <div class="mode-control">
            <span>智能辨识引擎</span>
            <div class="pipeline-summary">
              <strong>本草智策智能辨识引擎</strong><b>+</b><strong>辅助参考</strong><b>+</b><strong>结构化知识核验</strong>
            </div>
            <div class="mode-status">
              <n-tag size="small" :bordered="false" :type="localReady ? 'success' : 'default'">
                辅助参考：{{ localReady ? '已就绪' : '不可用' }}
              </n-tag>
              <n-tag size="small" :bordered="false" :type="cloudReady ? 'success' : 'default'">
                多模态主识别：{{ cloudStatusText }}
              </n-tag>
              <n-tag size="small" :bordered="false" :type="capabilities?.knowledge_catalog_loaded ? 'success' : 'default'">
                45 类知识包：{{ capabilities?.knowledge_catalog_loaded ? '已加载' : '未加载' }}
              </n-tag>
            </div>
            <n-alert v-if="capabilityHint" type="warning" :bordered="false" class="capability-alert">
              {{ capabilityHint }}
            </n-alert>
          </div>

          <n-button type="primary" size="large" block :disabled="!canStart" :loading="starting" @click="startTask">
            开始智能辨识
            <template #icon><Play :size="18" /></template>
          </n-button>
        </div>
      </div>

      <div class="surface workflow-panel">
        <div class="surface-header workflow-heading">
          <div>
            <h2 class="surface-title">识别进度</h2>
            <span class="workflow-status">{{ recognitionRecord?.recognition_status || (starting ? 'recognizing' : 'uploaded') }}</span>
          </div>
          <div class="workflow-progress">
            <strong>{{ recognitionProgress }}%</strong>
            <n-progress
              type="line"
              :percentage="recognitionProgress"
              :height="7"
              :show-indicator="false"
              :status="errorText ? 'error' : 'success'"
            />
          </div>
        </div>
        <n-spin :show="starting" size="small">
          <div class="workflow-list">
            <div v-for="(node, index) in workflowNodes" :key="node.code" class="workflow-row" :class="nodeState(node.code)">
              <div class="node-state-icon">
                <CheckCircle2 v-if="nodeState(node.code) === 'success'" :size="20" />
                <LoaderCircle v-else-if="nodeState(node.code) === 'running'" class="spin-icon" :size="20" />
                <AlertCircle v-else-if="nodeState(node.code) === 'failed'" :size="20" />
                <Circle v-else :size="20" />
              </div>
              <div class="workflow-copy">
                <span>{{ String(index + 1).padStart(2, '0') }}</span>
                <strong>{{ node.label }}</strong>
                <small>{{ formatRuntimeText(latestNodeEvent(node.code)?.summary, node.code) }}</small>
              </div>
              <span class="node-elapsed">{{ formatDuration(latestNodeEvent(node.code)?.elapsed_ms) }}</span>
            </div>
          </div>
        </n-spin>
      </div>
    </section>

    <section v-if="candidate || terminal" class="result-section">
      <div class="result-heading">
        <div class="result-name">
          <span class="eyebrow">识别结果</span>
          <h2>{{ candidate ? candidatePrimaryName(candidate) : '未得到可用结果' }}</h2>
        </div>
        <div v-if="candidate && (candidate.confidence || 0) > 0" class="confidence-block">
          <n-progress
            type="circle"
            :percentage="Math.round((candidate.confidence || 0) * 100)"
            :width="86"
            :stroke-width="8"
            color="#1f6b4f"
            rail-color="#e8eeea"
          />
          <span>置信度</span>
        </div>
        <div v-if="false" class="result-tags">
          <n-tag v-if="manualReviewRequired" type="warning" :bordered="false">需人工复核</n-tag>
          <n-tag v-else-if="candidate" type="info" :bordered="false">识别已完成</n-tag>
        </div>
      </div>

      <n-alert v-if="false && agentErrorText" type="warning" :bordered="false" class="task-alert">
        {{ agentErrorText }}
      </n-alert>
      <n-alert v-if="false && knowledgeMatch?.status === 'out_of_catalog'" type="info" :bordered="false" class="task-alert">
        已完成药材辨识；该药材暂未收录于本地知识库。
      </n-alert>
      <div v-if="false" class="result-actions assistant-actions">
        <span>智能辅助：{{ agentStatusText }}</span>
        <n-button
          v-if="recognitionRecord?.agent_status !== 'skipped' && !recognitionRecord?.agent_task_id"
          secondary
          :loading="loadingTask"
          @click="startAgentAdvice"
        >
          生成学习建议
        </n-button>
        <span v-else-if="task?.result?.agent_result">学习建议已生成，可在任务记录中查看。</span>
      </div>

      <n-tabs v-if="false" type="line" animated class="result-tabs">
        <n-tab-pane name="conclusion" tab="识别结论">
          <div class="conclusion-grid">
            <div class="decision-panel">
              <span class="detail-label">识别状态</span>
              <strong>{{ recognitionRecord?.recognition_status || 'completed' }}</strong>
              <p>{{ formatRuntimeText(String(fusionResult?.decision_reason || '已完成图像辨识、名称规范化与知识核验。')) }}</p>
              <dl>
                <div>
                  <dt>主识别置信度</dt>
                  <dd>{{ formatPercent(finalIdentification?.confidence as number | undefined, 1) }}</dd>
                </div>
                <div>
                  <dt>辅助参考</dt>
                  <dd>{{ yoloReference?.candidate?.raw_name || yoloReference?.candidate?.herb_name || '不可用' }} · {{ formatPercent(yoloReference?.candidate?.confidence as number | undefined, 1) }}</dd>
                </div>
                <div>
                  <dt>知识核验</dt>
                  <dd>{{ knowledgeVerification?.status || 'not_available' }} / {{ knowledgeMatch?.status || 'not_available' }}</dd>
                </div>
                <div>
                  <dt>融合一致性</dt>
                  <dd>{{ formatRuntimeText(String(fusionResult?.agreement_status || recognitionRecord?.agreement_status || '')) }}</dd>
                </div>
                <div>
                  <dt>识别记录</dt>
                  <dd class="mono">{{ recognitionRecord?.recognition_id || '--' }}</dd>
                </div>
              </dl>
            </div>
            <div class="candidate-panel">
              <span class="detail-label">候选药材</span>
              <div v-if="topCandidates.length" class="candidate-list">
                <div v-for="(item, index) in topCandidates" :key="`${item.herb_name}-${index}`" class="candidate-row">
                  <span>{{ index + 1 }}</span>
                  <div>
                    <strong>{{ candidatePrimaryName(item) }}</strong>
                    <small>{{ candidateSecondaryName(item) || '--' }}</small>
                  </div>
                  <b>{{ formatPercent(item.confidence, 1) }}</b>
                </div>
              </div>
              <n-empty v-else size="small" description="暂无候选结果" />
            </div>
          </div>
        </n-tab-pane>

        <n-tab-pane v-if="cloudVisionResult" name="vision" :tab="`辨识依据 (${visionEvidenceCount})`">
          <div class="vision-review">
            <div class="vision-review-header">
              <div>
                <span class="detail-label">智能辨识引擎</span>
                <strong>本草智策智能辨识引擎</strong>
              </div>
              <span>{{ formatDuration(cloudVisionResult!.elapsed_ms) }}</span>
            </div>

            <section class="vision-top">
              <span class="detail-label">Top-3 候选</span>
              <div v-if="cloudCandidates.length" class="candidate-list">
                <div v-for="(item, index) in cloudCandidates.slice(0, 3)" :key="`cloud-${candidatePrimaryName(item)}-${index}`" class="candidate-row">
                  <span>{{ index + 1 }}</span>
                  <div>
                    <strong>{{ candidatePrimaryName(item) }}</strong>
                    <small>{{ candidateSecondaryName(item) || '智能辨识候选' }}</small>
                  </div>
                  <b>{{ formatPercent(item.confidence, 1) }}</b>
                </div>
              </div>
              <n-empty v-else size="small" description="未返回候选" />
            </section>

            <div class="vision-evidence-columns">
              <section class="vision-evidence-group">
                <span class="detail-label">性状依据</span>
                <div v-if="characterEvidence.length" class="vision-evidence-list">
                  <div v-for="(item, index) in characterEvidence" :key="`character-${index}`" class="vision-evidence-row">
                    <p>{{ item.text }}</p>
                    <small>{{ item.confidence == null ? '图像依据' : formatPercent(item.confidence, 1) }}</small>
                  </div>
                </div>
                <n-empty v-else size="small" description="暂无性状依据" />
              </section>
              <section class="vision-evidence-group">
                <span class="detail-label">质控依据</span>
                <div v-if="qualityEvidence.length" class="vision-evidence-list">
                  <div v-for="(item, index) in qualityEvidence" :key="`quality-${index}`" class="vision-evidence-row">
                    <p>{{ item.text }}</p>
                    <small>{{ item.confidence == null ? '图像依据' : formatPercent(item.confidence, 1) }}</small>
                  </div>
                </div>
                <n-empty v-else size="small" description="暂无质控依据" />
              </section>
            </div>

            <section v-if="cloudVisionResult!.uncertainty || traceabilityAdvice.length" class="vision-summary">
              <div v-if="cloudVisionResult!.uncertainty">
                <span class="detail-label">不确定性</span>
                <p>{{ formatRuntimeText(cloudVisionResult!.uncertainty) }}</p>
              </div>
              <div v-if="traceabilityAdvice.length">
                <span class="detail-label">复核建议</span>
                <ul>
                  <li v-for="(item, index) in traceabilityAdvice" :key="`advice-${index}`">{{ item }}</li>
                </ul>
              </div>
            </section>
          </div>
        </n-tab-pane>

      </n-tabs>

      <div v-if="false" class="result-actions">
        <span>完成时间 {{ formatDate(recognitionRecord?.created_at) }}</span>
        <n-tooltip trigger="hover">
          <template #trigger>
            <n-button secondary @click="router.push('/traces')">
              证据链
              <template #icon><ScanSearch :size="17" /></template>
            </n-button>
          </template>
          查看识别与智能辅助追踪
        </n-tooltip>
      </div>
    </section>
  </div>
</template>

<style scoped>
.recognition-page {
  display: grid;
}

.safety-alert,
.task-alert {
  margin-bottom: 14px;
}

.recognition-workspace {
  display: grid;
  grid-template-columns: minmax(320px, 0.72fr) minmax(470px, 1.28fr);
  gap: 20px;
  align-items: start;
}

.capture-panel,
.workflow-panel {
  min-height: 590px;
}

.file-size,
.workflow-status {
  color: var(--muted);
  font-size: 11px;
}

.capture-body {
  display: grid;
  gap: 18px;
}

.capture-source,
.mode-control {
  display: grid;
  gap: 9px;
}

.capture-source > span,
.mode-control > span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 650;
}

.pipeline-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  color: var(--ink);
  font-size: 12px;
}

.pipeline-summary strong {
  padding: 6px 8px;
  border-radius: 5px;
  background: var(--primary-soft);
  font-weight: 600;
}

.pipeline-summary b {
  color: var(--primary);
}

.capture-source :deep(.n-radio-group),
.mode-control :deep(.n-radio-group) {
  display: flex;
  width: 100%;
  flex-wrap: nowrap;
}

.capture-source :deep(.n-radio-button),
.mode-control :deep(.n-radio-button) {
  width: auto;
  min-width: 0;
  flex: 1 1 0;
  text-align: center;
}

.mode-status {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.capability-alert {
  font-size: 12px;
}

.upload-zone {
  position: relative;
  display: grid;
  width: 100%;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  color: var(--muted);
  background: #f7f9f7;
  border: 1px dashed var(--line-strong);
  border-radius: 7px;
  cursor: pointer;
  place-items: center;
}

.upload-zone.active {
  background: var(--primary-soft);
  border-color: var(--primary);
}

.upload-zone.filled {
  border-style: solid;
}

.upload-zone input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}

.upload-zone img {
  width: 100%;
  height: 100%;
  background: #17211c;
  object-fit: contain;
}

.detection-box {
  position: absolute;
  z-index: 2;
  min-width: 2px;
  min-height: 2px;
  border: 2px solid #53d78b;
  box-shadow: 0 0 0 1px rgba(23, 33, 28, 0.5);
  pointer-events: none;
}

.detection-box b {
  position: absolute;
  top: -24px;
  left: -2px;
  max-width: 180px;
  padding: 3px 6px;
  overflow: hidden;
  color: #fff;
  background: rgba(25, 91, 67, 0.92);
  font-size: 9px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detection-box.low-confidence {
  border-color: #e2a33a;
}

.detection-box.low-confidence b {
  background: rgba(151, 91, 10, 0.94);
}

.camera-zone {
  position: relative;
  display: grid;
  width: 100%;
  min-height: 260px;
  overflow: hidden;
  background: #17211c;
  border: 1px solid #35443b;
  border-radius: 7px;
  place-items: center;
}

.camera-zone video,
.camera-zone img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.camera-loading {
  position: absolute;
  inset: 0;
  display: grid;
  background: rgba(23, 33, 28, 0.58);
  place-items: center;
}

.camera-controls {
  position: absolute;
  right: 12px;
  bottom: 12px;
  left: 12px;
  display: flex;
  justify-content: center;
}

.upload-placeholder {
  display: grid;
  gap: 9px;
  justify-items: center;
  padding: 24px;
  text-align: center;
}

.upload-placeholder svg {
  color: var(--primary);
}

.upload-placeholder strong {
  color: var(--ink);
  font-size: 14px;
}

.upload-placeholder small {
  color: var(--subtle);
  font-size: 11px;
}

.replace-label {
  position: absolute;
  right: 10px;
  bottom: 10px;
  padding: 5px 8px;
  color: #fff;
  background: rgba(23, 33, 28, 0.78);
  border-radius: 4px;
  font-size: 11px;
}

.workflow-heading > div:first-child {
  min-width: 130px;
}

.workflow-progress {
  display: grid;
  grid-template-columns: 45px minmax(130px, 220px);
  align-items: center;
  gap: 10px;
}

.workflow-progress strong {
  color: var(--primary);
  font-size: 13px;
  text-align: right;
}

.workflow-list {
  display: grid;
}

.workflow-row {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr) 74px;
  align-items: center;
  gap: 12px;
  min-height: 58px;
  padding: 8px 18px;
  border-bottom: 1px solid var(--line);
}

.workflow-row:last-child {
  border-bottom: 0;
}

.node-state-icon {
  display: grid;
  color: #b0bab3;
  place-items: center;
}

.workflow-copy {
  display: grid;
  grid-template-columns: 32px minmax(92px, 0.55fr) minmax(120px, 1fr);
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.workflow-copy > span {
  color: var(--subtle);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 10px;
}

.workflow-copy strong {
  color: #4a5750;
  font-size: 13px;
  font-weight: 620;
}

.workflow-copy small {
  overflow: hidden;
  color: var(--subtle);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-elapsed {
  color: var(--subtle);
  font-size: 10px;
  text-align: right;
}

.workflow-row.success .node-state-icon,
.workflow-row.success .workflow-copy strong {
  color: var(--primary);
}

.workflow-row.running {
  background: var(--amber-soft);
}

.workflow-row.running .node-state-icon,
.workflow-row.running .workflow-copy strong {
  color: var(--amber);
}

.workflow-row.failed .node-state-icon,
.workflow-row.failed .workflow-copy strong {
  color: var(--danger);
}

.spin-icon {
  animation: spin 900ms linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.result-section {
  margin-top: 26px;
  padding-top: 25px;
  border-top: 1px solid var(--line-strong);
}

.result-heading {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 100px auto;
  align-items: center;
  gap: 22px;
  min-height: 140px;
  padding: 22px 24px;
  background: #eff6f2;
  border-left: 4px solid var(--primary);
}

.result-name h2 {
  margin: 4px 0 2px;
  color: var(--ink);
  font-size: 30px;
  line-height: 1.2;
  font-weight: 740;
}

.result-name > span:last-child {
  color: var(--muted);
  font-size: 13px;
}

.confidence-block {
  display: grid;
  justify-items: center;
  gap: 4px;
  color: var(--muted);
  font-size: 11px;
}

.result-tags {
  display: flex;
  align-items: flex-end;
  flex-direction: column;
  gap: 8px;
}

.result-tabs {
  margin-top: 18px;
}

.result-tabs :deep(.n-tabs-pane-wrapper) {
  padding-top: 8px;
}

.conclusion-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.8fr);
  gap: 18px;
}

.decision-panel,
.candidate-panel,
.resource-result {
  padding: 20px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.detail-label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 650;
}

.decision-panel > strong {
  display: block;
  margin: 6px 0 8px;
  color: var(--primary-strong);
  font-size: 19px;
}

.decision-panel > p {
  color: #4e5c54;
  font-size: 13px;
  line-height: 1.7;
}

.decision-panel dl {
  display: grid;
  gap: 9px;
  margin: 18px 0 0;
  padding-top: 15px;
  border-top: 1px solid var(--line);
}

.decision-panel dl > div {
  display: grid;
  grid-template-columns: 130px minmax(0, 1fr);
  gap: 12px;
}

.decision-panel dt,
.decision-panel dd {
  margin: 0;
  font-size: 12px;
}

.decision-panel dt {
  color: var(--muted);
}

.decision-panel dd {
  color: var(--ink);
  overflow-wrap: anywhere;
}

.candidate-list {
  display: grid;
  gap: 2px;
  margin-top: 9px;
}

.candidate-row {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) 64px;
  align-items: center;
  gap: 10px;
  min-height: 54px;
  border-bottom: 1px solid var(--line);
}

.candidate-row:last-child {
  border-bottom: 0;
}

.candidate-row > span {
  color: var(--subtle);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 10px;
}

.candidate-row > div {
  display: grid;
}

.candidate-row strong {
  color: var(--ink);
  font-size: 13px;
}

.candidate-row small {
  color: var(--subtle);
  font-size: 10px;
}

.candidate-row b {
  color: var(--primary);
  font-size: 12px;
  text-align: right;
}

.vision-review {
  display: grid;
  gap: 20px;
  padding: 4px;
}

.vision-review-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line);
}

.vision-review-header > div {
  display: grid;
  gap: 5px;
}

.vision-review-header strong {
  color: var(--ink);
  font-size: 15px;
}

.vision-review-header > span {
  color: var(--subtle);
  font-size: 11px;
}

.vision-top {
  min-width: 0;
}

.vision-evidence-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

.vision-evidence-group {
  min-width: 0;
}

.vision-evidence-list {
  margin-top: 9px;
  border-top: 1px solid var(--line);
}

.vision-evidence-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--line);
}

.vision-evidence-row p,
.vision-summary p,
.vision-summary ul {
  margin: 0;
  color: #4c5a52;
  font-size: 12px;
  line-height: 1.65;
}

.vision-evidence-row small {
  color: var(--subtle);
  font-size: 10px;
  white-space: nowrap;
}

.vision-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
  padding: 16px;
  background: #f7f9f7;
  border-left: 3px solid var(--amber);
}

.vision-summary > div {
  display: grid;
  gap: 7px;
  min-width: 0;
}

.vision-summary ul {
  padding-left: 18px;
}

.evidence-list {
  border-top: 1px solid var(--line);
}

.evidence-item {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 16px;
  padding: 20px 4px;
  border-bottom: 1px solid var(--line);
}

.evidence-index {
  color: var(--blue);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 12px;
}

.evidence-content {
  min-width: 0;
}

.evidence-title-row,
.resource-result-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.evidence-title-row h3,
.resource-result-header h3 {
  color: var(--ink);
  font-size: 15px;
  line-height: 1.4;
  font-weight: 650;
}

.evidence-content > p {
  margin-top: 8px;
  color: #4c5a52;
  font-size: 13px;
  line-height: 1.75;
}

.evidence-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 7px 16px;
  margin-top: 11px;
  color: var(--subtle);
  font-size: 10px;
}

.resource-result-header > div:last-child {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.resource-content {
  max-height: 420px;
  margin-top: 18px;
  padding: 18px 0;
  overflow-y: auto;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}

.review-strip {
  display: grid;
  grid-template-columns: 24px auto auto 1fr;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  color: var(--muted);
  font-size: 12px;
}

.review-strip svg,
.review-strip strong {
  color: var(--primary);
}

.review-strip small {
  color: var(--subtle);
  text-align: right;
}

.result-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.result-actions > span {
  margin-right: auto;
  color: var(--subtle);
  font-size: 11px;
}

@media (max-width: 1080px) {
  .recognition-workspace {
    grid-template-columns: 1fr;
  }

  .capture-panel,
  .workflow-panel {
    min-height: auto;
  }

}

@media (max-width: 760px) {
  .workflow-heading {
    align-items: stretch;
  }

  .workflow-progress {
    width: 100%;
    grid-template-columns: 42px minmax(0, 1fr);
  }

  .workflow-copy {
    grid-template-columns: 26px minmax(90px, 1fr);
  }

  .workflow-copy small {
    display: none;
  }

  .result-heading {
    grid-template-columns: minmax(0, 1fr) 90px;
  }

  .result-tags {
    grid-column: 1 / -1;
    align-items: flex-start;
    flex-direction: row;
    flex-wrap: wrap;
  }

  .conclusion-grid {
    grid-template-columns: 1fr;
  }

  .vision-evidence-columns,
  .vision-summary {
    grid-template-columns: 1fr;
  }

  .result-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .result-actions > span {
    margin-right: 0;
  }
}

@media (max-width: 480px) {
  .mode-control :deep(.n-radio-group) {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    height: auto;
    row-gap: 4px;
  }

  .capture-source :deep(.n-radio-group) {
    display: grid;
    grid-template-columns: 1fr;
    height: auto;
    row-gap: 4px;
  }

  .capture-source :deep(.n-radio-group__splitor) {
    display: none;
  }

  .mode-control :deep(.n-radio-group__splitor) {
    display: none;
  }

  .workflow-row {
    grid-template-columns: 22px minmax(0, 1fr);
    padding-inline: 12px;
  }

  .node-elapsed {
    display: none;
  }

  .result-heading {
    grid-template-columns: 1fr;
  }

  .confidence-block {
    justify-items: start;
  }

  .evidence-item {
    grid-template-columns: 28px minmax(0, 1fr);
  }
}
</style>
