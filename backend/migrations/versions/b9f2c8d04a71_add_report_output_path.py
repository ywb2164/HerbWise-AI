"""add report output path

Revision ID: b9f2c8d04a71
Revises: e4d1b8f0c692
"""

from alembic import op
from sqlalchemy import inspect
import app.modules.learning_paths.models  # noqa: F401
from app.core.database import Base

revision = "b9f2c8d04a71"
down_revision = "e4d1b8f0c692"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    names = {row["name"] for row in inspect(bind).get_columns("report_records")}
    if "output_path" not in names:
        op.add_column(
            "report_records",
            Base.metadata.tables["report_records"].c.output_path._copy(),
        )


def downgrade() -> None:
    bind = op.get_bind()
    names = {row["name"] for row in inspect(bind).get_columns("report_records")}
    if "output_path" in names:
        op.drop_column("report_records", "output_path")
