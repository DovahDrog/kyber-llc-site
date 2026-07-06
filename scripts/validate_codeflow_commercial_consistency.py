#!/usr/bin/env python3
"""Validate CodeFlow public commercial positioning consistency.

This catches the exact failure Alex found: live/static buyer surfaces must show the
Operations+ $12k/mo positioning, private/staff-demo routes must exist, and older
starter-portal pricing language must not remain on buyer-facing pages.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    ROOT / "codeflow" / "index.html",
    ROOT / "codeflow" / "demo" / "index.html",
    ROOT / "codeflow" / "private" / "index.html",
    ROOT / "codeflow" / "staff-demo" / "index.html",
]
REQUIRED_PHRASES = [
    "CodeFlow Municipal Operations+",
    "$12,000/mo",
    "$20,000 setup",
    "mobile field workflow",
    "City Pack source maintenance/versioning",
    "packet PDF export",
    "management dashboard",
    "public-records/export readiness",
    "role-based review gates",
    "city system-stack mapping",
    "quarterly source/workflow reviews",
    "staff-final-review-only",
]
FORBIDDEN_PATTERNS = [
    r"\$2,000\s*/?\s*month",
    r"\$2,000/mo",
    r"Starter Portal",
    r"Department Portal",
    r"City Pack Buildout:\s*\$7,500-\$25,000",
    r"Subscription:\s*\$2,000/month",
]


def text(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing required route file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    pages = {}
    for path in REQUIRED_FILES:
        try:
            pages[path] = text(path)
        except AssertionError as exc:
            failures.append(str(exc))
    combined = "\n".join(pages.values())
    for phrase in REQUIRED_PHRASES:
        if phrase not in combined:
            failures.append(f"missing required phrase: {phrase}")
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, combined, flags=re.I):
            failures.append(f"forbidden old pricing language still present: {pattern}")
    if failures:
        print("CodeFlow commercial consistency validation FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("CodeFlow commercial consistency validation passed")
    for path in REQUIRED_FILES:
        print(f"- {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
