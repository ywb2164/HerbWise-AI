import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import async_session_factory
from app.modules.auth.models import Role, User
from app.modules.auth.service import hash_password
from app.modules.knowledge.models import MedicineAlias, MedicineFeature, MedicineItem
from app.modules.profiles.models import (
    LearnerDimension,
    LearnerProfile,
    TestOption,
    TestQuestion,
)
from app.modules.profiles.rules import DIMENSION_CODES, score_level
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

    # The original workflow seed is retained above; V0.2 additions below are
    # idempotent and contain only clearly labelled demonstration data.
    async with async_session_factory() as session:
        roles: dict[str, Role] = {}
        for code in (
            "admin",
            "student",
            "teacher",
            "clinical_pharmacist",
            "quality_inspector",
        ):
            role = await session.scalar(select(Role).where(Role.code == code))
            if role is None:
                role = Role(
                    code=code,
                    name=code.replace("_", " ").title(),
                    description="demo_seed_data",
                )
                session.add(role)
                await session.flush()
            roles[code] = role
        for username, display_name, role_code, learner_id, is_superuser in (
            ("admin", "System administrator", "admin", None, True),
            ("student", "Demo student", "student", "stu_001", False),
        ):
            user = await session.scalar(select(User).where(User.username == username))
            if user is None:
                user = User(
                    username=username,
                    password_hash=hash_password("HerbWise@2026"),
                    display_name=display_name,
                    learner_id=learner_id,
                    is_superuser=is_superuser,
                )
                user.roles.append(roles[role_code])
                session.add(user)
        for code in DIMENSION_CODES:
            dimension = await session.scalar(
                select(LearnerDimension).where(
                    LearnerDimension.learner_id == "stu_001",
                    LearnerDimension.dimension_code == code,
                )
            )
            if dimension is None:
                session.add(
                    LearnerDimension(
                        learner_id="stu_001",
                        dimension_key=code,
                        dimension_code=code,
                        score=50,
                        level=score_level(50),
                        detail_json={"seed": "demo_seed_data"},
                        evidence_json={"seed": "demo_seed_data"},
                    )
                )
        for code, zh, en in (
            ("astragalus", "黄芪", "Astragalus"),
            ("codonopsis", "党参", "Codonopsis"),
            ("licorice", "甘草", "Licorice"),
        ):
            medicine = await session.scalar(
                select(MedicineItem).where(MedicineItem.medicine_code == code)
            )
            if medicine is None:
                medicine = MedicineItem(
                    medicine_code=code,
                    standard_name_zh=zh,
                    standard_name_en=en,
                    training_class_name=zh,
                    description="demo_seed_data",
                )
                session.add(medicine)
                await session.flush()
            if not await session.scalar(
                select(MedicineAlias).where(
                    MedicineAlias.medicine_id == medicine.id,
                    MedicineAlias.normalized_name == zh,
                )
            ):
                session.add(
                    MedicineAlias(
                        medicine_id=medicine.id,
                        alias_name=zh,
                        alias_type="demo",
                        language="zh",
                        normalized_name=zh,
                    )
                )
            if not await session.scalar(
                select(MedicineFeature).where(
                    MedicineFeature.medicine_id == medicine.id,
                    MedicineFeature.feature_name == "demo_feature",
                )
            ):
                session.add(
                    MedicineFeature(
                        medicine_id=medicine.id,
                        feature_type="appearance",
                        feature_name="demo_feature",
                        feature_value="demo_seed_data",
                    )
                )
        for index, code in enumerate(DIMENSION_CODES, start=1):
            for offset in range(2):
                question_code = f"initial_{index}_{offset + 1}"
                if await session.scalar(
                    select(TestQuestion).where(
                        TestQuestion.question_code == question_code
                    )
                ):
                    continue
                question = TestQuestion(
                    question_code=question_code,
                    dimension_code=code,
                    question_type="single_choice",
                    stem=f"Demo question {index}-{offset + 1}",
                    difficulty="basic",
                    correct_answer_json={"value": "A"},
                    explanation="demo_seed_data",
                    score=1,
                )
                session.add(question)
                await session.flush()
                session.add_all(
                    [
                        TestOption(
                            question_id=question.id,
                            option_key="A",
                            option_text="Correct",
                            sort_order=1,
                        ),
                        TestOption(
                            question_id=question.id,
                            option_key="B",
                            option_text="Incorrect",
                            sort_order=2,
                        ),
                    ]
                )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
