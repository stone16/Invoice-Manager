from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class InvoiceStatus(str, Enum):
    UPLOADED = "已上传"      # File uploaded, waiting for OCR processing
    PROCESSING = "解析中"    # OCR/LLM processing in progress
    PENDING = "待处理"       # Processing complete, no conflicts
    REVIEWING = "待审核"     # Has conflicts or missing fields, needs manual review
    CONFIRMED = "已确认"     # Manually reviewed and confirmed
    REIMBURSED = "已报销"    # Reimbursement completed
    NOT_REIMBURSED = "未报销" # Not yet reimbursed


class InvoiceBase(BaseModel):
    invoice_number: Optional[str] = Field(None, description="发票号码")
    issue_date: Optional[date] = Field(None, description="开票日期")
    buyer_name: Optional[str] = Field(None, description="购买方名称")
    buyer_tax_id: Optional[str] = Field(None, description="购买方纳税人识别号")
    seller_name: Optional[str] = Field(None, description="销售方名称")
    seller_tax_id: Optional[str] = Field(None, description="销售方纳税人识别号")
    item_name: Optional[str] = Field(None, description="项目名称")
    total_with_tax: Optional[Decimal] = Field(None, description="价税合计金额")
    specification: Optional[str] = Field(None, description="规格型号")
    unit: Optional[str] = Field(None, description="单位")
    quantity: Optional[Decimal] = Field(None, description="数量")
    unit_price: Optional[Decimal] = Field(None, description="单价")
    amount: Optional[Decimal] = Field(None, description="金额")
    tax_rate: Optional[str] = Field(None, description="税率")
    tax_amount: Optional[Decimal] = Field(None, description="税额")


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(InvoiceBase):
    status: Optional[InvoiceStatus] = None
    owner: Optional[str] = None


class InvoiceResponse(InvoiceBase):
    id: int
    file_name: str
    file_type: str
    status: InvoiceStatus
    owner: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    items: List[InvoiceResponse]
    total: int
    page: int
    page_size: int


class OcrResultResponse(BaseModel):
    id: int
    invoice_id: int
    raw_text: Optional[str] = None
    invoice_number: Optional[str] = None
    issue_date: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_tax_id: Optional[str] = None
    seller_name: Optional[str] = None
    seller_tax_id: Optional[str] = None
    item_name: Optional[str] = None
    total_with_tax: Optional[str] = None
    specification: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[str] = None
    unit_price: Optional[str] = None
    amount: Optional[str] = None
    tax_rate: Optional[str] = None
    tax_amount: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LlmResultResponse(BaseModel):
    id: int
    invoice_id: int
    invoice_number: Optional[str] = None
    issue_date: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_tax_id: Optional[str] = None
    seller_name: Optional[str] = None
    seller_tax_id: Optional[str] = None
    item_name: Optional[str] = None
    total_with_tax: Optional[str] = None
    specification: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[str] = None
    unit_price: Optional[str] = None
    amount: Optional[str] = None
    tax_rate: Optional[str] = None
    tax_amount: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ParsingDiffResponse(BaseModel):
    id: int
    invoice_id: int
    field_name: str
    ocr_value: Optional[str] = None
    llm_value: Optional[str] = None
    final_value: Optional[str] = None
    source: Optional[str] = None
    resolved: int = 0

    class Config:
        from_attributes = True


class InvoiceDetailResponse(InvoiceResponse):
    ocr_result: Optional[OcrResultResponse] = None
    llm_result: Optional[LlmResultResponse] = None
    parsing_diffs: List[ParsingDiffResponse] = []


class BatchUpdateRequest(BaseModel):
    invoice_ids: List[int]
    status: Optional[InvoiceStatus] = None
    owner: Optional[str] = None


class BatchDeleteRequest(BaseModel):
    invoice_ids: List[int] = Field(..., description="要删除的发票ID列表")


class StatisticsResponse(BaseModel):
    count: int = Field(description="发票数量")
    total_amount: Decimal = Field(description="金额合计")
    total_tax: Decimal = Field(description="税额合计")
    total_with_tax: Decimal = Field(description="价税合计")


class UploadResponse(BaseModel):
    id: int
    file_name: str
    status: str
    message: str


class ResolveDiffRequest(BaseModel):
    """Request to resolve a parsing diff by selecting a source value."""
    source: str = Field(..., description="'ocr', 'llm', or 'custom'")
    custom_value: Optional[str] = Field(None, description="Custom value if source is 'custom'")
