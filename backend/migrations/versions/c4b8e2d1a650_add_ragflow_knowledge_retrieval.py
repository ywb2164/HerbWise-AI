"""add ragflow knowledge retrieval

Revision ID: c4b8e2d1a650
Revises: 9c2d7e5b104a
"""

from alembic import op
from sqlalchemy import inspect

import app.modules.knowledge.models  # noqa: F401
import app.modules.knowledge.rag_models  # noqa: F401
from app.core.database import Base

revision = "c4b8e2d1a650"
down_revision = "9c2d7e5b104a"
branch_labels = None
depends_on = None

_TABLES = (
    "knowledge_datasets",
    "knowledge_documents",
    "rag_retrieval_records",
    "rag_evidence_records",
    "rag_replay_records",
)


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    for name in _TABLES:
        if name not in existing:
            op.create_table(
                name, *[column._copy() for column in Base.metadata.tables[name].columns]
            )


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    for name in reversed(_TABLES):
        if name in existing:
            op.drop_table(name)
