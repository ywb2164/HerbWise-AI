"""add auth and business modules

Revision ID: 53e14d9e3d7c
Revises: 5f85f9852819

The initial migration remains untouched. This revision adds all V0.2 tables
and extends the pre-existing learner tables compatibly.
"""

from alembic import op
from sqlalchemy import Column, UniqueConstraint

import app.models  # noqa: F401
from app.core.database import Base

revision = "53e14d9e3d7c"
down_revision = "5f85f9852819"
branch_labels = None
depends_on = None

_EXISTING = {"learner_profiles", "learner_dimensions"}


def _copy_column(table_name: str, column_name: str) -> Column:
    return Base.metadata.tables[table_name].c[column_name].copy()


def upgrade() -> None:
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
        op.add_column("learner_profiles", _copy_column("learner_profiles", column_name))
    for column_name in ("dimension_code", "level", "evidence_json"):
        op.add_column(
            "learner_dimensions", _copy_column("learner_dimensions", column_name)
        )

    for table in Base.metadata.sorted_tables:
        if table.name in _EXISTING:
            continue
        columns = [column.copy() for column in table.columns]
        constraints = [
            constraint.copy()
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        ]
        op.create_table(table.name, *columns, *constraints)
        for index in table.indexes:
            op.create_index(
                index.name,
                table.name,
                [column.name for column in index.columns],
                unique=index.unique,
            )
    op.create_unique_constraint(
        "uq_learner_dimension_code",
        "learner_dimensions",
        ["learner_id", "dimension_code"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_learner_dimension_code", "learner_dimensions", type_="unique"
    )
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in _EXISTING:
            continue
        for index in table.indexes:
            op.drop_index(index.name, table_name=table.name)
        op.drop_table(table.name)
    for column_name in ("dimension_code", "level", "evidence_json"):
        op.drop_column("learner_dimensions", column_name)
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
        op.drop_column("learner_profiles", column_name)
