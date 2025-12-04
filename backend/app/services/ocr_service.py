"""OCR processing service for invoice images using PaddleOCR."""

import re
import logging
from io import BytesIO
from typing import Optional, Dict, Any
from datetime import datetime, date

from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class OCRService:
    """Handles OCR processing for invoice images using PaddleOCR."""

    def __init__(self):
        self._ocr = None

    @property
    def ocr(self):
        """Lazy-load PaddleOCR instance."""
        if self._ocr is None:
            from paddleocr import PaddleOCR
            import logging as log_module
            # Suppress PaddleOCR logging
            log_module.getLogger('ppocr').setLevel(log_module.WARNING)
            log_module.getLogger('paddlex').setLevel(log_module.WARNING)
            logger.info("Initializing PaddleOCR...")
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang='ch',
            )
            logger.info("PaddleOCR initialized successfully")
        return self._ocr

    def _extract_text_from_result(self, result) -> tuple[list, list]:
        """Extract text and confidences from OCR result (v2.x API)."""
        text_lines = []
        confidences = []

        if not result:
            return text_lines, confidences

        # PaddleOCR v2.x returns list of [bbox, (text, confidence)]
        for item in result:
            if isinstance(item, list) and len(item) >= 2:
                # Format: [bbox, (text, confidence)]
                if isinstance(item[1], tuple) and len(item[1]) >= 2:
                    text, confidence = item[1]
                    if text:
                        text_lines.append(text)
                        confidences.append(confidence * 100 if confidence <= 1.0 else confidence)

        return text_lines, confidences

    def process_image(self, image_data: bytes) -> tuple[str, float]:
        """Process image bytes and extract text.

        Args:
            image_data: Raw image bytes

        Returns:
            Tuple of (extracted_text, average_confidence)
        """
        try:
            image = Image.open(BytesIO(image_data))
            image_array = np.array(image)

            # PaddleOCR v2.x uses ocr() method
            result = self.ocr.ocr(image_array, cls=True)
            if result and result[0]:
                result = result[0]

            text_lines, confidences = self._extract_text_from_result(result)

            combined_text = "\n".join(text_lines)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return combined_text, avg_confidence

        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            raise

    def process_pdf(self, pdf_data: bytes) -> tuple[str, float]:
        """Process PDF and extract text from all pages.

        Args:
            pdf_data: Raw PDF bytes

        Returns:
            Tuple of (extracted_text, average_confidence)
        """
        try:
            from pdf2image import convert_from_bytes

            images = convert_from_bytes(pdf_data, dpi=200)

            all_text = []
            all_confidences = []

            for image in images:
                image_array = np.array(image)

                # PaddleOCR v2.x uses ocr() method
                result = self.ocr.ocr(image_array, cls=True)
                if result and result[0]:
                    result = result[0]

                text_lines, confidences = self._extract_text_from_result(result)
                all_text.extend(text_lines)
                all_confidences.extend(confidences)

            combined_text = "\n".join(all_text)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

            return combined_text, avg_confidence

        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            raise


class FieldExtractor:
    """Extracts structured fields from invoice text (Chinese and English)."""

    # Regex patterns for Chinese invoice fields
    # Chinese invoices typically have buyer (购买方) at the top-left, seller (销售方) at the bottom-left
    PATTERNS_CN = {
        'invoice_number': r'发票号码[：:]\s*(\d+)',
        'invoice_code': r'发票代码[：:]\s*(\d+)',
        'issue_date': r'开票日期[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2})',
        # Buyer patterns - multiple strategies for different invoice formats
        # Pattern 1: "名称：XXX" after 购买方 section
        # Pattern 2: "购买方" followed by "名称" on next line(s)
        # Pattern 3: Direct match after 购买方名称
        'buyer_name': r'(?:购买方|购\s*买\s*方)[\s\S]*?名\s*称[：:]\s*([^\n]+?)(?=\s*(?:纳税人识别号|统一社会信用代码|地\s*址|开户行|\n\s*\n|$))',
        'buyer_tax_id': r'(?:购买方|购\s*买\s*方)[\s\S]*?(?:纳税人识别号|统一社会信用代码)[/／]?[：:]\s*([A-Z0-9]+)',
        # Seller patterns - similar strategies
        'seller_name': r'(?:销售方|销\s*售\s*方)[\s\S]*?名\s*称[：:]\s*([^\n]+?)(?=\s*(?:纳税人识别号|统一社会信用代码|地\s*址|开户行|\n\s*\n|$))',
        'seller_tax_id': r'(?:销售方|销\s*售\s*方)[\s\S]*?(?:纳税人识别号|统一社会信用代码)[/／]?[：:]\s*([A-Z0-9]+)',
        # Match item after * markers or 项目名称 header
        'item_name': r'\*([^*\n]+)\*',
        'total_with_tax': r'(?:小写|价税合计)[）)（(]*[¥￥]\s*([\d,.]+)',
        'amount': r'(?:合\s*计|金额)[¥￥]?\s*([\d,.]+)',
        'tax_amount': r'税\s*额[¥￥]?\s*([\d,.]+)',
        'tax_rate': r'(?:税率[/／征收率]*[：:]?\s*|金额\n)(\d+%?|免税)',
    }

    # Regex patterns for English invoice fields
    PATTERNS_EN = {
        'invoice_number': r'(?:Invoice\s*#?|INV[_-]?|#)\s*[:#]?\s*([A-Z0-9_-]+)',
        'issue_date': r'(?:Date|Invoice\s+Date)[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        'buyer_name': r'Bill\s*To[:\s]*\n(?:.*\n)*?([A-Za-z][A-Za-z0-9\s]+?)(?:\n\d|\n[A-Z][a-z])',
        'seller_name': r'INVOICE\n#[^\n]+\n([A-Za-z][A-Za-z\s]+)',
        'total_with_tax': r'(?:Total|Balance\s+Due|Amount\s+Due)[:\s]*\$?\s*([\d,.]+)',
        'amount': r'(?:Subtotal)[:\s]*\$?\s*([\d,.]+)',
    }

    def _is_chinese_invoice(self, text: str) -> bool:
        """Detect if the invoice is in Chinese."""
        chinese_keywords = ['发票', '购买方', '销售方', '税额', '价税合计', '纳税人']
        return any(kw in text for kw in chinese_keywords)

    def extract_fields(self, text: str) -> Dict[str, Any]:
        """Extract all invoice fields from OCR text.

        Args:
            text: OCR extracted text

        Returns:
            Dictionary of extracted fields
        """
        fields = {}

        # Choose pattern set based on language detection
        if self._is_chinese_invoice(text):
            patterns = self.PATTERNS_CN
        else:
            patterns = self.PATTERNS_EN

        for field_name, pattern in patterns.items():
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    fields[field_name] = self._clean_value(value, field_name)
                else:
                    fields[field_name] = None
            except Exception as e:
                logger.warning(f"Failed to extract {field_name}: {e}")
                fields[field_name] = None

        return fields

    def _clean_value(self, value: str, field_name: str) -> Any:
        """Clean and convert field value to appropriate type."""
        if not value:
            return None

        # Parse date fields
        if field_name == 'issue_date':
            return self._parse_date(value)

        # Parse currency fields
        if field_name in ['total_with_tax', 'amount', 'tax_amount']:
            return self._parse_currency(value)

        return value

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format (supports Chinese and English)."""
        if not date_str:
            return None

        # Handle Chinese date format (年月日)
        date_str = date_str.replace("年", "-").replace("月", "-").replace("日", "")
        date_str = date_str.replace("/", "-")

        # Try various date formats
        formats = [
            "%Y-%m-%d",           # 2018-08-13
            "%m-%d-%Y",           # 08-13-2018
            "%d-%m-%Y",           # 13-08-2018
            "%B %d, %Y",          # August 13, 2018
            "%b %d, %Y",          # Aug 13, 2018
            "%B %d %Y",           # August 13 2018
            "%b %d %Y",           # Aug 13 2018
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(date_str.strip(), fmt)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return date_str

    def _parse_currency(self, currency_str: str) -> Optional[str]:
        """Parse currency string, return as string to preserve precision."""
        if not currency_str:
            return None

        # Remove currency symbols and formatting
        cleaned = re.sub(r'[$¥￥,\s]', '', currency_str)

        try:
            float(cleaned)
            return cleaned
        except ValueError:
            return currency_str


# Singleton instances
_ocr_service: Optional[OCRService] = None
_field_extractor: Optional[FieldExtractor] = None


def get_ocr_service() -> OCRService:
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service


def get_field_extractor() -> FieldExtractor:
    global _field_extractor
    if _field_extractor is None:
        _field_extractor = FieldExtractor()
    return _field_extractor
