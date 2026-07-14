"""Read-only loader for the optional curated 45-class knowledge package."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def normalize_catalog_name(value: str) -> str:
    """Normalize only for exact-equivalence matching, never fuzzy matching."""

    return re.sub(r"[\s\-_/(),.，。（）]+", "", value).casefold()


@dataclass(frozen=True)
class CatalogMatch:
    status: str
    original_name: str
    profile: dict[str, Any] | None = None

    @property
    def standard_name_en(self) -> str:
        if self.profile is None:
            return self.original_name
        return str(self.profile.get("standard_name_en") or self.original_name)


class KnowledgeCatalog:
    """Loads authoritative package records when the user supplies the package."""

    _path: Path | None = None
    _index: dict[str, dict[str, Any]] = {}

    @classmethod
    def _records(cls, content: object) -> list[dict[str, Any]]:
        if isinstance(content, list):
            return [item for item in content if isinstance(item, dict)]
        if isinstance(content, dict):
            for key in ("records", "profiles", "items", "data", "herbs"):
                value = content.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    @classmethod
    def _load(cls) -> None:
        path = get_settings().resolved_knowledge_catalog_path()
        if cls._path == path:
            return
        cls._path, cls._index = path, {}
        if not path.is_file():
            return
        try:
            records = cls._records(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            return
        for profile in records:
            # Exact matching only.  Preserve this order to make the catalog's
            # standard Chinese name authoritative whenever aliases overlap.
            names: list[object] = [
                profile.get("standard_name_zh"),
                *list(profile.get("aliases") or []),
                profile.get("training_class_name"),
                profile.get("standard_name_en"),
                profile.get("pharmacopoeial_latin_name"),
            ]
            for name in names:
                if isinstance(name, str) and name.strip():
                    cls._index.setdefault(normalize_catalog_name(name), profile)

    @classmethod
    def status(cls) -> dict[str, object]:
        cls._load()
        return {
            "loaded": bool(cls._index),
            "path": str(cls._path) if cls._path else None,
            "record_count": len({id(value) for value in cls._index.values()}),
        }

    @classmethod
    def match(cls, *, name_zh: str | None, name_en: str | None) -> CatalogMatch:
        cls._load()
        original_name = name_zh or name_en or ""
        profile = None
        for name in (name_zh, name_en):
            if name and name.strip():
                profile = cls._index.get(normalize_catalog_name(name))
                if profile is not None:
                    break
        return CatalogMatch(
            status="matched" if profile else "out_of_catalog",
            original_name=original_name,
            profile=profile,
        )
