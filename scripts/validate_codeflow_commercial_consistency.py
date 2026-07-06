#!/usr/bin/env python3
"""Validate CodeFlow public commercial positioning consistency.

This catches the exact failure Alex found: live/static buyer surfaces must show the
Operations+ $12k/mo positioning, private/staff-demo routes must exist, the public
pricing PDF must match the same commercial story, and older starter-portal pricing
language must not remain on buyer-facing assets.
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
PDF_FILE = ROOT / "codeflow" / "assets" / "codeflow-sales-model-pricing-explanation.pdf"
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
PDF_REQUIRED_PHRASES = [
    "CodeFlow Municipal Operations+",
    "$20,000",
    "$10,000/mo",
    "$12,000/mo",
    "staff-final-review-only",
    "City Pack source maintenance/versioning",
    "mobile field workflow",
    "packet PDF export",
    "management dashboard",
    "public-records/export readiness",
    "role-based review gates",
    "city system-stack mapping",
    "quarterly source/workflow reviews",
]
FORBIDDEN_PATTERNS = [
    r"\$2,000\s*/?\s*month",
    r"\$2,000/mo",
    r"Starter Portal",
    r"Department Portal",
    r"City Pack Buildout:\s*\$7,500-\$25,000",
    r"Subscription:\s*\$2,000/month",
]


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def text(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing required route file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def pdf_text(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing required PDF asset: {path.relative_to(ROOT)}")
    try:
        import fitz  # PyMuPDF
    except Exception as exc:  # pragma: no cover - local validation dependency
        raise AssertionError(f"cannot validate PDF text; PyMuPDF import failed: {exc}") from exc
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)


def phrase_present(phrase: str, haystack: str) -> bool:
    return normalize(phrase) in normalize(haystack)


def main() -> int:
    failures: list[str] = []
    pages: dict[Path, str] = {}
    for path in REQUIRED_FILES:
        try:
            pages[path] = text(path)
        except AssertionError as exc:
            failures.append(str(exc))
    combined = "\n".join(pages.values())
    for phrase in REQUIRED_PHRASES:
        if phrase not in combined:
            failures.append(f"missing required phrase on HTML surfaces: {phrase}")
    try:
        pdf_combined = pdf_text(PDF_FILE)
    except AssertionError as exc:
        failures.append(str(exc))
        pdf_combined = ""
    for phrase in PDF_REQUIRED_PHRASES:
        if not phrase_present(phrase, pdf_combined):
            failures.append(f"missing required phrase in pricing PDF: {phrase}")
    all_buyer_text = combined + "\n" + pdf_combined
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, all_buyer_text, flags=re.I):
            failures.append(f"forbidden old pricing language still present: {pattern}")
    if failures:
        print("CodeFlow commercial consistency validation FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("CodeFlow commercial consistency validation passed")
    for path in REQUIRED_FILES:
        print(f"- {path.relative_to(ROOT)}")
    print(f"- {PDF_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
