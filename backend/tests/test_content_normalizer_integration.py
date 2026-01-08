from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "backend"))

# Check if paddle is available (required for PaddleOCR)
try:
    import paddle
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False

from app.services.content_normalizer.normalizer import ContentNormalizer  # noqa: E402
from app.services.content_normalizer.extractor.ocr_engine import OcrSpan  # noqa: E402
from app.services.content_normalizer.block_id import is_valid_pdf_block_id, is_valid_excel_block_id  # noqa: E402


class FakeOcrEngine:
    def __init__(self, spans: list[OcrSpan]):
        self._spans = spans

    def extract(self, image_bytes: bytes) -> list[OcrSpan]:
        return list(self._spans)


@pytest.mark.skipif(not PADDLE_AVAILABLE, reason="paddle not installed")
def test_content_normalizer_pdf_pipeline_assigns_block_ids():
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((50, 60), "Invoice 123")
    pdf_bytes = doc.tobytes()
    doc.close()

    normalizer = ContentNormalizer()
    metadata = normalizer.normalize(
        file_bytes=pdf_bytes,
        file_name="sample.pdf",
        file_object_fid="local",
        doc_index=1,
    )

    assert metadata.content_type.name == "PDF"
    page = metadata.file_content.pages[0]
    assert page.bounding_boxes
    assert all(is_valid_pdf_block_id(bbox.id) for bbox in page.bounding_boxes)


@pytest.mark.skipif(not PADDLE_AVAILABLE, reason="paddle not installed")
def test_content_normalizer_excel_pipeline_assigns_block_ids():
    import openpyxl

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet["A1"] = "Invoice"

    buffer = BytesIO()
    workbook.save(buffer)
    excel_bytes = buffer.getvalue()

    normalizer = ContentNormalizer()
    metadata = normalizer.normalize(
        file_bytes=excel_bytes,
        file_name="sample.xlsx",
        file_object_fid="local",
        doc_index=1,
    )

    assert metadata.content_type.name == "EXCEL"
    ids = {bbox.id for bbox in metadata.file_content.sheets[0].bounding_boxes}
    assert any(is_valid_excel_block_id(block_id) for block_id in ids)


def test_content_normalizer_image_pipeline_assigns_block_ids():
    from PIL import Image

    image = Image.new("RGB", (100, 50), color=(255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    ocr_spans = [OcrSpan(text="TOTAL", top_left=(5, 5), bottom_right=(45, 15))]
    normalizer = ContentNormalizer(ocr_engine=FakeOcrEngine(ocr_spans))
    metadata = normalizer.normalize(
        file_bytes=image_bytes,
        file_name="image.png",
        file_object_fid="local",
        doc_index=1,
    )

    page = metadata.file_content.pages[0]
    assert page.bounding_boxes
    assert all(is_valid_pdf_block_id(bbox.id) for bbox in page.bounding_boxes)
