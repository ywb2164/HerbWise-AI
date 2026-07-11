from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class VisionCandidate(BaseModel):
    herb_name: str
    english_name: str
    confidence: float


class VisionResult(BaseModel):
    candidate: VisionCandidate
    top_candidates: list[VisionCandidate]
    evidence: list[str]
    elapsed_ms: int


class KnowledgeEvidence(BaseModel):
    chunk_id: str
    content: str
    document_name: str
    page: int
    score: float
    source_type: str


class GeneratedResource(BaseModel):
    title: str
    content: str
    resource_type: str = "study_note"


class ReviewResult(BaseModel):
    status: str
    summary: str
    suggestions: list[str] = Field(default_factory=list)


class PathUpdateResult(BaseModel):
    status: str
    next_steps: list[str]


class LLMProvider(ABC):
    @abstractmethod
    async def generate_resource(
        self, evidence: list[KnowledgeEvidence]
    ) -> list[GeneratedResource]: ...

    @abstractmethod
    async def review_resource(
        self, resources: list[GeneratedResource]
    ) -> ReviewResult: ...

    @abstractmethod
    async def diagnose_profile(self, learner_id: str) -> dict: ...

    @abstractmethod
    async def update_learning_path(
        self, learner_id: str, review: ReviewResult
    ) -> PathUpdateResult: ...


class VisionProvider(ABC):
    @abstractmethod
    async def recognize(self, image_path: str | None) -> VisionResult: ...


class RAGProvider(ABC):
    @abstractmethod
    async def retrieve(self, query: str) -> list[KnowledgeEvidence]: ...
