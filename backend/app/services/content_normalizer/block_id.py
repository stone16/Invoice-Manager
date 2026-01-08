from __future__ import annotations

import re
from typing import Iterable, List

from app.services.content_normalizer.models import BoundingBox

_PDF_BLOCK_ID_PATTERN = re.compile(r"^\d+\.\d+\.\d+:\d+:\d+$")
_EXCEL_BLOCK_ID_PATTERN = re.compile(r"^\d+\.\d+\.[A-Z]+\d+$")
_MERGED_BLOCK_ID_PATTERN = re.compile(r"^\d+\.\d+\.[A-Z]+\d+:[A-Z]+\d+$")


def build_pdf_block_id(doc_index: int, page_index: int, row: int, col: int, idx: int) -> str:
    """Build a PDF block ID for a specific row/column/idx."""
    return f"{doc_index}.{page_index}.{row}:{col}:{idx}"


def build_excel_block_id(doc_index: int, sheet_index: int, cell_ref: str) -> str:
    """Build an Excel block ID for a single cell reference."""
    return f"{doc_index}.{sheet_index}.{cell_ref}"


def build_merged_cell_block_id(doc_index: int, sheet_index: int, start: str, end: str) -> str:
    """Build an Excel block ID for a merged cell range."""
    return f"{doc_index}.{sheet_index}.{start}:{end}"


def is_valid_pdf_block_id(block_id: str) -> bool:
    """Return True if a PDF block ID matches the expected pattern."""
    return bool(_PDF_BLOCK_ID_PATTERN.match(block_id))


def is_valid_excel_block_id(block_id: str) -> bool:
    """Return True if an Excel block ID matches the single-cell pattern."""
    return bool(_EXCEL_BLOCK_ID_PATTERN.match(block_id))


def is_valid_merged_cell_block_id(block_id: str) -> bool:
    """Return True if an Excel block ID matches the merged cell pattern."""
    return bool(_MERGED_BLOCK_ID_PATTERN.match(block_id))


def assign_pdf_block_ids(
    doc_index: int,
    page_index: int,
    bboxes: Iterable[BoundingBox],
) -> List[BoundingBox]:
    """Assign PDF block IDs to bounding boxes and return updated copies."""
    updated: List[BoundingBox] = []
    for bbox in bboxes:
        if bbox.row is None or bbox.col is None or bbox.idx is None:
            raise ValueError("BoundingBox missing row/col/idx for block ID assignment")
        updated.append(
            bbox.model_copy(
                update={
                    "id": build_pdf_block_id(doc_index, page_index, bbox.row, bbox.col, bbox.idx)
                }
            )
        )
    return updated
