from __future__ import annotations

from typing import Optional

from app.models.digi_flow import FileContentType
from app.services.content_normalizer.block_id import assign_pdf_block_ids
from app.services.content_normalizer.clustering import cluster_into_coordinates
from app.services.content_normalizer.extractor import ExcelExtractor, ImageExtractor, PDFExtractor
from app.services.content_normalizer.models import FileContentMetadata, PageContent


class ContentNormalizer:
    def __init__(self, ocr_engine: Optional[object] = None):
        self._pdf_extractor = PDFExtractor(ocr_engine=ocr_engine)
        self._image_extractor = ImageExtractor(ocr_engine=ocr_engine)
        self._excel_extractor = ExcelExtractor()

    def _detect_type(self, file_name: str) -> FileContentType:
        ext = file_name.split(".")[-1].lower()
        if ext == "pdf":
            return FileContentType.PDF
        if ext in {"xlsx", "xls"}:
            return FileContentType.EXCEL
        if ext in {"png", "jpg", "jpeg", "bmp", "tiff"}:
            return FileContentType.IMAGE
        raise ValueError(f"Unsupported file type: {ext}")

    def _assign_pdf_block_ids(self, metadata: FileContentMetadata) -> FileContentMetadata:
        updated_pages = []
        for page in metadata.file_content.pages:
            clustered = cluster_into_coordinates(page.bounding_boxes)
            with_ids = assign_pdf_block_ids(metadata.index, page.id, clustered)
            updated_pages.append(page.model_copy(update={"bounding_boxes": with_ids}))
        updated_content = PageContent(pages=updated_pages)
        return metadata.model_copy(update={"file_content": updated_content})

    def normalize(
        self,
        file_bytes: bytes,
        file_name: str,
        file_object_fid: str,
        doc_index: int = 1,
    ) -> FileContentMetadata:
        content_type = self._detect_type(file_name)
        if content_type == FileContentType.PDF:
            metadata = self._pdf_extractor.extract(
                file_bytes=file_bytes,
                doc_index=doc_index,
                file_name=file_name,
                file_object_fid=file_object_fid,
            )
            return self._assign_pdf_block_ids(metadata)
        if content_type == FileContentType.IMAGE:
            metadata = self._image_extractor.extract(
                file_bytes=file_bytes,
                doc_index=doc_index,
                file_name=file_name,
                file_object_fid=file_object_fid,
            )
            return self._assign_pdf_block_ids(metadata)
        if content_type == FileContentType.EXCEL:
            return self._excel_extractor.extract(
                file_bytes=file_bytes,
                doc_index=doc_index,
                file_name=file_name,
                file_object_fid=file_object_fid,
            )
        raise ValueError(f"Unsupported content type: {content_type}")
