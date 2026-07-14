"""add deterministic learning task loop

Revision ID: f1a2b3c4d5e6
Revises: e4d1b8f0c692
"""

from alembic import op
from sqlalchemy import UniqueConstraint, inspect

import app.models  # noqa: F401
from app.core.database import Base

revision = "f1a2b3c4d5e6"
down_revision = "e4d1b8f0c692"
branch_labels = None
depends_on = None

NEW_TABLES = (
    "learning_questions",
    "learning_task_questions",
    "learning_task_attempts",
    "learning_task_answers",
    "learning_events",
)
# ``learning_paths`` was added while the earlier broad V0.2 migration was
# still being developed.  Databases upgraded before those models were
# registered can therefore legitimately be at ``e4...`` without these tables.
# Create the prerequisite tables here as well, so the migration is safe for
# both fresh databases and those older local development volumes.
PREREQUISITE_TABLES = (
    "learning_answers",
    "learning_tasks",
    "learning_paths",
    "path_reports",
    "report_records",
)
TASK_COLUMNS = (
    "source",
    "estimated_minutes",
    "deadline",
    "target_dimension_codes_json",
    "target_knowledge_points_json",
    "resource_ids_json",
    "learning_path_id",
    "started_at",
    "updated_at",
)


def _create_table_if_missing(table_name: str, table_names: set[str]) -> None:
    if table_name in table_names:
        return

    table = Base.metadata.tables[table_name]
    op.create_table(
        table_name,
        *[column._copy() for column in table.columns],
        *[
            constraint._copy()
            # ``constraint._copy()`` attaches the copy to the table and can
            # mutate SQLAlchemy's underlying constraint set.  Snapshot it
            # before iterating so migrations work consistently on MySQL.
            for constraint in list(table.constraints)
            if isinstance(constraint, UniqueConstraint) and constraint.name
        ],
    )
    table_names.add(table_name)


def upgrade() -> None:
    bind = op.get_bind()
    table_names = set(inspect(bind).get_table_names())
    for table in (*PREREQUISITE_TABLES, *NEW_TABLES):
        _create_table_if_missing(table, table_names)
    existing = {
        column["name"] for column in inspect(bind).get_columns("learning_tasks")
    }
    for name in TASK_COLUMNS:
        if name not in existing:
            op.add_column(
                "learning_tasks", Base.metadata.tables["learning_tasks"].c[name]._copy()
            )
    indexes = {
        "learning_questions": (
            ("ix_learning_questions_question_code", ["question_code"]),
            ("ix_learning_questions_dimension_code", ["dimension_code"]),
            ("ix_learning_questions_knowledge_point", ["knowledge_point"]),
            ("ix_learning_questions_difficulty", ["difficulty"]),
        ),
        "learning_task_questions": (
            ("ix_learning_task_questions_task_id", ["task_id"]),
            ("ix_learning_task_questions_question_id", ["question_id"]),
        ),
        "learning_task_attempts": (
            ("ix_learning_task_attempts_attempt_id", ["attempt_id"]),
            ("ix_learning_task_attempts_task_id", ["task_id"]),
            ("ix_learning_task_attempts_learner_id", ["learner_id"]),
            ("ix_learning_task_attempts_status", ["status"]),
        ),
        "learning_task_answers": (
            ("ix_learning_task_answers_attempt_id", ["attempt_id"]),
            ("ix_learning_task_answers_question_id", ["question_id"]),
        ),
        "learning_events": (
            ("ix_learning_events_learner_id", ["learner_id"]),
            ("ix_learning_events_source_id", ["source_id"]),
            ("ix_learning_events_occurred_at", ["occurred_at"]),
        ),
    }
    for table, items in indexes.items():
        existing_indexes = {item["name"] for item in inspect(bind).get_indexes(table)}
        for name, columns in items:
            if name not in existing_indexes:
                op.create_index(name, table, columns)


def downgrade() -> None:
    bind = op.get_bind()
    for name in TASK_COLUMNS:
        if name in {
            column["name"] for column in inspect(bind).get_columns("learning_tasks")
        }:
            op.drop_column("learning_tasks", name)
    for table in reversed(NEW_TABLES):
        if table in inspect(bind).get_table_names():
            op.drop_table(table)
