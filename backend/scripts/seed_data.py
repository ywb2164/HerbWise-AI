import asyncio
import sys
from pathlib import Path

from sqlalchemy import or_, select

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import async_session_factory
from app.modules.auth.models import Menu, Permission, Role, User
from app.modules.auth.service import hash_password
from app.modules.knowledge.models import (
    KnowledgeSource,
    MedicineAlias,
    MedicineFeature,
    MedicineItem,
    SimilarMedicine,
)
from app.modules.profiles.models import (
    LearnerDimension,
    LearnerProfile,
    TestOption,
    TestQuestion,
)
from app.modules.profiles.rules import DIMENSION_CODES, score_level
from app.modules.resources.business_models import PromptTemplate
from app.modules.system.models import AgentConfig, ModelConfig, SystemConfig, TestCase
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
        permissions: dict[str, Permission] = {}
        for code, name in (
            ("profile.read", "Read learner profiles"),
            ("profile.write", "Manage learner profiles"),
            ("medicine.read", "Read medicine knowledge"),
            ("learning.write", "Submit learning activity"),
            ("admin.manage", "Manage backend configuration"),
        ):
            permission = await session.scalar(
                select(Permission).where(Permission.code == code)
            )
            if permission is None:
                permission = Permission(
                    code=code, name=name, description="demo_seed_data"
                )
                session.add(permission)
                await session.flush()
            permissions[code] = permission
        menus: dict[str, Menu] = {}
        for index, (code, name, path, permission_code) in enumerate(
            (
                ("dashboard", "Dashboard", "/dashboard", "profile.read"),
                ("profiles", "Learner profiles", "/profiles", "profile.read"),
                ("recognition", "Recognition", "/recognition", "medicine.read"),
                ("resources", "Resources", "/resources", "learning.write"),
                ("admin", "Administration", "/admin", "admin.manage"),
            ),
            start=1,
        ):
            menu = await session.scalar(select(Menu).where(Menu.code == code))
            if menu is None:
                menu = Menu(
                    code=code,
                    name=name,
                    path=path,
                    component=code,
                    sort_order=index,
                    menu_type="menu",
                    permission_code=permission_code,
                    is_visible=True,
                    is_enabled=True,
                )
                session.add(menu)
                await session.flush()
            menus[code] = menu
        for permission in permissions.values():
            if permission not in roles["admin"].permissions:
                roles["admin"].permissions.append(permission)
        for menu in menus.values():
            if menu not in roles["admin"].menus:
                roles["admin"].menus.append(menu)
        for code in ("profile.read", "medicine.read", "learning.write"):
            if permissions[code] not in roles["student"].permissions:
                roles["student"].permissions.append(permissions[code])
        for code in ("dashboard", "profiles", "recognition", "resources"):
            if menus[code] not in roles["student"].menus:
                roles["student"].menus.append(menus[code])

        profile = await session.scalar(
            select(LearnerProfile).where(LearnerProfile.learner_id == "stu_001")
        )
        if profile is not None:
            profile.name = profile.name or profile.display_name or "Demo learner"
            profile.identity_type = profile.identity_type or "student"
            profile.overall_level = profile.overall_level or "weak"
        legacy_dimension_keys = {
            "basic_knowledge": "memory",
            "character_identification": "herb_identification",
            "similar_medicine": "review",
            "pharmacopoeia_rules": "pharmacopoeia",
            "clinical_quality_control": "safety",
            "practical_review": "practice",
        }
        for code in DIMENSION_CODES:
            dimension = await session.scalar(
                select(LearnerDimension).where(
                    LearnerDimension.learner_id == "stu_001",
                    or_(
                        LearnerDimension.dimension_code == code,
                        LearnerDimension.dimension_key == legacy_dimension_keys[code],
                    ),
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
            else:
                dimension.dimension_key = code
                dimension.dimension_code = code
                dimension.level = dimension.level or score_level(dimension.score)
                dimension.evidence_json = dimension.evidence_json or {
                    "seed": "demo_seed_data"
                }
        medicine_records: dict[str, MedicineItem] = {}
        for code, zh, en, alias_name in (
            ("astragalus", "黄芪", "Astragalus", "黄耆"),
            ("codonopsis", "党参", "Codonopsis", "潞党参"),
            ("licorice", "甘草", "Licorice", "国老"),
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
            medicine_records[code] = medicine
            if not await session.scalar(
                select(MedicineAlias).where(
                    MedicineAlias.medicine_id == medicine.id,
                    MedicineAlias.normalized_name == alias_name,
                )
            ):
                session.add(
                    MedicineAlias(
                        medicine_id=medicine.id,
                        alias_name=alias_name,
                        alias_type="demo",
                        language="zh",
                        normalized_name=alias_name,
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
        if not await session.scalar(
            select(SimilarMedicine).where(
                SimilarMedicine.medicine_id == medicine_records["astragalus"].id,
                SimilarMedicine.similar_medicine_id
                == medicine_records["codonopsis"].id,
            )
        ):
            session.add(
                SimilarMedicine(
                    medicine_id=medicine_records["astragalus"].id,
                    similar_medicine_id=medicine_records["codonopsis"].id,
                    confusion_reason="demo_seed_data: root appearance can be confused",
                    distinguishing_features_json={
                        "data_source": "demo_seed_data",
                        "features": ["surface", "section"],
                    },
                    risk_level="low",
                )
            )
        if not await session.scalar(
            select(KnowledgeSource).where(
                KnowledgeSource.source_code == "demo-knowledge-v1"
            )
        ):
            session.add(
                KnowledgeSource(
                    source_code="demo-knowledge-v1",
                    source_name="Demonstration knowledge source",
                    source_type="demo",
                    version="v1",
                    citation="Not a pharmacopoeia source; demonstration data only",
                    copyright_note="demo_seed_data",
                    review_status="demo_seed_data",
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

        model_config = await session.scalar(
            select(ModelConfig).where(ModelConfig.config_code == "mock-default")
        )
        if model_config is None:
            model_config = ModelConfig(
                config_code="mock-default",
                provider="mock",
                model_name="mock-llm",
                model_type="text",
                credential_reference=None,
                timeout_seconds=30,
                max_retries=1,
                extra_json={"seed": "demo_seed_data"},
            )
            session.add(model_config)
            await session.flush()
        prompt = await session.scalar(
            select(PromptTemplate).where(
                PromptTemplate.template_code == "resource-default-v1"
            )
        )
        if prompt is None:
            prompt = PromptTemplate(
                template_code="resource-default-v1",
                name="Default mock resource prompt",
                task_type="lecture",
                system_prompt="Generate a clearly labelled mock learning resource.",
                user_prompt_template="Medicine: {medicine_name}; learner: {learner_id}",
                output_schema_json={"type": "object"},
                version="v1",
                is_active=True,
            )
            session.add(prompt)
            await session.flush()
        for node in (
            "load_profile",
            "recognize_image",
            "vision_review",
            "retrieve_knowledge",
            "judge_result",
            "generate_resources",
            "review_resources",
            "update_learning_path",
            "save_trace",
        ):
            if not await session.scalar(
                select(AgentConfig).where(AgentConfig.agent_code == node)
            ):
                session.add(
                    AgentConfig(
                        agent_code=node,
                        name=node.replace("_", " ").title(),
                        description="demo_seed_data",
                        workflow_node=node,
                        model_config_id=model_config.id,
                        prompt_template_id=(
                            prompt.id
                            if node in {"generate_resources", "review_resources"}
                            else None
                        ),
                        timeout_seconds=30,
                        max_retries=1,
                        enabled=True,
                        config_json={"mode": "mock"},
                    )
                )
        for key, value in (
            ("ai_mode", {"value": "mock"}),
            ("rag_mode", {"value": "mock"}),
            ("yolo_mode", {"value": "mock"}),
        ):
            if not await session.scalar(
                select(SystemConfig).where(SystemConfig.config_key == key)
            ):
                session.add(
                    SystemConfig(
                        config_key=key,
                        config_value_json=value,
                        description="demo_seed_data",
                        is_public=True,
                    )
                )
        for index, case_type in enumerate(
            ("recognition", "resource_generation", "review"), start=1
        ):
            code = f"demo_case_{index}"
            if not await session.scalar(
                select(TestCase).where(TestCase.case_code == code)
            ):
                session.add(
                    TestCase(
                        case_code=code,
                        name=f"Demo {case_type} case",
                        case_type=case_type,
                        input_json={"data_source": "mock"},
                        expected_json={"status": "success"},
                        tags_json=["demo_seed_data"],
                        status="active",
                    )
                )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
