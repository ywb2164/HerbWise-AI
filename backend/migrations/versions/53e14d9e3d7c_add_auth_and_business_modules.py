"""add auth and business modules

Revision ID: 53e14d9e3d7c
Revises: 5f85f9852819

The initial migration remains untouched. This revision adds all V0.2 tables
and extends the pre-existing learner tables compatibly.
"""

from alembic import op
from sqlalchemy import Column, UniqueConstraint, inspect

import app.models  # noqa: F401
from app.core.database import Base

revision = "53e14d9e3d7c"
down_revision = "5f85f9852819"
branch_labels = None
depends_on = None

_INITIAL_TABLES = {
    "agent_logs",
    "learner_dimensions",
    "learner_profiles",
    "task_events",
    "task_records",
    "trace_records",
    "uploaded_files",
}


def _copy_column(table_name: str, column_name: str) -> Column:
    return Base.metadata.tables[table_name].c[column_name]._copy()


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def _unique_names(table_name: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in inspect(op.get_bind()).get_unique_constraints(table_name)
        if constraint.get("name")
    }


def upgrade() -> None:
    profile_columns = _column_names("learner_profiles")
    for column_name in (
        "user_id",
        "name",
        "identity_type",
        "education_background",
        "professional_background",
        "learning_goal",
        "learning_preference",
        "overall_level",
        "diagnosis_summary",
    ):
        if column_name not in profile_columns:
            op.add_column(
                "learner_profiles", _copy_column("learner_profiles", column_name)
            )
    dimension_columns = _column_names("learner_dimensions")
    for column_name in ("dimension_code", "level", "evidence_json"):
        if column_name not in dimension_columns:
            op.add_column(
                "learner_dimensions", _copy_column("learner_dimensions", column_name)
            )

    table_names = _table_names()
    for table in Base.metadata.sorted_tables:
        if table.name in table_names:
            continue
        columns = [column._copy() for column in table.columns]
        constraints = [
            UniqueConstraint(
                *[column.name for column in constraint.columns],
                name=constraint.name,
            )
            for constraint in list(table.constraints)
            if isinstance(constraint, UniqueConstraint)
        ]
        op.create_table(table.name, *columns, *constraints)
        table_names.add(table.name)
    if "uq_learner_dimension_code" not in _unique_names("learner_dimensions"):
        op.create_unique_constraint(
            "uq_learner_dimension_code",
            "learner_dimensions",
            ["learner_id", "dimension_code"],
        )


def downgrade() -> None:
    if "uq_learner_dimension_code" in _unique_names("learner_dimensions"):
        op.drop_constraint(
            "uq_learner_dimension_code", "learner_dimensions", type_="unique"
        )
    table_names = _table_names()
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in _INITIAL_TABLES or table.name not in table_names:
            continue
        op.drop_table(table.name)
    dimension_columns = _column_names("learner_dimensions")
    for column_name in ("dimension_code", "level", "evidence_json"):
        if column_name in dimension_columns:
            op.drop_column("learner_dimensions", column_name)
    profile_columns = _column_names("learner_profiles")
    for column_name in (
        "user_id",
        "name",
        "identity_type",
        "education_background",
        "professional_background",
        "learning_goal",
        "learning_preference",
        "overall_level",
        "diagnosis_summary",
    ):
        if column_name in profile_columns:
            op.drop_column("learner_profiles", column_name)
