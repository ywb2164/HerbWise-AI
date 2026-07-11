"""complete rag citation trace support

Revision ID: d8f7a3c209b1
Revises: c4b8e2d1a650
"""

from alembic import op
from sqlalchemy import inspect
import app.modules.knowledge.rag_models  # noqa: F401
import app.modules.resources.business_models  # noqa: F401
from app.core.database import Base

revision = "d8f7a3c209b1"
down_revision = "c4b8e2d1a650"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "knowledge_sync_records" not in inspector.get_table_names():
        op.create_table(
            "knowledge_sync_records",
            *[
                c._copy()
                for c in Base.metadata.tables["knowledge_sync_records"].columns
            ],
        )
    for table, columns in {
        "rag_evidence_records": ("rank", "retained_reason", "duplicate_of"),
        "rag_replay_records": ("medicine_id", "task_type"),
        "resource_outputs": (
            "retrieval_id",
            "evidence_ids_json",
            "citations_json",
            "data_source",
        ),
        "resource_reviews": (
            "retrieval_id",
            "citation_validity_score",
            "evidence_coverage_score",
            "citation_check_json",
            "evidence_ids_json",
            "data_source",
        ),
    }.items():
        existing = {c["name"] for c in inspect(bind).get_columns(table)}
        for name in columns:
            if name not in existing:
                op.add_column(table, Base.metadata.tables[table].c[name]._copy())


def downgrade() -> None:
    bind = op.get_bind()
    for table, columns in {
        "resource_reviews": (
            "data_source",
            "evidence_ids_json",
            "citation_check_json",
            "evidence_coverage_score",
            "citation_validity_score",
            "retrieval_id",
        ),
        "resource_outputs": (
            "data_source",
            "citations_json",
            "evidence_ids_json",
            "retrieval_id",
        ),
        "rag_replay_records": ("task_type", "medicine_id"),
        "rag_evidence_records": ("duplicate_of", "retained_reason", "rank"),
    }.items():
        existing = {c["name"] for c in inspect(bind).get_columns(table)}
        for name in columns:
            if name in existing:
                op.drop_column(table, name)
    if "knowledge_sync_records" in inspect(bind).get_table_names():
        op.drop_table("knowledge_sync_records")
