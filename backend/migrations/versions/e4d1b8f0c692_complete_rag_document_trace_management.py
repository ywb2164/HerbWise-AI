"""complete rag document trace management

Revision ID: e4d1b8f0c692
Revises: d8f7a3c209b1
"""

from alembic import op
from sqlalchemy import inspect
import app.modules.knowledge.rag_models  # noqa: F401
from app.core.database import Base

revision = "e4d1b8f0c692"
down_revision = "d8f7a3c209b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table, names in {
        "knowledge_documents": ("raw_status", "last_error", "last_checked_at"),
        "rag_retrieval_records": (
            "query_version",
            "structured_count",
            "rag_count",
            "retained_count",
            "insufficient_evidence",
        ),
    }.items():
        existing = {row["name"] for row in inspect(bind).get_columns(table)}
        for name in names:
            if name not in existing:
                op.add_column(table, Base.metadata.tables[table].c[name]._copy())


def downgrade() -> None:
    bind = op.get_bind()
    for table, names in {
        "rag_retrieval_records": (
            "insufficient_evidence",
            "retained_count",
            "rag_count",
            "structured_count",
            "query_version",
        ),
        "knowledge_documents": ("last_checked_at", "last_error", "raw_status"),
    }.items():
        existing = {row["name"] for row in inspect(bind).get_columns(table)}
        for name in names:
            if name in existing:
                op.drop_column(table, name)
