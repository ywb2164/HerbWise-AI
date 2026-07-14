from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelCallContext(BaseModel):
    request_id: str | None = None
    task_id: str | None = None
    learner_id: str | None = None
    file_id: str | None = None
    agent_code: str
    prompt_template_code: str | None = None
    prompt_version: str | None = None
    provider: str | None = None
    model_name: str | None = None
    supported_catalog: list[dict[str, object]] = Field(default_factory=list)


class ProviderCallResult(BaseModel):
    success: bool
    provider: str
    model_name: str | None = None
    request_id: str | None = None
    latency_ms: float = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    retry_count: int = 0
    raw_response_reference: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class RecognitionCandidate(BaseModel):
    medicine_id: int | None = None
    herb_name: str
    english_name: str | None = None
    training_class_name: str | None = None
    confidence: float = Field(ge=0, le=1)
    in_supported_catalog: bool = True
    matched_by: str | None = None
    raw_name: str | None = None
    rank: int = Field(default=1, ge=1)
    bbox: list[float] | None = None


VisionCandidate = RecognitionCandidate


class RecognitionEvidence(BaseModel):
    evidence_type: str
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    source: str


class VisionRecognitionResult(BaseModel):
    provider: str = "mock"
    model_name: str | None = "mock-vision"
    file_id: str | None = None
    candidate: RecognitionCandidate | None = None
    top_candidates: list[RecognitionCandidate] = Field(default_factory=list)
    character_evidence: list[RecognitionEvidence] = Field(default_factory=list)
    quality_control_evidence: list[RecognitionEvidence] = Field(default_factory=list)
    traceability_advice: list[str] = Field(default_factory=list)
    uncertainty: str | None = None
    elapsed_ms: float = 0
    raw_result_reference: str | None = None
    data_source: str = "mock"
    fallback_used: bool = False
    errors: list[str] = Field(default_factory=list)
    recognized: bool = True
    material_type: str = "unknown"
    visible_evidence: list[str] = Field(default_factory=list)
    uncertain_features: list[str] = Field(default_factory=list)
    alternative_candidates: list[dict[str, Any]] = Field(default_factory=list)
    needs_review: bool = False

    @property
    def evidence(self) -> list[str]:
        return [item.text for item in self.character_evidence]


VisionResult = VisionRecognitionResult


class FusionResult(BaseModel):
    status: str = "success"
    final_candidate: RecognitionCandidate | None = None
    local_result: VisionRecognitionResult | None = None
    qwen_result: VisionRecognitionResult | None = None
    agreement_status: str
    confidence_before_adjustment: float = Field(default=0, ge=0, le=1)
    confidence_after_adjustment: float = Field(default=0, ge=0, le=1)
    adjustment: float = 0
    decision_reason: str
    manual_review_required: bool = False
    in_supported_catalog: bool = False
    rule_version: str = "v0.3a-fusion-v1"
    fallback_used: bool = False
    final_identification: dict[str, Any] = Field(default_factory=dict)
    yolo_reference: dict[str, Any] = Field(default_factory=dict)
    knowledge_match: dict[str, Any] = Field(default_factory=dict)
    knowledge_verification: dict[str, Any] = Field(default_factory=dict)


class KnowledgeEvidence(BaseModel):
    chunk_id: str
    content: str
    document_name: str
    page: int
    score: float
    source_type: str


class RAGQuery(BaseModel):
    query: str
    learner_id: str | None = None
    task_id: str | None = None
    medicine_id: int | None = None
    medicine_name: str | None = None
    task_type: str = "identification"
    top_k: int = Field(default=8, ge=1, le=20)
    score_threshold: float = Field(default=0.25, ge=0, le=1)
    filters: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None
    trace_id: str | None = None


class RAGEvidence(BaseModel):
    evidence_id: str
    medicine_id: int | None = None
    source_id: int | None = None
    dataset_id: str | None = None
    document_id: str | None = None
    document_name: str
    chunk_id: str | None = None
    page_number: int | None = None
    section_title: str | None = None
    content: str
    highlighted_content: str | None = None
    score: float = Field(ge=0, le=1)
    vector_score: float | None = None
    keyword_score: float | None = None
    rerank_score: float | None = None
    source_type: str
    citation: str
    coordinates_json: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_source: str
    retrieved_at: datetime | None = None
    rank: int | None = None
    retained_reason: str | None = None
    duplicate_of: str | None = None


class RAGRetrievalResult(BaseModel):
    success: bool
    query: str
    provider: str
    dataset_id: str | None = None
    evidences: list[RAGEvidence] = Field(default_factory=list)
    total_candidates: int = 0
    returned_count: int = 0
    latency_ms: float = 0
    cache_hit: bool = False
    replay_used: bool = False
    fallback_used: bool = False
    error_code: str | None = None
    error_message: str | None = None
    retrieval_metadata: dict[str, Any] = Field(default_factory=dict)
    data_source: str = "mock"


class GeneratedResource(BaseModel):
    title: str
    content: str
    resource_type: str = "study_note"
    content_json: dict[str, Any] | None = None


class ReviewResult(BaseModel):
    status: str
    summary: str = ""
    suggestions: list[str] = Field(default_factory=list)
    pharmacopoeia_consistency_score: float = 0
    terminology_accuracy_score: float = 0
    source_completeness_score: float = 0
    answer_accuracy_score: float = 0
    hallucination_risk_score: float = 0
    medical_risk_score: float = 0
    issues: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class PathUpdateResult(BaseModel):
    status: str
    next_steps: list[str]


class LLMProvider(ABC):
    @abstractmethod
    async def generate_resource(
        self, evidence: list[KnowledgeEvidence], context: ModelCallContext | None = None
    ) -> list[GeneratedResource]: ...

    @abstractmethod
    async def review_resource(
        self,
        resources: list[GeneratedResource],
        context: ModelCallContext | None = None,
    ) -> ReviewResult: ...

    @abstractmethod
    async def complete_structured(
        self,
        messages: list[dict[str, Any]],
        schema: type[BaseModel],
        context: ModelCallContext,
    ) -> BaseModel: ...

    @abstractmethod
    async def diagnose_profile(self, learner_id: str) -> dict: ...

    @abstractmethod
    async def update_learning_path(
        self, learner_id: str, review: ReviewResult
    ) -> PathUpdateResult: ...


class VisionProvider(ABC):
    @abstractmethod
    async def recognize(
        self,
        image_path: str | None,
        context: ModelCallContext | None = None,
    ) -> VisionRecognitionResult: ...


class LocalVisionProvider(ABC):
    @abstractmethod
    async def predict_image(
        self, image_path: str | None, context: ModelCallContext
    ) -> VisionRecognitionResult: ...


class RAGProvider(ABC):
    @abstractmethod
    async def retrieve(self, query: str) -> list[KnowledgeEvidence]: ...

    @abstractmethod
    async def retrieve_detailed(self, query: RAGQuery) -> RAGRetrievalResult: ...

    @abstractmethod
    async def health_check(self) -> dict[str, object]: ...

    @abstractmethod
    async def list_documents(
        self, dataset_id: str | None = None
    ) -> list[dict[str, object]]: ...

    @abstractmethod
    async def sync_document(self, document: dict[str, object]) -> dict[str, object]: ...

    @abstractmethod
    async def delete_document_mapping(self, external_document_id: str) -> None: ...
