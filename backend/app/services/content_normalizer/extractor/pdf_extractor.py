from __future__ import annotations

from typing import List, Optional

import fitz

from app.models.digi_flow import FileContentType
from app.services.content_normalizer.block_id import build_image_block_id, build_pdf_text_block_id
from app.services.content_normalizer.extractor.ocr_engine import OcrSpan, PaddleOcrEngine
from app.services.content_normalizer.models import BoundingBox, FileContentMetadata, Page, PageContent
from app.services.content_normalizer.text_normalizer import normalize_text


class PDFExtractor:
    """Extractor for PDF documents with optional OCR on images."""

    def __init__(self, ocr_engine: Optional[PaddleOcrEngine] = None):
        """Initialize PDF extractor with optional OCR engine."""
        self._ocr_engine = ocr_engine

    def _extract_text_bboxes(self, page: fitz.Page, doc_index: int, page_index: int) -> List[BoundingBox]:
        """Extract text bounding boxes from a PDF page."""
        bboxes: List[BoundingBox] = []
        text_dict = page.get_text("dict")
        bbox_idx = 0
        for block in text_dict.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    is_valid, processed_text = normalize_text(span.get("text", ""))
                    if not is_valid:
                        continue
                    bbox = span.get("bbox", [])
                    if len(bbox) != 4:
                        continue
                    bbox_idx += 1
                    bboxes.append(
                        BoundingBox(
                            id=build_pdf_text_block_id(doc_index, page_index, bbox_idx),
                            raw_value=processed_text,
                            top_left_x=bbox[0],
                            top_left_y=bbox[1],
                            bottom_right_x=bbox[2],
                            bottom_right_y=bbox[3],
                        )
                    )
        return bboxes

    def _spans_to_boxes(
        self,
        spans: List[OcrSpan],
        x_offset: float,
        y_offset: float,
        scale_x: float,
        scale_y: float,
        doc_index: int,
        page_index: int,
        start_idx: int,
    ) -> List[BoundingBox]:
        """Convert OCR spans to PDF-space bounding boxes."""
        boxes: List[BoundingBox] = []
        for idx, span in enumerate(spans, start=start_idx):
            boxes.append(
                BoundingBox(
                    id=build_image_block_id(doc_index, page_index, idx),
                    raw_value=span.text,
                    top_left_x=span.top_left[0] * scale_x + x_offset,
                    top_left_y=span.top_left[1] * scale_y + y_offset,
                    bottom_right_x=span.bottom_right[0] * scale_x + x_offset,
                    bottom_right_y=span.bottom_right[1] * scale_y + y_offset,
                )
            )
        return boxes

    def _extract_image_bboxes(self, pdf: fitz.Document, page: fitz.Page, doc_index: int, page_index: int) -> List[BoundingBox]:
        """Extract OCR bounding boxes from images embedded in a PDF page."""
        if not self._ocr_engine:
            return []
        bboxes: List[BoundingBox] = []
        ocr_cache: dict[int, tuple[List[OcrSpan], int, int]] = {}
        span_idx = 0
        for img in page.get_images(full=True):
            xref = img[0]
            if xref not in ocr_cache:
                image_info = pdf.extract_image(xref)
                image_bytes = image_info["image"]
                img_width = image_info.get("width", 0) or 0
                img_height = image_info.get("height", 0) or 0
                if img_width <= 0 or img_height <= 0:
                    ocr_cache[xref] = ([], 0, 0)
                    continue
                ocr_cache[xref] = (self._ocr_engine.extract(image_bytes), img_width, img_height)

            spans, img_width, img_height = ocr_cache[xref]
            if not spans or img_width <= 0 or img_height <= 0:
                continue
            for rect in page.get_image_rects(xref):
                x0, x1 = sorted((rect.x0, rect.x1))
                y0, y1 = sorted((rect.y0, rect.y1))
                if x1 <= x0 or y1 <= y0:
                    continue
                scale_x = (x1 - x0) / img_width
                scale_y = (y1 - y0) / img_height
                if spans:
                    bboxes.extend(
                        self._spans_to_boxes(
                            spans,
                            x0,
                            y0,
                            scale_x,
                            scale_y,
                            doc_index,
                            page_index,
                            span_idx + 1,
                        )
                    )
                    span_idx += len(spans)
        return bboxes

    def extract(
        self,
        file_bytes: bytes,
        doc_index: int,
        file_name: str,
        file_object_fid: str,
        languages: Optional[List[str]] = None,
    ) -> FileContentMetadata:
        """Extract content metadata from a PDF file."""
        pages: List[Page] = []
        with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
            for page_index, page in enumerate(pdf, start=1):
                text_boxes = self._extract_text_bboxes(page, doc_index, page_index)
                image_boxes = self._extract_image_bboxes(pdf, page, doc_index, page_index)
                page_boxes = text_boxes + image_boxes
                width, height = int(page.rect.width), int(page.rect.height)
                pages.append(Page(id=page_index, width=width, height=height, bounding_boxes=page_boxes))

        content = PageContent(pages=pages)
        return FileContentMetadata(
            index=doc_index,
            file_object_fid=file_object_fid,
            file_name=file_name,
            file_bytes_size=len(file_bytes),
            content_type=FileContentType.PDF,
            languages=languages or ["zh"],
            file_content=content,
        )
