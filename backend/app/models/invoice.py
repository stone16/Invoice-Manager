from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Numeric,
    Text, LargeBinary, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship

from app.database import Base


class InvoiceStatus(str, Enum):
    UPLOADED = "已上传"      # File uploaded, waiting for OCR processing
    PROCESSING = "解析中"    # OCR/LLM processing in progress
    PENDING = "待处理"       # Processing complete, no conflicts (legacy, kept for compatibility)
    REVIEWING = "待审核"     # Has conflicts or missing fields, needs manual review
    CONFIRMED = "已确认"     # Manually reviewed and confirmed
    REIMBURSED = "已报销"    # Reimbursement completed
    NOT_REIMBURSED = "未报销" # Not yet reimbursed


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)

    # File storage
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf, jpg, png
    file_data = Column(LargeBinary, nullable=False)

    # Required fields (NOT NULL)
    invoice_number = Column(String(50), nullable=True)  # 发票号码
    issue_date = Column(Date, nullable=True)  # 开票日期
    buyer_name = Column(String(255), nullable=True)  # 购买方名称
    buyer_tax_id = Column(String(50), nullable=True)  # 购买方纳税人识别号
    seller_name = Column(String(255), nullable=True)  # 销售方名称
    seller_tax_id = Column(String(50), nullable=True)  # 销售方纳税人识别号
    item_name = Column(String(500), nullable=True)  # 项目名称/货物名称
    total_with_tax = Column(Numeric(12, 2), nullable=True)  # 价税合计金额

    # Optional fields (can be NULL)
    specification = Column(String(255), nullable=True)  # 规格型号
    unit = Column(String(50), nullable=True)  # 单位
    quantity = Column(Numeric(12, 4), nullable=True)  # 数量
    unit_price = Column(Numeric(12, 4), nullable=True)  # 单价
    amount = Column(Numeric(12, 2), nullable=True)  # 金额(不含税)
    tax_rate = Column(String(20), nullable=True)  # 税率
    tax_amount = Column(Numeric(12, 2), nullable=True)  # 税额

    # Status management
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.PENDING, nullable=False)
    owner = Column(String(100), nullable=True)  # 归属人

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships (cascade delete to clean up related records)
    ocr_result = relationship("OcrResult", back_populates="invoice", uselist=False, cascade="all, delete-orphan")
    llm_result = relationship("LlmResult", back_populates="invoice", uselist=False, cascade="all, delete-orphan")
    parsing_diffs = relationship("ParsingDiff", back_populates="invoice", cascade="all, delete-orphan")


class OcrResult(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, unique=True)

    # Parsed fields from OCR
    raw_text = Column(Text, nullable=True)  # 原始OCR文本
    invoice_number = Column(String(50), nullable=True)
    issue_date = Column(String(50), nullable=True)
    buyer_name = Column(String(255), nullable=True)
    buyer_tax_id = Column(String(50), nullable=True)
    seller_name = Column(String(255), nullable=True)
    seller_tax_id = Column(String(50), nullable=True)
    item_name = Column(String(500), nullable=True)
    total_with_tax = Column(String(50), nullable=True)
    specification = Column(String(255), nullable=True)
    unit = Column(String(50), nullable=True)
    quantity = Column(String(50), nullable=True)
    unit_price = Column(String(50), nullable=True)
    amount = Column(String(50), nullable=True)
    tax_rate = Column(String(20), nullable=True)
    tax_amount = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    invoice = relationship("Invoice", back_populates="ocr_result")


class LlmResult(Base):
    __tablename__ = "llm_results"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, unique=True)

    # Parsed fields from LLM
    invoice_number = Column(String(50), nullable=True)
    issue_date = Column(String(50), nullable=True)
    buyer_name = Column(String(255), nullable=True)
    buyer_tax_id = Column(String(50), nullable=True)
    seller_name = Column(String(255), nullable=True)
    seller_tax_id = Column(String(50), nullable=True)
    item_name = Column(String(500), nullable=True)
    total_with_tax = Column(String(50), nullable=True)
    specification = Column(String(255), nullable=True)
    unit = Column(String(50), nullable=True)
    quantity = Column(String(50), nullable=True)
    unit_price = Column(String(50), nullable=True)
    amount = Column(String(50), nullable=True)
    tax_rate = Column(String(20), nullable=True)
    tax_amount = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    invoice = relationship("Invoice", back_populates="llm_result")


class ParsingDiff(Base):
    __tablename__ = "parsing_diffs"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)

    field_name = Column(String(100), nullable=False)  # 字段名
    ocr_value = Column(Text, nullable=True)  # OCR解析值
    llm_value = Column(Text, nullable=True)  # LLM解析值
    final_value = Column(Text, nullable=True)  # 最终确认值
    source = Column(String(20), nullable=True)  # ocr/llm/manual
    resolved = Column(Integer, default=0)  # 0=未解决, 1=已解决

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    invoice = relationship("Invoice", back_populates="parsing_diffs")
