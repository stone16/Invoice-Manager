from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import List, Tuple

import numpy as np
from PIL import Image

from app.services.content_normalizer.text_normalizer import normalize_text


@dataclass(frozen=True)
class OcrSpan:
    text: str
    top_left: Tuple[float, float]
    bottom_right: Tuple[float, float]


class PaddleOcrEngine:
    def __init__(self, lang: str = "ch", use_angle_cls: bool = True):
        from paddleocr import PaddleOCR
        import logging as log_module

        log_module.getLogger("ppocr").setLevel(log_module.WARNING)
        log_module.getLogger("paddlex").setLevel(log_module.WARNING)
        self._ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang)

    def extract(self, image_bytes: bytes) -> List[OcrSpan]:
        image = Image.open(BytesIO(image_bytes))
        image_array = np.array(image)
        result = self._ocr.ocr(image_array, cls=True)
        spans: List[OcrSpan] = []
        if not result:
            return spans
        for item in result[0]:
            if not isinstance(item, list) or len(item) < 2:
                continue
            bbox_points, text_info = item
            if not isinstance(text_info, tuple) or len(text_info) < 1:
                continue
            raw_text = text_info[0]
            is_valid, processed = normalize_text(raw_text)
            if not is_valid:
                continue
            xs = [point[0] for point in bbox_points]
            ys = [point[1] for point in bbox_points]
            spans.append(
                OcrSpan(
                    text=processed,
                    top_left=(min(xs), min(ys)),
                    bottom_right=(max(xs), max(ys)),
                )
            )
        return spans
