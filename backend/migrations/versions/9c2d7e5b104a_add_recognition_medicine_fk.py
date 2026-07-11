"""add recognition medicine foreign key

Revision ID: 9c2d7e5b104a
Revises: 7a3e91b4c2f0
"""

from alembic import op
from sqlalchemy import inspect

revision = "9c2d7e5b104a"
down_revision = "7a3e91b4c2f0"
branch_labels = None
depends_on = None

_NAME = "fk_recognition_records_final_medicine_id"


def _foreign_keys() -> set[str]:
    return {
        item["name"]
        for item in inspect(op.get_bind()).get_foreign_keys("recognition_records")
        if item.get("name")
    }


def upgrade() -> None:
    if _NAME not in _foreign_keys():
        op.create_foreign_key(
            _NAME,
            "recognition_records",
            "medicine_items",
            ["final_medicine_id"],
            ["id"],
        )


def downgrade() -> None:
    if _NAME in _foreign_keys():
        op.drop_constraint(_NAME, "recognition_records", type_="foreignkey")
