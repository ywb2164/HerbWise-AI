"""add personalised learning plans

Revision ID: f3a4b5c6d7e8
Revises: f2a3b4c5d6e7
"""

from alembic import op
import sqlalchemy as sa

revision = "f3a4b5c6d7e8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.String(64), nullable=False),
        sa.Column("learner_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("stage", sa.String(128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("daily_minutes", sa.Integer(), nullable=False),
        sa.Column("total_estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("profile_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("weak_points_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("recent_performance_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(128)),
        sa.Column("provider", sa.String(64)),
        sa.Column("prompt_version", sa.String(64)),
        sa.Column("data_source", sa.String(64), nullable=False, server_default="llm"),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("plan_id"),
    )
    op.create_index("ix_learning_plans_plan_id", "learning_plans", ["plan_id"])
    op.create_index("ix_learning_plans_learner_id", "learning_plans", ["learner_id"])
    op.create_index("ix_learning_plans_status", "learning_plans", ["status"])
    op.create_table(
        "learning_plan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.String(64), nullable=False),
        sa.Column("plan_id", sa.String(64), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("target_dimensions_json", sa.JSON(), nullable=False),
        sa.Column("target_knowledge_points_json", sa.JSON(), nullable=False),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("difficulty", sa.String(32), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("linked_task_id", sa.String(64)),
        sa.Column("linked_resource_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("item_id"),
        sa.UniqueConstraint("plan_id", "order_index", name="uq_learning_plan_item_order"),
    )
    op.create_index("ix_learning_plan_items_item_id", "learning_plan_items", ["item_id"])
    op.create_index("ix_learning_plan_items_plan_id", "learning_plan_items", ["plan_id"])
    op.create_index("ix_learning_plan_items_linked_task_id", "learning_plan_items", ["linked_task_id"])
    op.create_index("ix_learning_plan_items_linked_resource_id", "learning_plan_items", ["linked_resource_id"])


def downgrade() -> None:
    op.drop_table("learning_plan_items")
    op.drop_table("learning_plans")
