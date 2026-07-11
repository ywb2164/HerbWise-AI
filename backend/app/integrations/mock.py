from app.integrations.contracts import (
    GeneratedResource,
    KnowledgeEvidence,
    LLMProvider,
    PathUpdateResult,
    RAGProvider,
    RAGQuery,
    RAGEvidence,
    RAGRetrievalResult,
    ReviewResult,
    RecognitionEvidence,
    VisionCandidate,
    VisionProvider,
    VisionResult,
    ModelCallContext,
)


class MockVisionProvider(VisionProvider):
    async def recognize(
        self, image_path: str | None, context: ModelCallContext | None = None
    ) -> VisionResult:
        candidates = [
            VisionCandidate(
                herb_name="黄芪", english_name="Astragalus", confidence=0.91
            ),
            VisionCandidate(
                herb_name="党参", english_name="Codonopsis", confidence=0.06
            ),
            VisionCandidate(herb_name="甘草", english_name="Licorice", confidence=0.03),
        ]
        return VisionResult(
            provider="mock",
            model_name="mock-vision-v1",
            file_id=context.file_id if context else None,
            candidate=candidates[0],
            top_candidates=candidates,
            character_evidence=[
                RecognitionEvidence(
                    evidence_type="appearance",
                    text="mock visible appearance",
                    source="mock",
                ),
                RecognitionEvidence(
                    evidence_type="surface", text="mock surface evidence", source="mock"
                ),
                RecognitionEvidence(
                    evidence_type="section", text="mock section evidence", source="mock"
                ),
            ],
            elapsed_ms=120,
        )


class MockRAGProvider(RAGProvider):
    async def retrieve(self, query: str) -> list[KnowledgeEvidence]:
        return [
            KnowledgeEvidence(
                chunk_id=f"mock_{index}",
                content=f"黄芪相关药典知识片段 {index}。",
                document_name="中国药典（示例）",
                page=index,
                score=round(0.96 - index * 0.03, 2),
                source_type="mock",
            )
            for index in range(1, 4)
        ]

    async def retrieve_detailed(self, query: RAGQuery) -> RAGRetrievalResult:
        evidence = [
            RAGEvidence(
                evidence_id=f"mock_evidence_{index}",
                dataset_id="mock-dataset",
                document_id="mock-document",
                document_name="中国药典（示例）",
                chunk_id=f"mock_{index}",
                page_number=index,
                content=f"{query.query} 的模拟来源证据片段 {index}。",
                score=round(0.96 - index * 0.03, 2),
                source_type="mock",
                citation=f"中国药典（示例） p.{index} [mock_{index}]",
                data_source="mock",
            )
            for index in range(1, min(query.top_k, 3) + 1)
        ]
        return RAGRetrievalResult(
            success=True,
            query=query.query,
            provider="mock",
            dataset_id="mock-dataset",
            evidences=evidence,
            total_candidates=len(evidence),
            returned_count=len(evidence),
            data_source="mock",
        )

    async def health_check(self) -> dict[str, object]:
        return {"configured": True, "reachable": True, "provider": "mock"}

    async def list_documents(
        self, dataset_id: str | None = None
    ) -> list[dict[str, object]]:
        return [
            {"document_id": "mock-document", "dataset_id": dataset_id or "mock-dataset"}
        ]

    async def sync_document(self, document: dict[str, object]) -> dict[str, object]:
        return {
            "success": True,
            "external_document_id": document.get("document_code", "mock-document"),
        }

    async def delete_document_mapping(self, external_document_id: str) -> None:
        del external_document_id


class MockLLMProvider(LLMProvider):
    async def generate_resource(
        self, evidence: list[KnowledgeEvidence], context: ModelCallContext | None = None
    ) -> list[GeneratedResource]:
        return [
            GeneratedResource(
                title="黄芪识别学习卡",
                content="黄芪（Astragalus）为豆科植物黄芪的干燥根。",
            ),
            GeneratedResource(
                title="巩固练习", content="请根据性状特征辨别黄芪、党参和甘草。"
            ),
        ]

    async def review_resource(
        self,
        resources: list[GeneratedResource],
        context: ModelCallContext | None = None,
    ) -> ReviewResult:
        return ReviewResult(status="pass", summary="模拟审核通过", suggestions=[])

    async def complete_structured(self, messages, schema, context):
        del messages, context
        return schema.model_validate({})

    async def diagnose_profile(self, learner_id: str) -> dict:
        return {
            "learner_id": learner_id,
            "level": "beginner",
            "strengths": ["基础辨识"],
        }

    async def update_learning_path(
        self, learner_id: str, review: ReviewResult
    ) -> PathUpdateResult:
        return PathUpdateResult(
            status="updated", next_steps=["复习黄芪性状", "完成辨识练习"]
        )
