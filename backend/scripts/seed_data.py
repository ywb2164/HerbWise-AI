import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import async_session_factory
from app.modules.profiles.models import LearnerDimension, LearnerProfile
from app.modules.tasks.models import TaskRecord


async def seed() -> None:
    async with async_session_factory() as session:
        profile = await session.scalar(
            select(LearnerProfile).where(LearnerProfile.learner_id == "stu_001")
        )
        if profile is None:
            session.add(
                LearnerProfile(
                    learner_id="stu_001",
                    display_name="示例学习者",
                    profile_json={"level": "beginner"},
                )
            )
            for key in (
                "herb_identification",
                "pharmacopoeia",
                "safety",
                "memory",
                "practice",
                "review",
            ):
                session.add(
                    LearnerDimension(
                        learner_id="stu_001",
                        dimension_key=key,
                        score=50,
                        detail_json={"seed": True},
                    )
                )

        task = await session.scalar(
            select(TaskRecord).where(TaskRecord.task_id == "task_seed_demo")
        )
        if task is None:
            session.add(
                TaskRecord(
                    task_id="task_seed_demo",
                    task_type="recognize_and_learn",
                    status="success",
                    learner_id="stu_001",
                    progress=100,
                    result_json={
                        "herb": "Astragalus",
                        "confidence": 0.91,
                        "mode": "mock",
                    },
                )
            )

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
