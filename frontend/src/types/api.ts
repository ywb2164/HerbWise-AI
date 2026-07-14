export type JsonRecord = Record<string, unknown>

export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
  error_code?: string | null
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
export type ModelPurpose = 'vision' | 'text'

export interface ModelSettingsStatus {
  purpose: ModelPurpose
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
  purpose: ModelPurpose
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

export type DimensionCode =
  | 'basic_knowledge'
  | 'character_identification'
  | 'similar_medicine'
  | 'pharmacopoeia_rules'
  | 'clinical_quality_control'
  | 'practical_review'

export interface ProfilePayload {
  learner_id: string
  name: string
  identity_type: string
  user_id?: number | null
  education_background?: string | null
  professional_background?: string | null
  learning_goal?: string | null
  learning_preference?: string | null
}

export type ProfileUpdatePayload = Omit<ProfilePayload, 'learner_id' | 'user_id'>

export interface InitialQuestionOption {
  key: string
  text: string
  sort_order: number
}

export interface InitialQuestion {
  id: number
  question_code: string
  dimension_code: DimensionCode
  question_type: string
  stem: string
  difficulty: string
  score: number
  options: InitialQuestionOption[]
}

export interface DiagnosisResult {
  dimension_scores: Record<DimensionCode, number>
  overall_score: number
  overall_level: string
  weak_dimensions: DimensionCode[]
  weak_knowledge_points: string[]
  diagnosis_summary: string
  recommended_resource_types: string[]
  recommended_next_task: string
}

export interface InitialTestResult {
  record_id: string
  total_score: number
  dimension_scores: Record<DimensionCode, number>
  diagnosis: DiagnosisResult
}

export interface ProfileHistoryItem {
  event_type: string
  before_json?: JsonRecord | null
  after_json?: JsonRecord | null
  reason: string
  source_task_id?: string | null
  created_at?: string
}

export interface LearningAnswerPayload {
  learner_id: string
  task_id?: string | null
  question_id?: number | null
  dimension_code: DimensionCode
  knowledge_point: string
  answer: JsonRecord
  is_correct: boolean
  score: number
  feedback?: string | null
}

export interface LearningAnswer extends LearningAnswerPayload {
  id: number
  submitted_at?: string
}

export interface InitialTestStatus {
  completed: boolean
  record_id: string | null
  submitted_at: string | null
}

export interface LearningTaskQuestion {
  question_id: number
  question_type: 'single_choice' | 'multiple_choice' | 'true_false'
  stem: string
  options: Array<{ key: string; text: string }>
  dimension_code: DimensionCode
  knowledge_point: string
  difficulty: string
  order_index: number
  score_weight: number
}

export interface LearningTask {
  task_id: string
  title: string
  task_type: string
  source: string
  status: string
  difficulty: string
  estimated_minutes: number | null
  deadline: string | null
  progress: number
  target_dimensions: DimensionCode[]
  target_knowledge_points: string[]
  resource_ids: string[]
  created_at?: string
  started_at?: string | null
  completed_at?: string | null
  question_count?: number
  latest_attempt?: {
    attempt_id: string
    submitted_at?: string | null
    raw_score?: number | null
    accuracy?: number | null
    wrong_count?: number
  } | null
}

export interface LearningTaskDetail extends LearningTask {
  questions: LearningTaskQuestion[]
}

export interface LearningTaskAttempt {
  task_id: string
  attempt_id: string
  status: 'in_progress'
  started_at: string
  questions: LearningTaskQuestion[]
}

export interface LearningTaskResult {
  task_id: string
  attempt_id: string
  status: 'completed'
  raw_score: number
  final_score: number
  accuracy: number
  duration_seconds: number
  question_results: Array<{
    question_id: number
    student_answer: string | string[] | null
    correct_answer: string | string[]
    is_correct: boolean
    score: number
    explanation: string
  }>
  dimension_changes: Array<{ dimension_code: DimensionCode; before: number; after: number; delta: number; reason: string }>
  weak_point_changes: Array<{ dimension_code: DimensionCode; knowledge_point: string; before: string | null; after: string; reason: string }>
  next_task: LearningTask | null
}

export interface LearningPlanItem {
  item_id: string
  order_index: number
  title: string
  reason: string
  target_dimensions: string[]
  target_knowledge_points: string[]
  task_type: string
  difficulty: 'basic' | 'intermediate' | 'advanced' | string
  estimated_minutes: number
  resource_type: string
  status: 'pending' | 'in_progress' | 'completed' | 'skipped' | string
  linked_task_id: string | null
  linked_resource_id: string | null
}

export interface LearningPlan {
  plan_id: string
  status: string
  stage: string
  summary: string
  goal: string
  daily_minutes: number
  total_estimated_minutes: number
  fallback_used: boolean
  items: LearningPlanItem[]
}

export interface CapabilityStatus {
  ai_mode: string
  vision_mode: string
  llm_mode: string
  rag_mode: string
  qwen_configured: boolean
  local_model_configured: boolean
  local_model_loaded: boolean
  knowledge_catalog_loaded: boolean
  knowledge_catalog_record_count: number
  generation_model_configured: boolean
  review_model_configured: boolean
  mock_fallback_available: boolean
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
  training_class_name?: string | null
  raw_name?: string | null
  confidence?: number
  rank?: number
  in_supported_catalog?: boolean
  matched_by?: string | null
  source_provider?: string
  elapsed_ms?: number
  bbox?: number[] | null
  [key: string]: unknown
}

export interface RecognitionEvidence extends JsonRecord {
  evidence_type: string
  text: string
  confidence?: number | null
  source: string
}

export interface VisionRecognitionResult extends JsonRecord {
  provider?: string
  model_name?: string | null
  candidate?: RecognitionCandidate | null
  top_candidates?: RecognitionCandidate[]
  character_evidence?: RecognitionEvidence[]
  quality_control_evidence?: RecognitionEvidence[]
  traceability_advice?: string[]
  uncertainty?: string | null
  elapsed_ms?: number
  data_source?: string
  recognized?: boolean
  material_type?: string
  visible_evidence?: string[]
  uncertain_features?: string[]
  alternative_candidates?: Array<{ name_en: string; confidence: number }>
  needs_review?: boolean
}

export interface RecognitionFusionResult extends JsonRecord {
  final_candidate?: RecognitionCandidate | null
  manual_review_required?: boolean
  agreement_status?: string
  confidence_after_adjustment?: number
  confidence_before_adjustment?: number
  decision_reason?: string
  local_result?: VisionRecognitionResult | null
  qwen_result?: VisionRecognitionResult | null
  final_identification?: JsonRecord
  yolo_reference?: VisionRecognitionResult | JsonRecord
  knowledge_match?: JsonRecord
  knowledge_verification?: JsonRecord
}

export interface RecognitionRecord {
  recognition_id: string
  task_id?: string | null
  learner_id: string
  file_id: string
  vision_mode: string
  status: string
  recognition_status?: 'uploaded' | 'recognizing' | 'normalizing' | 'completed' | 'unrecognized' | 'failed'
  agent_status?: 'not_started' | 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  agent_task_id?: string | null
  final_medicine_id?: number | null
  final_name?: string | null
  confidence?: number | null
  agreement_status?: string | null
  manual_review_required: boolean
  local_result?: VisionRecognitionResult | null
  qwen_result?: VisionRecognitionResult | null
  fusion_result?: RecognitionFusionResult | null
  provider_failures?: ProviderFailure[] | null
  data_source: string
  final_identification?: JsonRecord | null
  yolo_reference?: VisionRecognitionResult | JsonRecord | null
  knowledge_match?: JsonRecord | null
  knowledge_verification?: JsonRecord | null
  agent_result?: JsonRecord | null
  agent_error?: JsonRecord | null
  created_at?: string
}

export interface ProviderFailure extends JsonRecord {
  provider: string
  error_code: string
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
  plan_id?: string | null
  learning_plan_item_id?: string | null
  task_id?: string | null
  medicine_id?: number | null
  resource_type: string
  title: string
  content_markdown: string
  content_json?: JsonRecord
  learning_objectives?: string[]
  target_dimensions?: string[]
  target_knowledge_points?: string[]
  difficulty: string
  estimated_minutes?: number | null
  personalization_reason?: string | null
  status: string
  provider: string
  model_name?: string | null
  prompt_version?: string | null
  requires_rag?: boolean
  retrieval_id?: string | null
  citation_count?: number
  citations?: Array<{ evidence_id: string; citation: string }>
  review_status?: string | null
  review_score?: number | null
  rewrite_count?: number
  version?: number
  parent_resource_id?: string | null
  data_source?: string
  fallback_used?: boolean
  created_at?: string
  updated_at?: string
}

export interface ResourceGenerationJob {
  job_id: string
  learner_id: string
  plan_id?: string | null
  learning_plan_item_id?: string | null
  task_id?: string | null
  resource_type: string
  difficulty: string
  status: string
  requires_rag: boolean
  rag_reason_codes: string[]
  retrieval_id?: string | null
  resource_id?: string | null
  error_code?: string | null
  error_message?: string | null
  created_at?: string
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
  recognition_result?: VisionRecognitionResult
  fusion_result?: RecognitionFusionResult
  provider_failures?: ProviderFailure[]
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
  agent_result?: JsonRecord
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
