import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import async_session_factory
from app.modules.learning_paths.models import LearningQuestion


async def seed() -> dict[str, int]:
    path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "seed"
        / "learning_questions.json"
    )
    questions = json.loads(path.read_text(encoding="utf-8"))
    summary = {"created": 0, "updated": 0, "skipped": 0}
    async with async_session_factory() as session:
        for item in questions:
            current = await session.scalar(
                select(LearningQuestion).where(
                    LearningQuestion.question_code == item["code"]
                )
            )
            values = {
                "question_type": item["question_type"],
                "stem": item["stem"],
                "options_json": item["options"],
                "answer_key": {"value": item["answer"]},
                "explanation": item["explanation"],
                "dimension_code": item["dimension_code"],
                "knowledge_point": item["knowledge_point"],
                "difficulty": item["difficulty"],
                "source": "competition_demo_seed",
                "review_status": "draft",
            }
            if current is None:
                session.add(LearningQuestion(question_code=item["code"], **values))
                summary["created"] += 1
            elif all(getattr(current, key) == value for key, value in values.items()):
                summary["skipped"] += 1
            else:
                for key, value in values.items():
                    setattr(current, key, value)
                summary["updated"] += 1
        await session.commit()
    return summary


if __name__ == "__main__":
    print(json.dumps(asyncio.run(seed()), ensure_ascii=False))
