"""DANGER: this script intentionally requires explicit confirmation and is never automatic."""

import argparse
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

sys.path.append(str(Path(__file__).resolve().parents[1]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="DANGER: deletes all HerbWise database tables."
    )
    parser.add_argument(
        "--confirm-reset",
        action="store_true",
        help="Required acknowledgement for destructive reset",
    )
    args = parser.parse_args()
    if not args.confirm_reset:
        parser.error(
            "Refusing to reset. Re-run only if intentional with --confirm-reset."
        )
    config = Config("alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
