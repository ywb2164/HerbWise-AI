"""Idempotently import an operator-supplied medicine class mapping CSV."""

from __future__ import annotations

import argparse
import asyncio
import csv
from pathlib import Path

from sqlalchemy import select

from app.core.database import async_session_factory
from app.modules.knowledge.models import MedicineAlias, MedicineItem
from app.modules.knowledge.normalizer import normalize_name

REQUIRED = {
    "training_class_name",
    "standard_name_zh",
    "standard_name_en",
    "aliases",
    "is_active",
}


async def import_csv(path: Path, dry_run: bool = False) -> dict[str, int]:
    counts = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not REQUIRED.issubset(set(rows[0])):
        raise ValueError(f"CSV must contain: {', '.join(sorted(REQUIRED))}")
    async with async_session_factory() as session:
        for row in rows:
            training = (row.get("training_class_name") or "").strip()
            standard = (row.get("standard_name_zh") or "").strip()
            if not training or not standard:
                counts["errors"] += 1
                continue
            item = await session.scalar(
                select(MedicineItem).where(MedicineItem.standard_name_zh == standard)
            )
            active = (row.get("is_active") or "true").strip().lower() in {
                "1",
                "true",
                "yes",
            }
            if item is None:
                counts["added"] += 1
                if dry_run:
                    continue
                item = MedicineItem(
                    medicine_code=f"import_{normalize_name(standard)[:48]}",
                    standard_name_zh=standard,
                    standard_name_en=(row.get("standard_name_en") or "").strip()
                    or None,
                    training_class_name=training,
                    is_active=active,
                )
                session.add(item)
                await session.flush()
            elif item.training_class_name in {None, "", training}:
                counts["updated"] += 1
                if not dry_run:
                    item.training_class_name, item.is_active = training, active
            else:
                counts["skipped"] += 1
                continue
            if not dry_run:
                for alias in filter(None, ((row.get("aliases") or "").split("|"))):
                    normalized = normalize_name(alias)
                    exists = await session.scalar(
                        select(MedicineAlias).where(
                            MedicineAlias.medicine_id == item.id,
                            MedicineAlias.normalized_name == normalized,
                        )
                    )
                    if not exists:
                        session.add(
                            MedicineAlias(
                                medicine_id=item.id,
                                alias_name=alias.strip(),
                                normalized_name=normalized,
                                alias_type="import",
                            )
                        )
        if not dry_run:
            await session.commit()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.csv_path.is_file():
        parser.error("CSV path does not exist")
    print(asyncio.run(import_csv(args.csv_path, args.dry_run)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
