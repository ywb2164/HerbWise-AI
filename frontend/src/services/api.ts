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
  JsonRecord,
  LearnerDimension,
  LearnerProfile,
  LearningAnswer,
  LearningAnswerPayload,
  LearningPath,
  MedicineFeature,
  MedicineItem,
  ModelConnectionResult,
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

  constructor(code: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

function unwrap<T>(payload: ApiEnvelope<T> | T): T {
  if (payload && typeof payload === 'object' && 'code' in payload && 'data' in payload) {
    const envelope = payload as ApiEnvelope<T>
    if (envelope.code !== 0) throw new ApiError(envelope.code, envelope.message)
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

  getModelSettings: () => request<ModelSettingsStatus>({ url: '/model-settings' }),
  saveModelSettings: (payload: ModelSettingsPayload) =>
    request<ModelSettingsStatus>({ method: 'PUT', url: '/model-settings', data: payload }),
  testModelSettings: (payload: ModelSettingsPayload) =>
    request<ModelConnectionResult>({ method: 'POST', url: '/model-settings/test', data: payload }),
  clearModelSettings: () =>
    request<{ cleared: boolean }>({ method: 'DELETE', url: '/model-settings' }),

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
