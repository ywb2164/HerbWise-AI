<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  NAlert,
  NButton,
  NEmpty,
  NProgress,
  NRadioButton,
  NRadioGroup,
  NSpin,
  NTabPane,
  NTabs,
  NTag,
  NTooltip,
  useMessage,
} from 'naive-ui'
import {
  AlertCircle,
  BookOpenCheck,
  Camera,
  CheckCircle2,
  Circle,
  FileChartColumn,
  ImagePlus,
  LoaderCircle,
  Play,
  RefreshCw,
  ScanSearch,
  UploadCloud,
} from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import SourceBadge from '../components/SourceBadge.vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
import { useModelSettingsStore } from '../stores/model-settings'
import type {
  AgentTask,
  CapabilityStatus,
  KnowledgeEvidence,
  ProviderFailure,
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
  formatProvider,
  formatResourceStatus,
  formatRuntimeText,
  getErrorMessage,
  isHttpStatus,
  taskTypeLabels,
} from '../utils/format'

type VisionMode = 'qwen' | 'local' | 'hybrid'
type NodeState = 'pending' | 'running' | 'success' | 'failed'
type CaptureMode = 'upload' | 'camera' | 'simulation'

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
const visionMode = ref<VisionMode>('local')
const capabilities = ref<CapabilityStatus | null>(null)
const capabilitiesLoading = ref(true)
const starting = ref(false)
const loadingTask = ref(false)
const dragActive = ref(false)
const errorText = ref('')
const task = ref<AgentTask | null>(null)
const recognitionRecord = ref<RecognitionRecord | null>(null)
const events = ref<TaskEvent[]>([])
const announcedTaskId = ref('')
let pollTimer: ReturnType<typeof setTimeout> | null = null

const workflowNodes = [
  { code: 'load_profile', label: '学情画像', progress: 10 },
  { code: 'recognize_image', label: '图像识别', progress: 20 },
  { code: 'vision_review', label: '视觉复核', progress: 30 },
  { code: 'retrieve_knowledge', label: '知识检索', progress: 45 },
  { code: 'judge_result', label: '纠错裁判', progress: 55 },
  { code: 'generate_resources', label: '资源生成', progress: 70 },
  { code: 'review_resources', label: '审核纠偏', progress: 80 },
  { code: 'update_learning_path', label: '路径更新', progress: 90 },
  { code: 'save_trace', label: '证据归档', progress: 100 },
]

const fusionResult = computed(
  () => task.value?.result?.fusion_result || recognitionRecord.value?.fusion_result || null,
)
const candidate = computed<RecognitionCandidate | null>(() => {
  const result = task.value?.result?.recognition_result?.candidate || fusionResult.value?.final_candidate
  if (result) return result
  if (!recognitionRecord.value?.final_name) return null
  return {
    medicine_id: recognitionRecord.value.final_medicine_id,
    herb_name: recognitionRecord.value.final_name,
    confidence: recognitionRecord.value.confidence || 0,
  }
})
const localVisionResult = computed<VisionRecognitionResult | null>(() => {
  const result = fusionResult.value?.local_result || recognitionRecord.value?.local_result
  if (result) return result
  const direct = task.value?.result?.recognition_result
  return direct?.provider === 'local' ? direct : null
})
const cloudVisionResult = computed<VisionRecognitionResult | null>(() => {
  const result = fusionResult.value?.qwen_result || recognitionRecord.value?.qwen_result
  if (result) return result
  const direct = task.value?.result?.recognition_result
  return direct?.provider === 'qwen' ? direct : null
})
const topCandidates = computed(() => {
  const local = localVisionResult.value?.top_candidates || []
  if (local.length) return local
  const cloud = cloudVisionResult.value?.top_candidates || []
  if (cloud.length) return cloud
  return task.value?.result?.recognition_result?.top_candidates || []
})
const cloudCandidates = computed(() => cloudVisionResult.value?.top_candidates || [])
const characterEvidence = computed<RecognitionEvidence[]>(() => cloudVisionResult.value?.character_evidence || [])
const qualityEvidence = computed<RecognitionEvidence[]>(() => cloudVisionResult.value?.quality_control_evidence || [])
const traceabilityAdvice = computed(() => cloudVisionResult.value?.traceability_advice || [])
const visionEvidenceCount = computed(() => characterEvidence.value.length + qualityEvidence.value.length)
const evidences = computed<KnowledgeEvidence[]>(() => task.value?.result?.knowledge_evidence || [])
const generatedResource = computed(() => task.value?.result?.generated_resources?.[0] || null)
const reviewResult = computed(() => task.value?.result?.review_result || null)
const manualReviewRequired = computed(
  () =>
    Boolean(fusionResult.value?.manual_review_required) ||
    Boolean(task.value?.result?.judge_result?.manual_review_required) ||
    Boolean(recognitionRecord.value?.manual_review_required) ||
    Boolean(candidate.value && (candidate.value.confidence || 0) < 0.5),
)
const terminal = computed(() => Boolean(task.value && ['success', 'failed'].includes(task.value.status)))
const localReady = computed(() => Boolean(capabilities.value?.local_model_configured))
const cloudReady = computed(() => Boolean(capabilities.value?.qwen_configured || modelSettings.configured))
const hybridReady = computed(() => localReady.value && cloudReady.value)
const cloudStatusText = computed(() => {
  if (cloudReady.value) return '已就绪'
  return modelSettings.configured ? '待接入视觉' : '未配置'
})
const visionModeAvailable = computed(() => isModeAvailable(visionMode.value))
const capabilityHint = computed(() => {
  if (capabilitiesLoading.value) return '正在检查视觉模型状态'
  if (visionMode.value === 'local' && !localReady.value) return '本地 YOLO 权重或 Ultralytics 运行环境尚未就绪'
  if (visionMode.value === 'qwen' && !cloudReady.value) return '云端多模态视觉模型尚未配置'
  if (visionMode.value === 'hybrid' && !hybridReady.value) return '双路复核需要本地 YOLO 与云端视觉模型同时可用'
  return ''
})
const canStart = computed(() =>
  Boolean(
    selectedFile.value &&
      !starting.value &&
      task.value?.status !== 'running' &&
      !capabilitiesLoading.value &&
      visionModeAvailable.value,
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

function isModeAvailable(mode: VisionMode, status = capabilities.value): boolean {
  if (!status) return false
  const cloudConfigured = status.qwen_configured || modelSettings.configured
  if (mode === 'local') return status.local_model_configured
  if (mode === 'qwen') return cloudConfigured
  return status.local_model_configured && cloudConfigured
}

function preferredVisionMode(status: CapabilityStatus): VisionMode {
  if (['qwen', 'local', 'hybrid'].includes(status.vision_mode)) {
    const configuredMode = status.vision_mode as VisionMode
    if (isModeAvailable(configuredMode, status)) return configuredMode
  }
  if (status.local_model_configured) return 'local'
  if (status.qwen_configured) return 'qwen'
  return 'local'
}

function candidatePrimaryName(item: RecognitionCandidate): string {
  return item.herb_name || item.english_name || item.raw_name || item.training_class_name || '未知'
}

function candidateSecondaryName(item: RecognitionCandidate): string {
  const primary = candidatePrimaryName(item)
  const secondary = item.english_name || item.raw_name || item.training_class_name || ''
  return secondary === primary ? '' : secondary
}

function providerFailureLabel(failure: ProviderFailure): string {
  const provider = failure.provider === 'local' ? '本地 YOLO' : failure.provider === 'qwen' ? '云端视觉' : failure.provider
  const reasons: Record<string, string> = {
    authentication_error: '鉴权失败',
    configuration_error: '未配置',
    invalid_response: '返回格式无效',
    local_model_unavailable: '模型不可用',
    network_error: '网络连接失败',
    provider_unavailable: '服务不可用',
    rate_limit_error: '调用频率受限',
    schema_validation_error: '结果结构校验失败',
    timeout_error: '调用超时',
    unsupported_file: '图片格式不支持',
  }
  return `${provider}：${reasons[failure.error_code] || failure.error_code}`
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
    if (taskData.progress >= 20 || ['success', 'failed'].includes(taskData.status)) {
      try {
        const records = await api.getRecognitionRecordsByTask(taskId)
        recognitionRecord.value = records.items[0] || recognitionRecord.value
      } catch {
        // The recognition record can lag briefly behind the task progress event.
      }
    }
    const failures = taskData.result?.provider_failures || []
    const noDetection = taskData.error_message === 'No usable recognition result'
    const taskError = taskData.error_message && !noDetection
      ? formatRuntimeText(taskData.error_message, taskData.error_message)
      : ''
    errorText.value = taskError || failures.map(providerFailureLabel).join('；')

    if (!['success', 'failed'].includes(taskData.status) && continuePolling) {
      pollTimer = window.setTimeout(() => void loadTask(taskId), 700)
    } else if (taskData.status === 'success' && announcedTaskId.value !== taskId) {
      announcedTaskId.value = taskId
      message.success('智能体任务已完成')
    } else if (taskData.status === 'failed' && announcedTaskId.value !== taskId) {
      announcedTaskId.value = taskId
      if (!noDetection) message.error(taskError || '智能体任务失败')
    }
  } catch (error) {
    if (isHttpStatus(error, 404)) {
      if (localStorage.getItem('herbwise.last_task_id') === taskId) {
        localStorage.removeItem('herbwise.last_task_id')
      }
      task.value = null
      recognitionRecord.value = null
      events.value = []
      errorText.value = ''
      return
    }
    errorText.value = getErrorMessage(error, '任务状态加载失败')
  } finally {
    loadingTask.value = false
  }
}

async function startTask(): Promise<void> {
  if (!selectedFile.value) {
    errorText.value = '请先选择药材图片'
    return
  }
  if (!visionModeAvailable.value) {
    errorText.value = capabilityHint.value || '当前视觉模型不可用'
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
    const created = await api.createTask({
      learner_id: auth.learnerId,
      task_type: 'full_loop',
      file_id: uploaded.file_id,
      vision_mode: visionMode.value,
      llm_mode: modelSettings.configured ? 'real' : 'mock',
    })
    localStorage.setItem('herbwise.last_task_id', created.task_id)
    task.value = {
      task_id: created.task_id,
      learner_id: auth.learnerId,
      task_type: 'full_loop',
      status: created.status,
      current_node: null,
      progress: 0,
      result: null,
      error_message: null,
      created_at: null,
      started_at: null,
      finished_at: null,
    }
    message.success('图片上传成功，智能体已启动')
    await loadTask(created.task_id)
  } catch (error) {
    errorText.value = getErrorMessage(error, '任务启动失败')
  } finally {
    starting.value = false
  }
}

function newTask(): void {
  clearPolling()
  task.value = null
  recognitionRecord.value = null
  events.value = []
  errorText.value = ''
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
  await modelSettings.load().catch(() => undefined)
  capabilitiesLoading.value = true
  try {
    const status = await api.getCapabilities()
    capabilities.value = status
    visionMode.value = preferredVisionMode(status)
  } catch {
    errorText.value = '视觉模型状态读取失败，请检查后端服务'
  } finally {
    capabilitiesLoading.value = false
  }
  const lastTaskId = localStorage.getItem('herbwise.last_task_id')
  if (lastTaskId) await loadTask(lastTaskId)
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
        <n-button v-if="task" secondary @click="newTask">
          新建任务
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
            <n-radio-group v-model:value="captureMode" name="capture-mode" :disabled="task?.status === 'running'">
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
              <b>{{ candidatePrimaryName(item) }} {{ formatPercent(item.confidence) }}</b>
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
            <span>视觉模型</span>
            <n-radio-group v-model:value="visionMode" name="vision-mode" :disabled="task?.status === 'running'">
              <n-radio-button value="local" :disabled="!localReady">本地 YOLO</n-radio-button>
              <n-radio-button value="qwen" :disabled="!cloudReady">云端多模态</n-radio-button>
              <n-radio-button value="hybrid" :disabled="!hybridReady">双路复核</n-radio-button>
            </n-radio-group>
            <div class="mode-status">
              <n-tag size="small" :bordered="false" :type="localReady ? 'success' : 'default'">
                YOLO {{ localReady ? '已就绪' : '未就绪' }}
              </n-tag>
              <n-tag size="small" :bordered="false" :type="cloudReady ? 'success' : 'default'">
                云端视觉 {{ cloudStatusText }}
              </n-tag>
            </div>
            <n-alert v-if="capabilityHint" type="warning" :bordered="false" class="capability-alert">
              {{ capabilityHint }}
            </n-alert>
          </div>

          <n-button type="primary" size="large" block :disabled="!canStart" :loading="starting" @click="startTask">
            启动智能体任务
            <template #icon><Play :size="18" /></template>
          </n-button>
        </div>
      </div>

      <div class="surface workflow-panel">
        <div class="surface-header workflow-heading">
          <div>
            <h2 class="surface-title">智能体任务流</h2>
            <span class="workflow-status">{{ formatResourceStatus(task?.status || 'pending') }}</span>
          </div>
          <div class="workflow-progress">
            <strong>{{ task?.progress || 0 }}%</strong>
            <n-progress
              type="line"
              :percentage="task?.progress || 0"
              :height="7"
              :show-indicator="false"
              :status="task?.status === 'failed' ? 'error' : 'success'"
            />
          </div>
        </div>
        <n-spin :show="loadingTask && !task" size="small">
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
          <span class="eyebrow">辨识结论</span>
          <h2>{{ candidate ? candidatePrimaryName(candidate) : '未得到可用结果' }}</h2>
          <span>{{ candidate?.english_name || task?.error_message || '' }}</span>
        </div>
        <div v-if="candidate" class="confidence-block">
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
        <div class="result-tags">
          <SourceBadge :source="task?.result?.judge_result?.data_source || task?.result?.recognition_result?.provider || recognitionRecord?.data_source || visionMode" />
          <n-tag v-if="manualReviewRequired" type="warning" :bordered="false">需人工复核</n-tag>
          <n-tag v-else-if="task?.status === 'success'" type="success" :bordered="false">流程通过</n-tag>
          <n-tag v-else-if="candidate" type="info" :bordered="false">识别已完成</n-tag>
        </div>
      </div>

      <n-tabs type="line" animated class="result-tabs">
        <n-tab-pane name="conclusion" tab="识别结论">
          <div class="conclusion-grid">
            <div class="decision-panel">
              <span class="detail-label">裁判结果</span>
              <strong>{{ formatResourceStatus(task?.result?.judge_result?.status || 'pass') }}</strong>
              <p>{{ formatRuntimeText(String(task?.result?.judge_result?.reason || fusionResult?.decision_reason || '智能体流程已完成结果复核。')) }}</p>
              <dl>
                <div>
                  <dt>融合一致性</dt>
                  <dd>{{ formatRuntimeText(String(fusionResult?.agreement_status || recognitionRecord?.agreement_status || '')) }}</dd>
                </div>
                <div>
                  <dt>调整后置信度</dt>
                  <dd>{{ formatPercent(fusionResult?.confidence_after_adjustment as number | undefined, 1) }}</dd>
                </div>
                <div>
                  <dt>识别记录</dt>
                  <dd class="mono">{{ task?.result?.recognition_id || recognitionRecord?.recognition_id || '--' }}</dd>
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

        <n-tab-pane v-if="cloudVisionResult" name="vision" :tab="`云端视觉 (${visionEvidenceCount})`">
          <div class="vision-review">
            <div class="vision-review-header">
              <div>
                <span class="detail-label">云端模型</span>
                <strong>{{ cloudVisionResult.model_name || formatProvider(cloudVisionResult.provider) }}</strong>
              </div>
              <span>{{ formatDuration(cloudVisionResult.elapsed_ms) }}</span>
            </div>

            <section class="vision-top">
              <span class="detail-label">Top-3 候选</span>
              <div v-if="cloudCandidates.length" class="candidate-list">
                <div v-for="(item, index) in cloudCandidates.slice(0, 3)" :key="`cloud-${candidatePrimaryName(item)}-${index}`" class="candidate-row">
                  <span>{{ index + 1 }}</span>
                  <div>
                    <strong>{{ candidatePrimaryName(item) }}</strong>
                    <small>{{ candidateSecondaryName(item) || formatProvider(cloudVisionResult.provider) }}</small>
                  </div>
                  <b>{{ formatPercent(item.confidence, 1) }}</b>
                </div>
              </div>
              <n-empty v-else size="small" description="云端模型未返回候选" />
            </section>

            <div class="vision-evidence-columns">
              <section class="vision-evidence-group">
                <span class="detail-label">性状依据</span>
                <div v-if="characterEvidence.length" class="vision-evidence-list">
                  <div v-for="(item, index) in characterEvidence" :key="`character-${index}`" class="vision-evidence-row">
                    <p>{{ item.text }}</p>
                    <small>{{ item.confidence == null ? formatProvider(item.source) : formatPercent(item.confidence, 1) }}</small>
                  </div>
                </div>
                <n-empty v-else size="small" description="暂无性状依据" />
              </section>
              <section class="vision-evidence-group">
                <span class="detail-label">质控依据</span>
                <div v-if="qualityEvidence.length" class="vision-evidence-list">
                  <div v-for="(item, index) in qualityEvidence" :key="`quality-${index}`" class="vision-evidence-row">
                    <p>{{ item.text }}</p>
                    <small>{{ item.confidence == null ? formatProvider(item.source) : formatPercent(item.confidence, 1) }}</small>
                  </div>
                </div>
                <n-empty v-else size="small" description="暂无质控依据" />
              </section>
            </div>

            <section v-if="cloudVisionResult.uncertainty || traceabilityAdvice.length" class="vision-summary">
              <div v-if="cloudVisionResult.uncertainty">
                <span class="detail-label">不确定性</span>
                <p>{{ formatRuntimeText(cloudVisionResult.uncertainty) }}</p>
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

        <n-tab-pane name="evidence" :tab="`知识证据 (${evidences.length})`">
          <div v-if="evidences.length" class="evidence-list">
            <article v-for="(item, index) in evidences" :key="item.evidence_id || index" class="evidence-item">
              <div class="evidence-index">{{ String(index + 1).padStart(2, '0') }}</div>
              <div class="evidence-content">
                <div class="evidence-title-row">
                  <h3>{{ item.document_name || item.citation || '知识证据' }}</h3>
                  <SourceBadge :source="item.data_source || item.source || 'mock'" />
                </div>
                <p>{{ item.content || '暂无证据摘要' }}</p>
                <div class="evidence-meta">
                  <span>页码 {{ item.page_number ?? '未标注' }}</span>
                  <span>Chunk {{ item.chunk_id || '未标注' }}</span>
                  <span>相关度 {{ formatPercent(item.score, 1) }}</span>
                  <span v-if="item.citation">{{ item.citation }}</span>
                </div>
              </div>
            </article>
          </div>
          <div v-else class="empty-state"><n-empty description="暂无知识证据" /></div>
        </n-tab-pane>

        <n-tab-pane name="resource" tab="生成资源">
          <div v-if="generatedResource" class="resource-result">
            <div class="resource-result-header">
              <div>
                <span class="detail-label">{{ taskTypeLabels[generatedResource.resource_type] || generatedResource.resource_type }}</span>
                <h3>{{ generatedResource.title }}</h3>
              </div>
              <div>
                <SourceBadge :source="generatedResource.provider" />
                <n-tag size="small" :bordered="false">{{ formatResourceStatus(generatedResource.status) }}</n-tag>
              </div>
            </div>
            <div class="content-prewrap resource-content">{{ generatedResource.content_markdown }}</div>
            <div v-if="reviewResult" class="review-strip">
              <BookOpenCheck :size="19" />
              <span>资源审核</span>
              <strong>{{ formatResourceStatus(reviewResult.status) }}</strong>
              <small>{{ formatProvider(reviewResult.provider) }}</small>
            </div>
          </div>
          <div v-else class="empty-state"><n-empty description="暂无生成资源" /></div>
        </n-tab-pane>
      </n-tabs>

      <div class="result-actions">
        <span>完成时间 {{ formatDate(task?.finished_at) }}</span>
        <n-tooltip trigger="hover">
          <template #trigger>
            <n-button secondary @click="router.push('/traces')">
              证据链
              <template #icon><ScanSearch :size="17" /></template>
            </n-button>
          </template>
          查看任务追踪与模型日志
        </n-tooltip>
        <n-button type="primary" @click="router.push('/reports')">
          生成报告
          <template #icon><FileChartColumn :size="17" /></template>
        </n-button>
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
