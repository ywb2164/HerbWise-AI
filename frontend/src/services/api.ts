import type { AxiosRequestConfig } from 'axios'
import type {
  AgentLog,
  AgentTask,
  AdminRecord,
  AdminUser,
  ApiEnvelope,
  CapabilityStatus,
  DiagnosisResult,
  InitialQuestion,
  InitialTestResult,
  InitialTestStatus,
  JsonRecord,
  LearnerDimension,
  LearnerProfile,
  LearningAnswer,
  LearningAnswerPayload,
  LearningPath,
  LearningPlan,
  LearningTask,
  LearningTaskAttempt,
  LearningTaskDetail,
  LearningTaskResult,
  MedicineFeature,
  MedicineItem,
  ModelConnectionResult,
  ModelPurpose,
  ModelSettingsPayload,
  ModelSettingsStatus,
  MetricsOverview,
  Paginated,
  ProfileHistoryItem,
  ProfilePayload,
  ProfileUpdatePayload,
  QualityMetric,
  RecognitionRecord,
  ReportRecord,
  ResourceItem,
  ResourceGenerationJob,
  RetrievalResult,
  ReviewResult,
  SimilarMedicine,
  TaskCreated,
  TaskEvent,
  TokenPair,
  TraceRecord,
  UploadedFile,
  UserSummary,
  WeakPoint,
} from '../types/api'
import http from './http'

class ApiError extends Error {
  readonly code: number
  readonly errorCode?: string | null

  constructor(code: number, message: string, errorCode?: string | null) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.errorCode = errorCode
  }
}

function unwrap<T>(payload: ApiEnvelope<T> | T): T {
  if (payload && typeof payload === 'object' && 'code' in payload && 'data' in payload) {
    const envelope = payload as ApiEnvelope<T>
    if (envelope.code !== 0) throw new ApiError(envelope.code, envelope.message, envelope.error_code)
    return envelope.data
  }
  return payload as T
}

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await http.request<ApiEnvelope<T> | T>(config)
  return unwrap(response.data)
}

export const api = {
  login: (username: string, password: string) =>
    request<TokenPair>({ method: 'POST', url: '/auth/login', data: { username, password } }),
  me: () => request<UserSummary>({ url: '/auth/me' }),
  logout: (refreshToken: string) =>
    request<{ logged_out: boolean }>({
      method: 'POST',
      url: '/auth/logout',
      data: { refresh_token: refreshToken },
    }),

  getModelSettings: (purpose: ModelPurpose) =>
    request<ModelSettingsStatus>({ url: `/model-settings/${purpose}` }),
  saveModelSettings: (purpose: ModelPurpose, payload: ModelSettingsPayload) =>
    request<ModelSettingsStatus>({ method: 'PUT', url: `/model-settings/${purpose}`, data: payload }),
  testTextModelSettings: (payload: ModelSettingsPayload) =>
    request<ModelConnectionResult>({ method: 'POST', url: '/model-settings/text/test', data: payload }),
  testVisionModelSettings: (payload: ModelSettingsPayload, file: File) => {
    const form = new FormData()
    form.append('protocol', payload.protocol)
    form.append('base_url', payload.base_url)
    form.append('model_id', payload.model_id)
    if (payload.api_key) form.append('api_key', payload.api_key)
    form.append('file', file)
    return request<ModelConnectionResult>({ method: 'POST', url: '/model-settings/vision/test', data: form })
  },
  clearModelSettings: (purpose: ModelPurpose) =>
    request<{ cleared: boolean }>({ method: 'DELETE', url: `/model-settings/${purpose}` }),

  getProfile: (learnerId: string) => request<LearnerProfile>({ url: `/profiles/${learnerId}` }),
  createProfile: (payload: ProfilePayload) =>
    request<LearnerProfile>({ method: 'POST', url: '/profiles', data: payload }),
  updateProfile: (learnerId: string, payload: ProfileUpdatePayload) =>
    request<LearnerProfile>({ method: 'PUT', url: `/profiles/${learnerId}`, data: payload }),
  diagnoseProfile: (learnerId: string) =>
    request<DiagnosisResult>({ method: 'POST', url: `/profiles/${learnerId}/diagnose` }),
  getProfileHistory: (learnerId: string) =>
    request<ProfileHistoryItem[]>({ url: `/profiles/${learnerId}/history` }),
  getInitialQuestions: () => request<InitialQuestion[]>({ url: '/tests/initial/questions' }),
  getInitialTestStatus: (learnerId: string) => request<InitialTestStatus>({ url: '/tests/initial/status', params: { learner_id: learnerId } }),
  submitInitialTest: (learnerId: string, answers: Array<{ question_id: number; answer: string }>) =>
    request<InitialTestResult>({
      method: 'POST',
      url: '/tests/initial/submit',
      data: { learner_id: learnerId, answers },
    }),
  getDimensions: (learnerId: string) =>
    request<LearnerDimension[]>({ url: `/profiles/${learnerId}/dimensions` }),
  getWeakPoints: (learnerId: string) =>
    request<WeakPoint[]>({ url: `/profiles/${learnerId}/weak-points` }),
  getLearningPath: (learnerId: string) =>
    request<LearningPath>({ url: `/learning-paths/${learnerId}` }),
  updateLearningPath: (learnerId: string) =>
    request<LearningPath>({ method: 'POST', url: '/learning-paths/update', params: { learner_id: learnerId } }),
  submitLearningAnswer: (payload: LearningAnswerPayload) =>
    request<LearningAnswer>({ method: 'POST', url: '/learning/answers', data: payload }),
  listLearningAnswers: (learnerId: string, pageSize = 50) =>
    request<Paginated<LearningAnswer>>({
      url: `/learning/answers/${learnerId}`,
      params: { page: 1, page_size: pageSize },
    }),
  listLearningTasks: (learnerId: string, status?: string) =>
    request<Paginated<LearningTask>>({ url: '/learning-tasks', params: { learner_id: learnerId, status, page: 1, page_size: 50 } }),
  getLearningTask: (taskId: string, learnerId: string) =>
    request<LearningTaskDetail>({ url: `/learning-tasks/${taskId}`, params: { learner_id: learnerId } }),
  startLearningTask: (taskId: string, learnerId: string) =>
    request<LearningTaskAttempt>({ method: 'POST', url: `/learning-tasks/${taskId}/start`, params: { learner_id: learnerId } }),
  submitLearningTask: (taskId: string, learnerId: string, attemptId: string, answers: Array<{ question_id: number; answer: string | string[] }>) =>
    request<LearningTaskResult>({ method: 'POST', url: `/learning-tasks/${taskId}/submit`, params: { learner_id: learnerId }, data: { attempt_id: attemptId, answers } }),
  getLearningTaskResult: (taskId: string, learnerId: string) =>
    request<LearningTaskResult>({ url: `/learning-tasks/${taskId}/result`, params: { learner_id: learnerId } }),
  getLearningAttemptResult: (attemptId: string, learnerId: string) =>
    request<LearningTaskResult>({ url: `/learning-tasks/attempts/${attemptId}/result`, params: { learner_id: learnerId } }),
  getCurrentLearningPlan: (learnerId: string) =>
    request<LearningPlan | null>({ url: '/learning-plans/current', params: { learner_id: learnerId } }),
  generateLearningPlan: (learnerId: string, dailyMinutes = 30) =>
    request<LearningPlan>({ method: 'POST', url: '/learning-plans/generate', data: { learner_id: learnerId, daily_minutes: dailyMinutes } }),

  getCapabilities: () => request<CapabilityStatus>({ url: '/capabilities' }),

  getMetricsOverview: () => request<MetricsOverview>({ url: '/metrics/overview' }),
  getQualityMetric: (metric: 'hallucination' | 'adaptation' | 'coverage') =>
    request<QualityMetric>({ url: `/metrics/${metric}` }),

  uploadFile: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<UploadedFile>({ method: 'POST', url: '/files/upload', data: form })
  },
  createTask: (payload: {
    learner_id: string
    task_type: string
    file_id: string
    vision_mode: 'qwen' | 'local' | 'hybrid'
    llm_mode: 'mock' | 'real'
  }) => request<TaskCreated>({ method: 'POST', url: '/agent/tasks', data: payload }),
  recognizeUploadedFile: (payload: {
    learner_id: string
    file_id: string
    vision_mode?: 'mock' | 'qwen' | 'local' | 'hybrid'
  }) => request<RecognitionRecord>({ method: 'POST', url: '/vision/recognize', data: payload }),
  createRecognitionAdvice: (recognitionId: string) =>
    request<{ recognition_id: string; agent_status: RecognitionRecord['agent_status']; agent_task_id: string | null }>({
      method: 'POST',
      url: `/vision/records/${recognitionId}/agent-advice`,
    }),
  getTask: (taskId: string) => request<AgentTask>({ url: `/agent/tasks/${taskId}` }),
  getTaskEvents: (taskId: string) => request<TaskEvent[]>({ url: `/agent/tasks/${taskId}/events` }),
  getTaskLogs: (taskId: string) => request<AgentLog[]>({ url: `/agent/tasks/${taskId}/logs` }),
  getRecognitionRecordsByTask: (taskId: string) =>
    request<Paginated<RecognitionRecord>>({ url: `/vision/records/by-task/${taskId}` }),

  listMedicines: (keyword = '', pageSize = 50) =>
    request<Paginated<MedicineItem>>({
      url: '/medicines',
      params: { page: 1, page_size: pageSize, keyword: keyword || undefined },
    }),
  getMedicine: (id: number) => request<MedicineItem>({ url: `/medicines/${id}` }),
  getMedicineFeatures: (id: number) => request<MedicineFeature[]>({ url: `/medicines/${id}/features` }),
  getSimilarMedicines: (id: number) => request<SimilarMedicine[]>({ url: `/medicines/${id}/similar` }),
  retrieveKnowledge: (payload: {
    learner_id: string
    medicine_name: string
    task_type: string
    query?: string
    top_k: number
  }) => request<RetrievalResult>({ method: 'POST', url: '/knowledge/retrieve', data: payload }),

  listResources: (learnerId: string, pageSize = 50) =>
    request<Paginated<ResourceItem>>({
      url: '/resources',
      params: { page: 1, page_size: pageSize, learner_id: learnerId },
    }),
  getResource: (resourceId: string) => request<ResourceItem>({ url: `/resources/${resourceId}` }),
  generateResource: (payload: {
    learner_id: string
    medicine_name: string
    resource_type: string
    difficulty: string
    task_id?: string
    retrieval_id?: string
    evidence_ids?: string[]
  }) => request<ResourceItem>({ method: 'POST', url: '/resources/generate', data: payload }),
  createResourceGenerationJob: (payload: {
    learner_id: string
    learning_plan_item_id?: string
    task_id?: string
    resource_type: string
    difficulty: string
    requires_citation?: boolean
    topic?: string
    additional_instruction?: string | null
  }) => request<ResourceGenerationJob>({ method: 'POST', url: '/resource-generation-jobs', data: payload }),
  getResourceGenerationJob: (jobId: string) => request<ResourceGenerationJob>({ url: `/resource-generation-jobs/${jobId}` }),
  listResourceGenerationJobs: (learnerId: string) => request<{ items: ResourceGenerationJob[] }>({ url: '/resource-generation-jobs', params: { learner_id: learnerId } }),
  retryResource: (resourceId: string) => request<ResourceGenerationJob>({ method: 'POST', url: `/resources/${resourceId}/retry` }),
  reviewResource: (resourceId: string) =>
    request<ReviewResult>({ method: 'POST', url: '/reviews/check', params: { resource_id: resourceId } }),
  getResourceReview: (resourceId: string) => request<ReviewResult>({ url: `/reviews/${resourceId}` }),

  getLearningReport: (learnerId: string) =>
    request<ReportRecord>({ url: `/reports/learning/${learnerId}` }),
  generateLearningReport: (learnerId: string) =>
    request<ReportRecord>({ method: 'POST', url: `/reports/learning/${learnerId}/generate` }),
  exportLearningReport: (learnerId: string) =>
    request<ReportRecord>({ method: 'POST', url: `/reports/learning/${learnerId}/export-word` }),
  exportTaskReport: (taskId: string) =>
    request<ReportRecord>({ method: 'POST', url: `/reports/tasks/${taskId}/export-word` }),
  downloadReport: async (reportId: string) => {
    const response = await http.get<Blob>(`/reports/${reportId}/download`, { responseType: 'blob' })
    return response.data
  },

  listTraces: (pageSize = 50) =>
    request<Paginated<TraceRecord>>({ url: '/traces', params: { page: 1, page_size: pageSize } }),
  getTracesByTask: (taskId: string) => request<TraceRecord[]>({ url: `/traces/by-task/${taskId}` }),

  listAdminRecords: <T extends AdminRecord>(resource: string, page = 1, pageSize = 20) =>
    request<Paginated<T>>({
      url: `/admin/${resource}`,
      params: { page, page_size: pageSize },
    }),
  createAdminRecord: <T extends AdminRecord>(resource: string, data: JsonRecord) =>
    request<T>({ method: 'POST', url: `/admin/${resource}`, data: { data } }),
  updateAdminRecord: <T extends AdminRecord>(resource: string, id: number, data: JsonRecord) =>
    request<T>({ method: 'PUT', url: `/admin/${resource}/${id}`, data: { data } }),
  deleteAdminRecord: (resource: string, id: number) =>
    request<{ deleted: boolean }>({ method: 'DELETE', url: `/admin/${resource}/${id}` }),
  createAdminUser: (data: JsonRecord) =>
    request<AdminUser>({ method: 'POST', url: '/admin/users', data }),
  updateAdminUser: (id: number, data: JsonRecord) =>
    request<AdminUser>({ method: 'PUT', url: `/admin/users/${id}`, data }),
  deleteAdminUser: (id: number) =>
    request<{ deleted: boolean }>({ method: 'DELETE', url: `/admin/users/${id}` }),
  testAdminModel: (id: number) =>
    request<{ connected: boolean; model_name: string; elapsed_ms: number }>({
      method: 'POST',
      url: `/admin/model-configs/${id}/test`,
      data: { message: 'Return JSON with ok=true and reply=OK' },
    }),
}

export { ApiError }
