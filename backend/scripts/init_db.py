"""Apply Alembic migrations; use this instead of manual table creation."""

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

sys.path.append(str(Path(__file__).resolve().parents[1]))


if __name__ == "__main__":
    command.upgrade(Config("alembic.ini"), "head")
