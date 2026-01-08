from __future__ import annotations

from io import BytesIO
from typing import List, Optional

from PIL import Image

from app.models.digi_flow import FileContentType
from app.services.content_normalizer.models import BoundingBox, FileContentMetadata, Page, PageContent
from app.services.content_normalizer.extractor.ocr_engine import OcrSpan, PaddleOcrEngine


class ImageExtractor:
    def __init__(self, ocr_engine: Optional[PaddleOcrEngine] = None):
        self._ocr_engine = ocr_engine or PaddleOcrEngine()

    def _spans_to_boxes(self, spans: List[OcrSpan]) -> List[BoundingBox]:
        return [
            BoundingBox(
                id="",
                raw_value=span.text,
                top_left_x=span.top_left[0],
                top_left_y=span.top_left[1],
                bottom_right_x=span.bottom_right[0],
                bottom_right_y=span.bottom_right[1],
            )
            for span in spans
        ]

    def extract(
        self,
        file_bytes: bytes,
        doc_index: int,
        file_name: str,
        file_object_fid: str,
    ) -> FileContentMetadata:
        image = Image.open(BytesIO(file_bytes))
        width, height = image.size
        spans = self._ocr_engine.extract(file_bytes)
        bounding_boxes = self._spans_to_boxes(spans)
        page = Page(id=1, width=width, height=height, bounding_boxes=bounding_boxes)
        content = PageContent(pages=[page])
        return FileContentMetadata(
            index=doc_index,
            file_object_fid=file_object_fid,
            file_name=file_name,
            file_bytes_size=len(file_bytes),
            content_type=FileContentType.IMAGE,
            languages=["zh"],
            file_content=content,
        )
