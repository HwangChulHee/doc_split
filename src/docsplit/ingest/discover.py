"""Work out what the input files are, from whatever the user dropped in data/.

The reviewer copies the PDFs they were given straight into ``data/`` under their
original names. Nothing enforces a directory layout, so roles are inferred:

  * a name containing "shuffled" is a package to classify
  * anything else is a candidate answer key, typed by a keyword in its name
  * a name with no recognizable keyword is reported and skipped, not guessed

Recognition is printed before the run so the user can see what was understood.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .pdf_parser import slugify

PACKAGE_MARKER = "shuffled"
LABEL_RE = re.compile(r"^(\d+)\b")

# Filename keyword -> document type. Order matters: the first hit wins, so the
# more specific spellings come first.
TYPE_KEYWORDS: list[tuple[str, str]] = [
    ("1003", "URLA_1003"),
    ("urla", "URLA_1003"),
    ("loan application", "URLA_1003"),
    ("credit", "CREDIT_REPORT"),
    ("title", "TITLE_REPORT"),
    ("commitment", "TITLE_REPORT"),
    ("prelim", "TITLE_REPORT"),
    ("income", "INCOME_DOC"),
    ("p & l", "INCOME_DOC"),
    ("p&l", "INCOME_DOC"),
    ("profit", "INCOME_DOC"),
    ("transcript", "INCOME_DOC"),
    ("w-2", "INCOME_DOC"),
    ("w2", "INCOME_DOC"),
    ("1040", "INCOME_DOC"),
    ("paystub", "INCOME_DOC"),
    ("paycheck", "INCOME_DOC"),
]


@dataclass
class InputFile:
    path: Path
    role: str  # "package" | "answer_key" | "unrecognized"
    label: str | None = None  # package label, e.g. "01"
    doc_type: str | None = None  # answer keys only
    slug: str = ""

    def __post_init__(self) -> None:
        self.slug = self.slug or slugify(self.path.name)


@dataclass
class Discovery:
    packages: list[InputFile] = field(default_factory=list)
    answer_keys: list[InputFile] = field(default_factory=list)
    unrecognized: list[InputFile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def all_files(self) -> list[InputFile]:
        return self.packages + self.answer_keys + self.unrecognized

    def render_table(self) -> str:
        rows = ["  파일                                               인식", "  " + "-" * 66]
        for f in self.packages:
            rows.append(f"  {f.path.name[:48]:<48} 분류 대상 패키지 (라벨 {f.label})")
        for f in self.answer_keys:
            rows.append(f"  {f.path.name[:48]:<48} 정답 원본 → {f.doc_type}")
        for f in self.unrecognized:
            rows.append(f"  {f.path.name[:48]:<48} ⚠️ 유형 불명 — 검증에서 제외")
        return "\n".join(rows)


def _doc_type_from_name(name: str) -> str | None:
    lowered = name.lower()
    for keyword, doc_type in TYPE_KEYWORDS:
        if keyword in lowered:
            return doc_type
    return None


def _label_from_name(name: str, fallback_index: int) -> str:
    m = LABEL_RE.match(name)
    if m:
        return m.group(1).zfill(2)
    return f"{fallback_index:02d}"


def discover_inputs(data_dir: Path) -> Discovery:
    """Scan data_dir for task PDFs and assign each a role.

    ``reference/`` is skipped: those are public blank forms kept for the
    standards comparison, not documents to classify.
    """
    if not data_dir.exists():
        raise SystemExit(f"{data_dir} 디렉터리가 없습니다. 받은 PDF를 이 안에 넣어주세요.")

    pdfs = sorted(p for p in data_dir.rglob("*.pdf") if "reference" not in p.parts)
    out = Discovery()
    if not pdfs:
        raise SystemExit(
            f"{data_dir} 에 PDF가 하나도 없습니다.\n"
            f"  받은 PDF 파일들을 {data_dir}/ 안에 그대로 복사한 뒤 다시 실행하세요."
        )

    package_index = 0
    for pdf in pdfs:
        if PACKAGE_MARKER in pdf.name.lower():
            package_index += 1
            out.packages.append(
                InputFile(pdf, "package", label=_label_from_name(pdf.name, package_index))
            )
            continue
        doc_type = _doc_type_from_name(pdf.name)
        if doc_type:
            out.answer_keys.append(InputFile(pdf, "answer_key", doc_type=doc_type))
        else:
            out.unrecognized.append(InputFile(pdf, "unrecognized"))
            out.warnings.append(
                f"'{pdf.name}' 은 파일명으로 문서 유형을 알 수 없어 정답 대조에서 제외합니다 "
                "(분류 실행에는 영향 없음)."
            )

    if not out.packages:
        raise SystemExit(
            f"{data_dir} 에 분류 대상 PDF가 없습니다.\n"
            f"  분류할 패키지 파일명에는 '{PACKAGE_MARKER}' 가 들어 있어야 합니다. "
            f"찾은 PDF: {', '.join(p.name for p in pdfs[:5])}"
        )

    labels = [f.label for f in out.packages]
    if len(set(labels)) != len(labels):
        for i, f in enumerate(out.packages, start=1):
            f.label = f"{i:02d}"
        out.warnings.append("패키지 라벨이 중복되어 파일 순서대로 다시 매겼습니다.")
    return out
