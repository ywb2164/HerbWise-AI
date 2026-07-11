"""add real ai integration records

Revision ID: 7a3e91b4c2f0
Revises: 53e14d9e3d7c
"""

from alembic import op
from sqlalchemy import UniqueConstraint, inspect

import app.models  # noqa: F401
import app.modules.recognition.models  # noqa: F401
from app.core.database import Base

revision = "7a3e91b4c2f0"
down_revision = "53e14d9e3d7c"
branch_labels = None
depends_on = None

_TABLES = ("model_call_records", "recognition_records")


def _tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()
    for name in _TABLES:
        if name in existing:
            continue
        table = Base.metadata.tables[name]
        constraints = [
            UniqueConstraint(
                *[column.name for column in constraint.columns], name=constraint.name
            )
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        ]
        op.create_table(
            name, *[column._copy() for column in table.columns], *constraints
        )


def downgrade() -> None:
    existing = _tables()
    for name in reversed(_TABLES):
        if name in existing:
            op.drop_table(name)
