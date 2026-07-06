#!/usr/bin/env python3
"""Validate CodeFlow public commercial and MGO-safe positioning consistency.

This catches the failures Alex flagged:
- buyer surfaces must show Operations+ pricing;
- private/staff-demo/proposal/intake surfaces must exist and speak the same language;
- buyer PDFs must match the same commercial story;
- MGO-safe system-of-record / manual-export posture must be visible;
- older starter-portal pricing language must not remain on buyer-facing assets.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
HTML_REQUIRED_FILES = [
    ROOT / "codeflow" / "index.html",
    ROOT / "codeflow" / "demo" / "index.html",
    ROOT / "codeflow" / "private" / "index.html",
    ROOT / "codeflow" / "staff-demo" / "index.html",
    ROOT / "codeflow" / "proposal" / "index.html",
    ROOT / "codeflow" / "intake" / "index.html",
    ROOT / "codeflow" / "proof" / "index.html",
    ROOT / "codeflow" / "system-stack" / "index.html",
]
PRICING_PDF = ROOT / "codeflow" / "assets" / "codeflow-sales-model-pricing-explanation.pdf"
MGO_BUYER_PDF = ROOT / "codeflow" / "assets" / "codeflow-mgo-beside-system-buyer-sheet.pdf"

OPERATIONS_REQUIRED_PHRASES = [
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
PRICING_PDF_REQUIRED_PHRASES = [
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
MGO_REQUIRED_PHRASES = [
    "System-of-record boundary",
    "Already using MGO",
    "does not replace MGO",
    "workflow-discipline layer",
    "source separation",
    "conflict handling",
    "review gates",
    "records readiness",
    "review-ready packet prep",
    "Manual export first",
    "Integration only when verified",
    "AI suggests and assembles; staff verifies and approves",
]
MGO_BUYER_PDF_REQUIRED_PHRASES = [
    "If you already use MGO",
    "does not replace MGO",
    "workflow-discipline layer",
    "system of record",
    "Manual export",
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


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def read_text(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def pdf_text(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing required PDF asset: {path.relative_to(ROOT)}")
    try:
        import fitz  # type: ignore
        doc = fitz.open(path)
        return "\n".join(page.get_text() for page in doc)
    except ModuleNotFoundError:
        pass
    try:
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise AssertionError(f"cannot validate PDF text for {path.relative_to(ROOT)}: {exc}") from exc


def phrase_present(phrase: str, haystack: str) -> bool:
    return normalize(phrase) in normalize(haystack)


def main() -> int:
    failures: list[str] = []
    pages: dict[Path, str] = {}
    for path in HTML_REQUIRED_FILES:
        try:
            pages[path] = read_text(path)
        except AssertionError as exc:
            failures.append(str(exc))
    combined = "\n".join(pages.values())

    for phrase in OPERATIONS_REQUIRED_PHRASES:
        if not phrase_present(phrase, combined):
            failures.append(f"missing Operations+ phrase on HTML surfaces: {phrase}")

    # The MGO-safe boundary must be present on every outward HTML surface, not only one page.
    for path, page in pages.items():
        for phrase in MGO_REQUIRED_PHRASES:
            if not phrase_present(phrase, page):
                failures.append(f"{path.relative_to(ROOT)} missing MGO-safe phrase: {phrase}")

    try:
        pricing_pdf = pdf_text(PRICING_PDF)
    except AssertionError as exc:
        failures.append(str(exc))
        pricing_pdf = ""
    for phrase in PRICING_PDF_REQUIRED_PHRASES:
        if not phrase_present(phrase, pricing_pdf):
            failures.append(f"missing required phrase in pricing PDF: {phrase}")

    try:
        mgo_pdf = pdf_text(MGO_BUYER_PDF)
    except AssertionError as exc:
        failures.append(str(exc))
        mgo_pdf = ""
    for phrase in MGO_BUYER_PDF_REQUIRED_PHRASES:
        if not phrase_present(phrase, mgo_pdf):
            failures.append(f"missing required phrase in MGO buyer PDF: {phrase}")

    all_buyer_text = combined + "\n" + pricing_pdf + "\n" + mgo_pdf
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, all_buyer_text, flags=re.I):
            failures.append(f"forbidden old pricing language still present: {pattern}")

    if failures:
        print("CodeFlow commercial/MGO-safe consistency validation FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("CodeFlow commercial/MGO-safe consistency validation passed")
    for path in HTML_REQUIRED_FILES:
        print(f"- {path.relative_to(ROOT)}")
    print(f"- {PRICING_PDF.relative_to(ROOT)}")
    print(f"- {MGO_BUYER_PDF.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
