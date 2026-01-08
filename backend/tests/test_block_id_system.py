from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "backend"))

from app.services.content_normalizer.block_id import (  # noqa: E402
    is_valid_excel_block_id,
    is_valid_merged_cell_block_id,
    is_valid_pdf_block_id,
)
from app.services.content_normalizer.models import BoundingBox  # noqa: E402


def test_pdf_block_id_format_validation():
    assert is_valid_pdf_block_id("1.2.3:1:5")
    assert not is_valid_pdf_block_id("1.2.3-1-5")


def test_excel_block_id_format_validation():
    assert is_valid_excel_block_id("1.1.A1")
    assert is_valid_excel_block_id("2.3.Z10")
    assert not is_valid_excel_block_id("1.1.1A")


def test_merged_cell_block_id_format_validation():
    assert is_valid_merged_cell_block_id("1.1.B2:C2")
    assert not is_valid_merged_cell_block_id("1.1.B2C2")


def test_bounding_box_model_defaults():
    bbox = BoundingBox(
        raw_value="Value",
        top_left_x=0,
        top_left_y=0,
        bottom_right_x=1,
        bottom_right_y=1,
    )
    assert bbox.id == ""
    assert bbox.row is None
    assert bbox.col is None
    assert bbox.idx is None
