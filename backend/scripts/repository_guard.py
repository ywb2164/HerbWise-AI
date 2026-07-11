"""Fail closed when forbidden runtime secrets or heavyweight artefacts are tracked."""

from __future__ import annotations
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_SUFFIXES = {".pt", ".pth", ".onnx"}
FORBIDDEN_PARTS = {
    "__pycache__",
    ".venv",
    "data/uploads",
    "data/reports",
    "data/models",
    "infra/ragflow/runtime",
}
SECRET = re.compile(
    r"(?i)(api[_-]?key|password|secret)\s*[=:]\s*['\"]?(?!\$\{|your_|example|development-only)[A-Za-z0-9_\-]{16,}"
)


def main() -> int:
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    issues: list[str] = []
    for name in tracked:
        path = Path(name)
        normalized = name.replace("\\", "/")
        if (
            path.name == ".env"
            or any(part in normalized for part in FORBIDDEN_PARTS)
            or path.suffix.lower() in FORBIDDEN_SUFFIXES
        ):
            issues.append(f"forbidden tracked artefact: {name}")
            continue
        if (
            path.suffix.lower()
            in {".py", ".ps1", ".yml", ".yaml", ".json", ".md", ".env"}
            and path.is_file()
            and path.name != ".env.example"
        ):
            if SECRET.search(
                (ROOT / path).read_text(encoding="utf-8", errors="ignore")
            ):
                issues.append(f"possible plaintext secret: {name}")
    if issues:
        print("Repository guard failed:\n" + "\n".join(issues))
        return 1
    print(
        "Repository guard passed: no forbidden tracked secrets, weights, uploads, reports, or volumes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
