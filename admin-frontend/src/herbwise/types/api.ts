export type JsonRecord = Record<string, unknown>

export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
  request_id?: string | null
}

export interface Paginated<T> {
  items: T[]
  page: number
  page_size: number
  total: number
  pages: number
}

export interface UserSummary {
  id: number
  username: string
  display_name: string
  learner_id: string | null
  roles: string[]
  permissions: string[]
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: UserSummary
}

export type ModelProtocol = 'openai' | 'anthropic'

export interface ModelSettingsStatus {
  configured: boolean
  protocol: ModelProtocol
  base_url: string
  model_id: string
  api_key_masked: string
  configured_at: string | null
  storage: 'server_memory'
}

export interface ModelSettingsPayload {
  protocol: ModelProtocol
  base_url: string
  model_id: string
  api_key?: string
}

export interface ModelConnectionResult {
  connected: boolean
  protocol: ModelProtocol
  model_id: string
  elapsed_ms: number
  reply: string
}

export interface AdminRecord extends JsonRecord {
  id: number
}

export interface AdminUser extends AdminRecord {
  username: string
  display_name: string
  email?: string | null
  learner_id?: string | null
  is_active: boolean
  is_superuser: boolean
  roles?: string[]
  last_login_at?: string | null
  created_at?: string
}

export interface LearnerProfile {
  learner_id: string
  user_id?: number | null
  name: string
  identity_type: string
  education_background?: string | null
  professional_background?: string | null
  learning_goal?: string | null
  learning_preference?: string | null
  overall_level: string
  diagnosis_summary?: string | null
  created_at?: string
  updated_at?: string
}

export interface LearnerDimension {
  dimension_code: string
  score: number
  level: string
  evidence_json?: JsonRecord
  updated_at?: string
}

export interface WeakPoint {
  dimension_code: string
  knowledge_point: string
  severity: string
  evidence_json?: JsonRecord
  is_resolved: boolean
  created_at?: string
  resolved_at?: string | null
}

export interface LearningPath {
  learner_id: string
  version: number
  status: string
  current_stage: string
  path: {
    current_stage?: string
    recommended_task_types?: string[]
    average_score?: number
    rule_version?: string
    [key: string]: unknown
  }
  reason?: string
  created_at?: string
  updated_at?: string
}

export interface MetricsOverview {
  learner_count: number
  medicine_count: number
  task_count: number
  successful_task_count: number
  failed_task_count: number
  resource_count: number
  approved_resource_count: number
  review_count: number
  path_update_count: number
  knowledge_source_count: number
  data_source: string
  is_official: boolean
}

export interface QualityMetric {
  metric_code: string
  data_source: string
  is_official: boolean
  calculation_method: string
  sample_count: number
  metric_value: number | null
}

export interface UploadedFile {
  file_id: string
  original_name: string
  relative_path: string
  mime_type: string
  size_bytes: number
  sha256: string
  created_at: string
}

export interface TaskCreated {
  task_id: string
  status: string
}

export interface RecognitionCandidate {
  medicine_id?: number | null
  herb_name?: string
  english_name?: string
  confidence?: number
  source_provider?: string
  elapsed_ms?: number
  [key: string]: unknown
}

export interface KnowledgeEvidence {
  evidence_id?: string
  document_id?: string | null
  document_name?: string
  chunk_id?: string | null
  page_number?: number | null
  content?: string
  score?: number
  citation?: string
  rank?: number
  data_source?: string
  source?: string
  [key: string]: unknown
}

export interface ResourceItem {
  resource_id: string
  learner_id: string
  task_id?: string | null
  medicine_id?: number | null
  resource_type: string
  title: string
  content_markdown: string
  content_json?: JsonRecord
  difficulty: string
  status: string
  provider: string
  model_name?: string | null
  prompt_version?: string | null
  created_at?: string
  updated_at?: string
}

export interface ReviewResult {
  review_id: string
  resource_id: string
  status: string
  pharmacopoeia_consistency_score?: number | null
  terminology_accuracy_score?: number | null
  source_completeness_score?: number | null
  answer_accuracy_score?: number | null
  hallucination_risk_score?: number | null
  medical_risk_score?: number | null
  issues: string[]
  suggestions: string[]
  evidence?: JsonRecord
  provider: string
  reviewed_at?: string
}

export interface TaskResult extends JsonRecord {
  recognition_id?: string
  recognition_result?: {
    candidate?: RecognitionCandidate
    top_candidates?: RecognitionCandidate[]
    provider?: string
    model_name?: string | null
    elapsed_ms?: number
  }
  fusion_result?: JsonRecord & {
    manual_review_required?: boolean
    agreement_status?: string
    confidence_after_adjustment?: number
    decision_reason?: string
  }
  judge_result?: JsonRecord & {
    status?: string
    reason?: string
    manual_review_required?: boolean
    data_source?: string
  }
  knowledge_evidence?: KnowledgeEvidence[]
  retrieval_id?: string
  generated_resources?: ResourceItem[]
  review_result?: ReviewResult
  path_update?: LearningPath
  trace_id?: string
}

export interface AgentTask {
  task_id: string
  learner_id: string
  task_type: string
  status: string
  current_node: string | null
  progress: number
  result: TaskResult | null
  error_message: string | null
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

export interface TaskEvent {
  event: string
  task_id: string
  node: string
  status: string
  progress: number
  elapsed_ms: number | null
  summary: string
  timestamp: string
}

export interface AgentLog {
  node: string
  provider: string | null
  model_name: string | null
  status: string
  elapsed_ms: number | null
  input_summary: string
  output_summary: string
  created_at: string
}

export interface MedicineItem {
  id: number
  medicine_code: string
  standard_name_zh: string
  standard_name_en?: string | null
  training_class_name?: string | null
  latin_name?: string | null
  source?: string | null
  properties_flavor?: string | null
  meridian_tropism?: string | null
  description?: string | null
  matched_by?: string
  is_active?: boolean
}

export interface MedicineFeature {
  id?: number
  feature_id?: number
  medicine_id?: number
  feature_type: string
  feature_name: string
  feature_value: string
  sort_order?: number
}

export interface SimilarMedicine {
  id?: number
  medicine_id?: number
  similar_medicine_id?: number
  similar_name?: string
  confusion_reason?: string | null
  distinguishing_features?: JsonRecord
  risk_level?: string
}

export interface RetrievalResult {
  retrieval_id: string
  task_id?: string | null
  learner_id?: string | null
  query?: string
  provider?: string
  returned_count?: number
  latency_ms?: number
  cache_hit?: boolean
  replay_used?: boolean
  fallback_used?: boolean
  status?: string
  data_source?: string
  evidences: KnowledgeEvidence[]
  [key: string]: unknown
}

export interface ReportRecord {
  report_id: string
  learner_id: string
  report_type: string
  title: string
  content: JsonRecord
  file_id?: string | null
  download_available: boolean
  status: string
  created_at?: string
  updated_at?: string
}

export interface TraceRecord {
  trace_id: string
  task_id: string
  learner_id: string
  trace_data: TaskResult & JsonRecord
  created_at?: string
  updated_at?: string
}
