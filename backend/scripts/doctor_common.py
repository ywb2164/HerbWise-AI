"""Small, redacted diagnostics primitives shared by V0.4 command-line tools."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(slots=True)
class Check:
    name: str
    status: str
    detail: str


def output(checks: list[Check], as_json: bool) -> int:
    """Print only safe diagnostic data and return a conventional exit code."""
    if as_json:
        print(
            json.dumps([asdict(item) for item in checks], ensure_ascii=False, indent=2)
        )
    else:
        for item in checks:
            print(f"{item.status.upper():7} {item.name}: {item.detail}")
    return 1 if any(item.status == "fail" for item in checks) else 0


def configured(value: str) -> bool:
    return bool(value.strip())


def writable(path: Path) -> tuple[bool, str]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".herbwise-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True, "writable"
    except OSError:
        return False, "not writable; create it or correct the configured directory"


def safe_exception(exc: Exception) -> str:
    """Avoid reflecting URLs with query parameters or accidental credentials."""
    message = str(exc).replace("Bearer ", "Bearer [redacted]")
    return message.split("?", 1)[0][:200]
