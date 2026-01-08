from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "backend"))

from app.services.content_normalizer.extractor.pdf_extractor import PDFExtractor  # noqa: E402
from app.services.content_normalizer.extractor.image_extractor import ImageExtractor  # noqa: E402
from app.services.content_normalizer.extractor.excel_extractor import ExcelExtractor  # noqa: E402
from app.services.content_normalizer.extractor.ocr_engine import OcrSpan  # noqa: E402
from app.services.content_normalizer.text_normalizer import normalize_chinese_text  # noqa: E402


class FakeOcrEngine:
    def __init__(self, spans: list[OcrSpan]):
        self._spans = spans

    def extract(self, image_bytes: bytes) -> list[OcrSpan]:
        return list(self._spans)


@pytest.mark.parametrize("text", ["Invoice 123", "发票号码 123456"])
def test_pdf_extractor_extracts_text_with_positions(text: str):
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((50, 60), text)
    pdf_bytes = doc.tobytes()
    doc.close()

    extractor = PDFExtractor(ocr_engine=FakeOcrEngine([]))
    metadata = extractor.extract(
        file_bytes=pdf_bytes,
        doc_index=1,
        file_name="sample.pdf",
        file_object_fid="local",
    )

    assert metadata.file_content.pages
    page_content = metadata.file_content.pages[0]
    assert page_content.bounding_boxes
    texts = {bbox.raw_value for bbox in page_content.bounding_boxes}
    assert any(text in value for value in texts)
    assert all(bbox.bottom_right_x >= bbox.top_left_x for bbox in page_content.bounding_boxes)
    assert all(bbox.bottom_right_y >= bbox.top_left_y for bbox in page_content.bounding_boxes)


def test_pdf_extractor_merges_embedded_image_ocr_results():
    import fitz
    from PIL import Image

    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((10, 10), "Header")
    image = Image.new("RGB", (40, 20), color=(255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    page.insert_image(fitz.Rect(0, 20, 40, 40), stream=buffer.getvalue())
    pdf_bytes = doc.tobytes()
    doc.close()

    ocr_spans = [OcrSpan(text="OCR", top_left=(10, 20), bottom_right=(40, 30))]
    extractor = PDFExtractor(ocr_engine=FakeOcrEngine(ocr_spans))
    metadata = extractor.extract(
        file_bytes=pdf_bytes,
        doc_index=1,
        file_name="mixed.pdf",
        file_object_fid="local",
    )

    texts = {bbox.raw_value for bbox in metadata.file_content.pages[0].bounding_boxes}
    assert "Header" in " ".join(texts)
    assert "OCR" in texts


def test_image_extractor_uses_paddle_ocr_engine():
    from PIL import Image

    image = Image.new("RGB", (100, 50), color=(255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    ocr_spans = [OcrSpan(text="TOTAL", top_left=(5, 5), bottom_right=(45, 15))]
    extractor = ImageExtractor(ocr_engine=FakeOcrEngine(ocr_spans))
    metadata = extractor.extract(
        file_bytes=image_bytes,
        doc_index=1,
        file_name="image.png",
        file_object_fid="local",
    )

    assert metadata.file_content.pages[0].bounding_boxes
    assert metadata.file_content.pages[0].bounding_boxes[0].raw_value == "TOTAL"


def test_excel_extractor_extracts_cells_and_merged_ranges():
    import openpyxl

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet["A1"] = "Invoice"
    sheet["B2"] = "Merged"
    sheet.merge_cells("B2:C2")

    buffer = BytesIO()
    workbook.save(buffer)
    excel_bytes = buffer.getvalue()

    extractor = ExcelExtractor()
    metadata = extractor.extract(
        file_bytes=excel_bytes,
        doc_index=1,
        file_name="sample.xlsx",
        file_object_fid="local",
    )

    sheet_content = metadata.file_content.sheets[0]
    ids = {bbox.id for bbox in sheet_content.bounding_boxes}
    assert "1.1.A1" in ids
    assert "1.1.B2:C2" in ids


def test_normalize_chinese_text_removes_intra_word_spaces():
    text = "发 票 号 码  123456"
    assert normalize_chinese_text(text) == "发票号码 123456"
