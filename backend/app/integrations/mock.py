from app.integrations.contracts import (
    GeneratedResource,
    KnowledgeEvidence,
    LLMProvider,
    PathUpdateResult,
    RAGProvider,
    ReviewResult,
    VisionCandidate,
    VisionProvider,
    VisionResult,
)


class MockVisionProvider(VisionProvider):
    async def recognize(self, image_path: str | None) -> VisionResult:
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
            candidate=candidates[0],
            top_candidates=candidates,
            evidence=["根部呈圆柱形", "表面淡棕黄色", "断面纤维性"],
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


class MockLLMProvider(LLMProvider):
    async def generate_resource(
        self, evidence: list[KnowledgeEvidence]
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

    async def review_resource(self, resources: list[GeneratedResource]) -> ReviewResult:
        return ReviewResult(status="pass", summary="模拟审核通过", suggestions=[])

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
