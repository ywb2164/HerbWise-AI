"""add resource-generation jobs and auditable resource fields

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "a4b5c6d7e8f9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def _add_missing_columns(table: str, columns: dict[str, sa.Column]) -> None:
    existing = {item["name"] for item in inspect(op.get_bind()).get_columns(table)}
    for name, column in columns.items():
        if name not in existing:
            op.add_column(table, column)


def _create_index_if_missing(table: str, name: str, columns: list[str]) -> None:
    existing = {item["name"] for item in inspect(op.get_bind()).get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, columns)


def upgrade() -> None:
    _add_missing_columns(
        "resource_outputs",
        {
            "plan_id": sa.Column("plan_id", sa.String(length=64), nullable=True),
            "plan_item_id": sa.Column(
                "plan_item_id", sa.String(length=64), nullable=True
            ),
            "learning_objectives_json": sa.Column(
                "learning_objectives_json", sa.JSON(), nullable=True
            ),
            "target_dimensions_json": sa.Column(
                "target_dimensions_json", sa.JSON(), nullable=True
            ),
            "target_knowledge_points_json": sa.Column(
                "target_knowledge_points_json", sa.JSON(), nullable=True
            ),
            "estimated_minutes": sa.Column(
                "estimated_minutes", sa.Integer(), nullable=True
            ),
            "personalization_reason": sa.Column(
                "personalization_reason", sa.Text(), nullable=True
            ),
            "task_snapshot_json": sa.Column(
                "task_snapshot_json", sa.JSON(), nullable=True
            ),
            "knowledge_snapshot_json": sa.Column(
                "knowledge_snapshot_json", sa.JSON(), nullable=True
            ),
            "citation_count": sa.Column(
                "citation_count", sa.Integer(), nullable=False, server_default="0"
            ),
            "review_status": sa.Column(
                "review_status", sa.String(length=32), nullable=True
            ),
            "review_score": sa.Column("review_score", sa.Float(), nullable=True),
            "rewrite_count": sa.Column(
                "rewrite_count", sa.Integer(), nullable=False, server_default="0"
            ),
            "version": sa.Column(
                "version", sa.Integer(), nullable=False, server_default="1"
            ),
            "parent_resource_id": sa.Column(
                "parent_resource_id", sa.String(length=64), nullable=True
            ),
            "fallback_used": sa.Column(
                "fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        },
    )
    for name, columns in {
        "ix_resource_outputs_plan_id": ["plan_id"],
        "ix_resource_outputs_plan_item_id": ["plan_item_id"],
        "ix_resource_outputs_parent_resource_id": ["parent_resource_id"],
    }.items():
        _create_index_if_missing("resource_outputs", name, columns)

    op.create_table(
        "resource_generation_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("learner_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=True),
        sa.Column("plan_item_id", sa.String(length=64), nullable=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=False),
        sa.Column("additional_instruction", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="pending"
        ),
        sa.Column(
            "requires_rag", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("rag_reason_json", sa.JSON(), nullable=True),
        sa.Column("retrieval_id", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("job_id"),
    )
    for name, columns in {
        "ix_resource_generation_jobs_job_id": ["job_id"],
        "ix_resource_generation_jobs_learner_id": ["learner_id"],
        "ix_resource_generation_jobs_plan_id": ["plan_id"],
        "ix_resource_generation_jobs_plan_item_id": ["plan_item_id"],
        "ix_resource_generation_jobs_task_id": ["task_id"],
        "ix_resource_generation_jobs_resource_type": ["resource_type"],
        "ix_resource_generation_jobs_status": ["status"],
        "ix_resource_generation_jobs_retrieval_id": ["retrieval_id"],
        "ix_resource_generation_jobs_resource_id": ["resource_id"],
    }.items():
        op.create_index(name, "resource_generation_jobs", columns)


def downgrade() -> None:
    op.drop_table("resource_generation_jobs")
    for name in (
        "fallback_used",
        "parent_resource_id",
        "version",
        "rewrite_count",
        "review_score",
        "review_status",
        "citation_count",
        "knowledge_snapshot_json",
        "task_snapshot_json",
        "personalization_reason",
        "estimated_minutes",
        "target_knowledge_points_json",
        "target_dimensions_json",
        "learning_objectives_json",
        "plan_item_id",
        "plan_id",
    ):
        op.drop_column("resource_outputs", name)
