"""Fail closed when forbidden runtime secrets or heavyweight artefacts are tracked."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_SUFFIXES = {".pt", ".pth", ".onnx"}
ALLOWED_ENV_FILES = {"admin-frontend/.env"}
TEXT_SUFFIXES = {
    ".cmd",
    ".css",
    ".env",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".ps1",
    ".py",
    ".scss",
    ".toml",
    ".ts",
    ".tsx",
    ".vue",
    ".yaml",
    ".yml",
}
FORBIDDEN_PARTS = {
    "__pycache__",
    ".venv",
    "data/uploads",
    "data/reports",
    "infra/ragflow/runtime",
}
SECRET = re.compile(
    r"(?i)(api[_-]?key|password|secret)\s*[=:]\s*['\"]?"
    r"(?!\$\{|your_|example|change-me-|development-only)"
    r"(?![A-Za-z_][A-Za-z0-9_]*\()[A-Za-z0-9_\-]{16,}"
)


def main() -> int:
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    issues: list[str] = []
    for name in tracked:
        path = Path(name)
        normalized = name.replace("\\", "/")
        allowed_model_metadata = normalized == "data/models/README.md" or (
            normalized.startswith("data/models/") and path.suffix.lower() == ".csv"
        )
        allowed_public_env = normalized in ALLOWED_ENV_FILES
        if (
            path.name == ".env"
            and not allowed_public_env
            or any(part in normalized for part in FORBIDDEN_PARTS)
            or normalized.startswith("data/models/")
            and not allowed_model_metadata
            or path.suffix.lower() in FORBIDDEN_SUFFIXES
        ):
            issues.append(f"forbidden tracked artefact: {name}")
            continue
        if (
            allowed_public_env
            or path.suffix.lower() in TEXT_SUFFIXES
            or path.name.startswith(".env.")
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
