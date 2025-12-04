"""OCR processing service for invoice images using PaddleOCR."""

import re
import logging
import threading
from io import BytesIO
from typing import Optional, Dict, Any
from datetime import datetime, date

from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)

# Thread lock for singleton initialization
_ocr_lock = threading.Lock()
_extractor_lock = threading.Lock()


class OCRService:
    """Handles OCR processing for invoice images using PaddleOCR."""

    def __init__(self):
        self._ocr = None
        self._init_lock = threading.Lock()

    @property
    def ocr(self):
        """Lazy-load PaddleOCR instance (thread-safe)."""
        if self._ocr is None:
            with self._init_lock:
                # Double-check after acquiring lock
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

    def _extract_pdf_text_layer(self, pdf_data: bytes) -> tuple[str, bool]:
        """Try to extract embedded text from PDF using pdfplumber.

        pdfplumber is more robust than pdftotext for complex PDF structures,
        especially Chinese e-invoices which often have unusual text layouts.

        Args:
            pdf_data: Raw PDF bytes

        Returns:
            Tuple of (extracted_text, has_useful_text)
        """
        try:
            import pdfplumber
            import tempfile
            import os

            # Write PDF to temp file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                f.write(pdf_data)
                temp_pdf = f.name

            try:
                all_text = []
                with pdfplumber.open(temp_pdf) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            all_text.append(text)

                combined_text = "\n".join(all_text)

                # Check if we got meaningful invoice data
                # Look for actual invoice content: numbers, dates, amounts
                has_invoice_number = bool(re.search(r'\d{10,20}', combined_text))  # Long number (invoice number)
                has_tax_id = bool(re.search(r'[A-Z0-9]{15,20}', combined_text))  # Tax ID pattern
                has_amount = bool(re.search(r'[¥￥]?\s*\d+\.\d{2}', combined_text))  # Currency amount
                has_keywords = any(kw in combined_text for kw in ['发票', '税', '金额', '合计', '购买方', '销售方'])

                # Consider useful if has invoice-like content
                has_useful = len(combined_text) > 100 and has_keywords and (has_invoice_number or has_tax_id or has_amount)

                if has_useful:
                    logger.info(f"PDF text layer extraction successful (pdfplumber): {len(combined_text)} chars")
                else:
                    logger.debug(f"PDF text extraction got {len(combined_text)} chars but no useful invoice data")

                return combined_text, has_useful
            finally:
                os.unlink(temp_pdf)

        except Exception as e:
            logger.warning(f"PDF text layer extraction failed: {e}")
            return "", False

    def process_pdf(self, pdf_data: bytes) -> tuple[str, float]:
        """Process PDF and extract text from all pages.

        First tries to extract embedded text layer (faster, more accurate for digital PDFs),
        then falls back to OCR for scanned PDFs.

        Args:
            pdf_data: Raw PDF bytes

        Returns:
            Tuple of (extracted_text, average_confidence)
        """
        # First try to extract embedded text layer
        text_layer, has_useful_text = self._extract_pdf_text_layer(pdf_data)

        if has_useful_text:
            logger.info("Using PDF embedded text layer instead of OCR")
            # High confidence for embedded text
            return text_layer, 99.0

        # Fall back to OCR for scanned PDFs
        logger.info("PDF has no useful text layer, falling back to OCR")

        try:
            from pdf2image import convert_from_bytes

            # Use higher DPI (300) for better text recognition
            # Some PDFs have text rendered as graphics which need higher resolution
            images = convert_from_bytes(pdf_data, dpi=300)
            logger.info(f"PDF converted to {len(images)} images at 300 DPI")

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
    # Note: PaddleOCR often reads two-column invoices in interleaved order
    # This causes buyer/seller info to be mixed. We use position-based extraction.
    PATTERNS_CN = {
        'invoice_number': r'发票号码[：:]\s*(\d+)',
        'invoice_code': r'发票代码[：:]\s*(\d+)',
        'issue_date': r'开票日期[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2})',
        # For buyer/seller, we use special extraction in extract_fields() method
        # These patterns are placeholders - actual extraction uses _extract_buyer_seller()
        'buyer_name': None,  # Extracted specially
        'buyer_tax_id': None,  # Extracted specially
        'seller_name': None,  # Extracted specially
        'seller_tax_id': None,  # Extracted specially
        # Match items with * markers in Chinese invoices
        # Format is typically *类别*商品名称, we want to capture "类别*商品名称"
        # Example: *家具*办公椅 → captures "家具*办公椅"
        'item_name': r'\*([^*\n]+(?:\*[^*\n]+)*)',
        'total_with_tax': r'(?:小写|价税合计)[）)（(]*\s*[¥￥]\s*([\d,.]+)',
        'amount': r'(?:合\s*计|金\s*额)\s*[¥￥]?\s*([\d,.]+)',
        'tax_amount': r'(?:税\s*额\s*[¥￥]?\s*([\d,.]+)|[¥￥]\s*[\d,.]+\s*[¥￥]\s*([\d,.]+))',
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

    def _extract_buyer_seller(self, text: str) -> Dict[str, Optional[str]]:
        """Extract buyer and seller info based on position in OCR text.

        PaddleOCR reads two-column invoices in interleaved order, causing
        buyer/seller sections to be mixed. We use position-based extraction:
        - First company name = buyer
        - Second company name = seller
        - First tax ID = buyer's tax ID
        - Second tax ID = seller's tax ID

        Args:
            text: OCR extracted text

        Returns:
            Dictionary with buyer_name, buyer_tax_id, seller_name, seller_tax_id
        """
        result = {
            'buyer_name': None,
            'buyer_tax_id': None,
            'seller_name': None,
            'seller_tax_id': None,
        }

        # Pattern to match company names after "称：" or "名称："
        # The OCR text often has broken lines like "名\n称：" so we handle that
        # Use non-greedy match and stop before next "销" or "名称" marker
        # Match company name ending with 公司/集团, but stop before 销/购/名称
        name_pattern = r'(?:名\s*)?称[：:]\s*([^销购\n]*?(?:有限公司|股份公司|集团|公司))'
        name_matches = re.findall(name_pattern, text)

        if len(name_matches) >= 2:
            result['buyer_name'] = self._clean_chinese_spaces(name_matches[0])
            result['seller_name'] = self._clean_chinese_spaces(name_matches[1])
            logger.info(f"Position-based extraction: buyer={result['buyer_name']}, seller={result['seller_name']}")
        elif len(name_matches) == 1:
            # Only one match - try to determine if it's buyer or seller from context
            cleaned_name = self._clean_chinese_spaces(name_matches[0])
            if '购' in text[:text.find(name_matches[0])] if name_matches[0] in text else False:
                result['buyer_name'] = cleaned_name
            else:
                result['seller_name'] = cleaned_name
            logger.info(f"Single name found: {cleaned_name}")

        # Pattern to match tax IDs (纳税人识别号)
        # Chinese tax IDs are typically 15-20 characters with letters and numbers
        tax_id_pattern = r'(?:纳税人识别号|统一社会信用代码|税号)[：:]\s*([A-Z0-9]{15,20})'
        tax_matches = re.findall(tax_id_pattern, text, re.IGNORECASE)

        if len(tax_matches) >= 2:
            result['buyer_tax_id'] = tax_matches[0].strip()
            result['seller_tax_id'] = tax_matches[1].strip()
        elif len(tax_matches) == 1:
            # Try to match with identified company
            if result['buyer_name'] and not result['seller_name']:
                result['buyer_tax_id'] = tax_matches[0].strip()
            elif result['seller_name'] and not result['buyer_name']:
                result['seller_tax_id'] = tax_matches[0].strip()

        # Fallback: try alternative patterns if nothing found
        if not result['buyer_name'] and not result['seller_name']:
            # Try simpler pattern - any company name
            simple_pattern = r'([^\n]*(?:有限公司|股份公司))'
            simple_matches = re.findall(simple_pattern, text)
            if len(simple_matches) >= 2:
                result['buyer_name'] = self._clean_chinese_spaces(simple_matches[0])
                result['seller_name'] = self._clean_chinese_spaces(simple_matches[1])
                logger.info(f"Fallback extraction: buyer={result['buyer_name']}, seller={result['seller_name']}")

        return result

    def extract_fields(self, text: str) -> Dict[str, Any]:
        """Extract all invoice fields from OCR text.

        Args:
            text: OCR extracted text

        Returns:
            Dictionary of extracted fields
        """
        fields = {}

        # Log OCR text for debugging (first 500 chars)
        logger.debug(f"OCR text (first 500 chars): {text[:500]}")

        is_chinese = self._is_chinese_invoice(text)

        # Choose pattern set based on language detection
        if is_chinese:
            patterns = self.PATTERNS_CN
        else:
            patterns = self.PATTERNS_EN

        for field_name, pattern in patterns.items():
            # Skip fields with None pattern (they need special extraction)
            if pattern is None:
                fields[field_name] = None
                continue

            try:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    # Handle patterns with multiple capture groups (alternation)
                    # Use the first non-None group
                    value = None
                    for i in range(1, len(match.groups()) + 1):
                        if match.group(i):
                            value = match.group(i).strip()
                            break
                    fields[field_name] = self._clean_value(value, field_name) if value else None
                else:
                    fields[field_name] = None
            except Exception as e:
                logger.warning(f"Failed to extract {field_name}: {e}")
                fields[field_name] = None

        # For Chinese invoices, use position-based extraction for buyer/seller
        if is_chinese:
            buyer_seller = self._extract_buyer_seller(text)
            fields['buyer_name'] = buyer_seller['buyer_name']
            fields['buyer_tax_id'] = buyer_seller['buyer_tax_id']
            fields['seller_name'] = buyer_seller['seller_name']
            fields['seller_tax_id'] = buyer_seller['seller_tax_id']

        # Log extraction results for debugging
        logger.info(f"OCR extracted: buyer={fields.get('buyer_name')}, seller={fields.get('seller_name')}")

        return fields

    def _clean_chinese_spaces(self, text: str) -> str:
        """Remove extra spaces between Chinese characters.

        PDF text extraction often adds spaces between Chinese characters
        due to font/layout issues. This function removes those spaces
        while preserving spaces around English text.

        Examples:
            "深圳那时餐 饮管理有限公司" → "深圳那时餐饮管理有限公司"
            "餐 饮服 务" → "餐饮服务"
        """
        if not text:
            return text

        # Pattern: Chinese char + space(s) + Chinese char
        # Remove spaces between Chinese characters
        # Chinese Unicode range: \u4e00-\u9fff (CJK Unified Ideographs)
        cleaned = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', text)

        # May need multiple passes for consecutive spaces
        while re.search(r'[\u4e00-\u9fff]\s+[\u4e00-\u9fff]', cleaned):
            cleaned = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', cleaned)

        return cleaned.strip()

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

        # Clean Chinese text fields (remove extra spaces)
        if field_name in ['buyer_name', 'seller_name', 'item_name']:
            return self._clean_chinese_spaces(value)

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
    """Get thread-safe OCRService singleton."""
    global _ocr_service
    if _ocr_service is None:
        with _ocr_lock:
            # Double-check after acquiring lock
            if _ocr_service is None:
                _ocr_service = OCRService()
    return _ocr_service


def get_field_extractor() -> FieldExtractor:
    """Get thread-safe FieldExtractor singleton."""
    global _field_extractor
    if _field_extractor is None:
        with _extractor_lock:
            # Double-check after acquiring lock
            if _field_extractor is None:
                _field_extractor = FieldExtractor()
    return _field_extractor
