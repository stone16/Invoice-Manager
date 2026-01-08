from __future__ import annotations

from typing import List, Optional, Union

from pydantic import BaseModel, Field

from app.models.digi_flow import FileContentType


class BoundingBox(BaseModel):
    id: str = ""
    raw_value: str
    top_left_x: float
    top_left_y: float
    bottom_right_x: float
    bottom_right_y: float
    row: Optional[int] = None
    col: Optional[int] = None
    idx: Optional[int] = None


class Page(BaseModel):
    id: int
    width: int
    height: int
    bounding_boxes: List[BoundingBox] = Field(default_factory=list)


class PageContent(BaseModel):
    pages: List[Page] = Field(default_factory=list)


class Sheet(BaseModel):
    id: int
    name: str
    bounding_boxes: List[BoundingBox] = Field(default_factory=list)


class SheetContent(BaseModel):
    sheets: List[Sheet] = Field(default_factory=list)


class FileContentMetadata(BaseModel):
    index: int
    file_object_fid: str
    file_name: str
    file_bytes_size: int
    content_type: FileContentType
    languages: List[str] = Field(default_factory=list)
    file_content: Union[PageContent, SheetContent]
