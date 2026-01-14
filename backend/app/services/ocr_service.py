"""OCR processing service for invoice images using PaddleOCR."""

import re
import logging
import threading
from io import BytesIO
from typing import Optional, Dict, Any, List, Tuple
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

    def _extract_text_from_result(self, result) -> Tuple[List[str], List[float], List[Dict[str, Any]]]:
        """Extract text, confidences, and line metadata from OCR result (v2.x API)."""
        text_lines: List[str] = []
        confidences: List[float] = []
        line_items: List[Dict[str, Any]] = []

        if not result:
            return text_lines, confidences, line_items

        # PaddleOCR v2.x returns list of [bbox, (text, confidence)]
        for item in result:
            if isinstance(item, list) and len(item) >= 2:
                bbox = item[0]
                if isinstance(item[1], tuple) and len(item[1]) >= 2:
                    text, confidence = item[1]
                    if not text:
                        continue

                    conf_score = confidence * 100 if confidence <= 1.0 else confidence
                    text_lines.append(text)
                    confidences.append(conf_score)

                    if isinstance(bbox, list) and len(bbox) >= 4:
                        xs = [point[0] for point in bbox if isinstance(point, (list, tuple)) and len(point) >= 2]
                        ys = [point[1] for point in bbox if isinstance(point, (list, tuple)) and len(point) >= 2]
                        if xs and ys:
                            min_x = min(xs)
                            max_x = max(xs)
                            min_y = min(ys)
                            max_y = max(ys)
                            line_items.append({
                                "text": text,
                                "confidence": conf_score,
                                "bbox": bbox,
                                "min_x": min_x,
                                "max_x": max_x,
                                "min_y": min_y,
                                "max_y": max_y,
                                "center_x": (min_x + max_x) / 2,
                                "center_y": (min_y + max_y) / 2,
                            })

        return text_lines, confidences, line_items

    def _sort_lines_by_position(self, lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort OCR lines by approximate reading order (top-to-bottom, left-to-right)."""
        if not lines:
            return []
        return sorted(lines, key=lambda item: (round(item["min_y"] / 10), item["min_x"]))

    def process_image(self, image_data: bytes) -> Tuple[str, float, List[Dict[str, Any]]]:
        """Process image bytes and extract text.

        Args:
            image_data: Raw image bytes

        Returns:
            Tuple of (extracted_text, average_confidence, ocr_lines)
        """
        try:
            image = Image.open(BytesIO(image_data))
            image_array = np.array(image)

            # PaddleOCR v2.x uses ocr() method
            result = self.ocr.ocr(image_array, cls=True)
            if result and result[0]:
                result = result[0]

            text_lines, confidences, line_items = self._extract_text_from_result(result)
            line_items = self._sort_lines_by_position(line_items)
            combined_text = "\n".join([line["text"] for line in line_items] or text_lines)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return combined_text, avg_confidence, line_items

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

    def process_pdf(self, pdf_data: bytes) -> Tuple[str, float, List[Dict[str, Any]]]:
        """Process PDF and extract text from all pages.

        First tries to extract embedded text layer (faster, more accurate for digital PDFs),
        then falls back to OCR for scanned PDFs.

        Args:
            pdf_data: Raw PDF bytes

        Returns:
            Tuple of (extracted_text, average_confidence, ocr_lines)
        """
        # First try to extract embedded text layer
        text_layer, has_useful_text = self._extract_pdf_text_layer(pdf_data)

        if has_useful_text:
            logger.info("Using PDF embedded text layer instead of OCR")
            # High confidence for embedded text
            return text_layer, 99.0, []

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
            all_lines: List[Dict[str, Any]] = []

            for image in images:
                image_array = np.array(image)

                # PaddleOCR v2.x uses ocr() method
                result = self.ocr.ocr(image_array, cls=True)
                if result and result[0]:
                    result = result[0]

                text_lines, confidences, line_items = self._extract_text_from_result(result)
                all_text.extend(text_lines)
                all_confidences.extend(confidences)
                all_lines.extend(line_items)

            all_lines = self._sort_lines_by_position(all_lines)
            combined_text = "\n".join([line["text"] for line in all_lines] or all_text)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

            return combined_text, avg_confidence, all_lines

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

    def _find_label_positions(self, text: str) -> Dict[str, list[int]]:
        """Find positions of buyer/seller label markers in text.

        Returns:
            Dictionary with 'buyer' and 'seller' keys, each containing
            list of character positions where labels were found.
        """
        # Define label markers for buyer and seller
        buyer_labels = ['购买方', '购方', '购货单位']
        # Seller labels include contextual markers that only appear in seller section
        seller_labels = ['销售方', '销方', '销货单位', '开票人', '收款人', '复核']

        positions: Dict[str, list[int]] = {'buyer': [], 'seller': []}

        for label in buyer_labels:
            for match in re.finditer(re.escape(label), text):
                positions['buyer'].append(match.start())

        for label in seller_labels:
            for match in re.finditer(re.escape(label), text):
                positions['seller'].append(match.start())

        # Handle vertical text format: 购/买/方 or 销/售/方 (with spaces/newlines)
        vertical_buyer = re.finditer(r'购\s*买\s*方', text)
        for match in vertical_buyer:
            positions['buyer'].append(match.start())

        vertical_seller = re.finditer(r'销\s*售\s*方', text)
        for match in vertical_seller:
            positions['seller'].append(match.start())

        # Handle spaced labels like "购 名称" / "销 名称" and "买 方" / "售 方"
        for match in re.finditer(r'购\s*名\s*称', text):
            positions['buyer'].append(match.start())
        for match in re.finditer(r'销\s*名\s*称', text):
            positions['seller'].append(match.start())
        for match in re.finditer(r'买\s*方', text):
            positions['buyer'].append(match.start())
        for match in re.finditer(r'售\s*方', text):
            positions['seller'].append(match.start())

        return positions

    def _find_label_positions_from_lines(self, lines: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Find buyer/seller label lines using OCR line metadata."""
        buyer_labels = ['购买方', '购方', '购货单位']
        seller_labels = ['销售方', '销方', '销货单位', '开票人', '收款人', '复核']
        buyer_patterns = [
            r'购\s*买\s*方',
            r'购\s*名\s*称',
            r'买\s*方',
        ]
        seller_patterns = [
            r'销\s*售\s*方',
            r'销\s*名\s*称',
            r'售\s*方',
        ]

        positions: Dict[str, List[Dict[str, Any]]] = {'buyer': [], 'seller': []}

        for line in lines:
            text = line.get("text", "")
            if any(label in text for label in buyer_labels) or any(re.search(pat, text) for pat in buyer_patterns):
                positions['buyer'].append(line)
            if any(label in text for label in seller_labels) or any(re.search(pat, text) for pat in seller_patterns):
                positions['seller'].append(line)

        return positions

    def _line_distance(self, line: Dict[str, Any], label_line: Dict[str, Any]) -> float:
        """Calculate weighted distance between a line and a label line."""
        dy = abs(line["center_y"] - label_line["center_y"])
        dx = abs(line["center_x"] - label_line["center_x"])
        return dy + (dx * 0.3)

    def _classify_line_by_labels(self, line: Dict[str, Any], label_lines: Dict[str, List[Dict[str, Any]]]) -> Optional[str]:
        """Classify a line as buyer or seller based on nearest label line."""
        buyer_lines = label_lines.get("buyer", [])
        seller_lines = label_lines.get("seller", [])

        def min_distance(lines: List[Dict[str, Any]]) -> float:
            if not lines:
                return float('inf')
            return min(self._line_distance(line, label) for label in lines)

        buyer_dist = min_distance(buyer_lines)
        seller_dist = min_distance(seller_lines)

        if buyer_dist == float('inf') and seller_dist == float('inf'):
            return None

        max_dist = max(buyer_dist, seller_dist)
        if max_dist and abs(buyer_dist - seller_dist) / max_dist < 0.15:
            return None

        return 'buyer' if buyer_dist < seller_dist else 'seller'

    def _min_label_distance(
        self,
        line: Dict[str, Any],
        label_lines: Dict[str, List[Dict[str, Any]]],
        label_key: str
    ) -> float:
        lines = label_lines.get(label_key, [])
        if not lines:
            return float('inf')
        return min(self._line_distance(line, label) for label in lines)

    def _normalize_line_text(self, text: str) -> str:
        """Normalize OCR line text for matching."""
        return re.sub(r'\s+', '', text or '')

    def _parse_inline_buyer_seller_names(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse buyer/seller names from inline label text."""
        match = re.search(r'购\s*名\s*称[：:]\s*(.+?)\s*销\s*名\s*称[：:]\s*(.+)', text)
        if not match:
            return None, None
        buyer_name = self._clean_chinese_spaces(match.group(1))
        seller_name = self._clean_chinese_spaces(match.group(2))
        return buyer_name, seller_name

    def _find_line_for_value(self, value: str, lines: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the line containing the given value."""
        if not value:
            return None
        normalized_value = self._normalize_line_text(value)
        for line in lines:
            line_text = line.get("text", "")
            if value in line_text:
                return line
            if normalized_value and normalized_value in self._normalize_line_text(line_text):
                return line
        return None

    def _classify_by_proximity(self, item_pos: int, label_positions: Dict[str, list[int]]) -> str:
        """Classify an item as 'buyer' or 'seller' based on nearest label.

        Args:
            item_pos: Character position of the item (company name or tax ID)
            label_positions: Dictionary from _find_label_positions()

        Returns:
            'buyer' or 'seller' based on which label is closer
        """
        def min_distance(positions: list[int]) -> float:
            if not positions:
                return float('inf')
            return min(abs(item_pos - pos) for pos in positions)

        buyer_dist = min_distance(label_positions['buyer'])
        seller_dist = min_distance(label_positions['seller'])

        return 'buyer' if buyer_dist < seller_dist else 'seller'

    def _extract_buyer_seller(self, text: str, lines: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Optional[str]]:
        """Extract buyer and seller info using label proximity.

        Uses context-aware extraction based on proximity to label markers
        (购买方/销售方) rather than relying on match order. This handles
        PaddleOCR's interleaved column reading correctly.

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

        label_positions = self._find_label_positions(text)
        has_labels = bool(label_positions['buyer'] or label_positions['seller'])

        line_labels = None
        if lines:
            line_labels = self._find_label_positions_from_lines(lines)

        if line_labels and line_labels['buyer'] and line_labels['seller']:
            line_result = self._extract_buyer_seller_from_lines(lines, line_labels)
            result.update({k: v for k, v in line_result.items() if v})

        if has_labels:
            text_result = self._extract_buyer_seller_from_text(text, label_positions)
            for key, value in text_result.items():
                if not result.get(key) and value:
                    result[key] = value

        if not all(result.values()):
            fallback = self._extract_buyer_seller_fallback(text)
            for key, value in fallback.items():
                if not result.get(key) and value:
                    result[key] = value

        if line_labels and (line_labels['buyer'] and line_labels['seller']):
            result = self._swap_if_needed(result, lines, line_labels)

        if not has_labels and not (line_labels and (line_labels['buyer'] or line_labels['seller'])):
            logger.info("No buyer/seller labels found, using position-based fallback")

        return result

    def _extract_buyer_seller_from_text(
        self,
        text: str,
        label_positions: Dict[str, list[int]]
    ) -> Dict[str, Optional[str]]:
        """Extract buyer/seller using label proximity in text."""
        result = {
            'buyer_name': None,
            'buyer_tax_id': None,
            'seller_name': None,
            'seller_tax_id': None,
        }

        for line in text.splitlines():
            if '购' in line and '销' in line:
                buyer_name, seller_name = self._parse_inline_buyer_seller_names(line)
                if buyer_name:
                    result['buyer_name'] = buyer_name
                if seller_name:
                    result['seller_name'] = seller_name
                if result['buyer_name'] or result['seller_name']:
                    break

        name_pattern = r'(?:名\s*)?称[：:]\s*(.+)$'
        name_matches = [(m.start(), m.group(1)) for m in re.finditer(name_pattern, text, re.MULTILINE)]

        if name_matches and not (result['buyer_name'] and result['seller_name']):
            buyers = []
            sellers = []

            for pos, name in name_matches:
                classification = self._classify_by_proximity(pos, label_positions)
                cleaned_name = self._clean_chinese_spaces(name)
                if classification == 'buyer':
                    buyers.append(cleaned_name)
                else:
                    sellers.append(cleaned_name)

            if buyers:
                result['buyer_name'] = buyers[0]
            if sellers:
                result['seller_name'] = sellers[0]

            logger.info(f"Label-based extraction: buyer={result['buyer_name']}, seller={result['seller_name']}")

        tax_id_pattern = r'(?:纳税人识别号|统一社会信用代码|税号)[：:]\s*([A-Z0-9]{15,20})'
        if not result['buyer_tax_id'] and not result['seller_tax_id']:
            for line in text.splitlines():
                line_matches = re.findall(tax_id_pattern, line, re.IGNORECASE)
                if len(line_matches) >= 2:
                    result['buyer_tax_id'] = line_matches[0].strip()
                    result['seller_tax_id'] = line_matches[1].strip()
                    break

        tax_matches = [(m.start(), m.group(1)) for m in re.finditer(tax_id_pattern, text, re.IGNORECASE)]

        if tax_matches and not (result['buyer_tax_id'] and result['seller_tax_id']):
            buyer_tax_ids = []
            seller_tax_ids = []

            for pos, tax_id in tax_matches:
                classification = self._classify_by_proximity(pos, label_positions)
                if classification == 'buyer':
                    buyer_tax_ids.append(tax_id.strip())
                else:
                    seller_tax_ids.append(tax_id.strip())

            if buyer_tax_ids:
                result['buyer_tax_id'] = buyer_tax_ids[0]
            if seller_tax_ids:
                result['seller_tax_id'] = seller_tax_ids[0]

        return result

    def _extract_buyer_seller_from_lines(
        self,
        lines: List[Dict[str, Any]],
        label_lines: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Optional[str]]:
        """Extract buyer/seller fields from OCR lines using label proximity."""
        result = {
            'buyer_name': None,
            'buyer_tax_id': None,
            'seller_name': None,
            'seller_tax_id': None,
        }

        buyers: List[Tuple[float, str]] = []
        sellers: List[Tuple[float, str]] = []
        buyer_tax_ids: List[Tuple[float, str]] = []
        seller_tax_ids: List[Tuple[float, str]] = []

        name_pattern = r'(?:名\s*)?称[：:]\s*(.+)$'
        tax_id_pattern = r'(?:纳税人识别号|统一社会信用代码|税号)[：:]\s*([A-Z0-9]{15,20})'

        for line in lines:
            text = line.get("text", "")
            inline_buyer, inline_seller = self._parse_inline_buyer_seller_names(text)
            if inline_buyer or inline_seller:
                if inline_buyer and not result['buyer_name']:
                    result['buyer_name'] = inline_buyer
                if inline_seller and not result['seller_name']:
                    result['seller_name'] = inline_seller
            name_match = re.search(name_pattern, text)
            tax_match = re.search(tax_id_pattern, text, re.IGNORECASE)

            classification = self._classify_line_by_labels(line, label_lines)
            if name_match and classification:
                cleaned_name = self._clean_chinese_spaces(name_match.group(1))
                if classification == 'buyer':
                    buyers.append((self._min_label_distance(line, label_lines, 'buyer'), cleaned_name))
                else:
                    sellers.append((self._min_label_distance(line, label_lines, 'seller'), cleaned_name))

            if tax_match and classification:
                tax_id = tax_match.group(1).strip()
                if classification == 'buyer':
                    buyer_tax_ids.append((self._min_label_distance(line, label_lines, 'buyer'), tax_id))
                else:
                    seller_tax_ids.append((self._min_label_distance(line, label_lines, 'seller'), tax_id))

        if buyers:
            result['buyer_name'] = sorted(buyers, key=lambda x: x[0])[0][1]
        if sellers:
            result['seller_name'] = sorted(sellers, key=lambda x: x[0])[0][1]
        if buyer_tax_ids:
            result['buyer_tax_id'] = sorted(buyer_tax_ids, key=lambda x: x[0])[0][1]
        if seller_tax_ids:
            result['seller_tax_id'] = sorted(seller_tax_ids, key=lambda x: x[0])[0][1]

        return result

    def _swap_if_needed(
        self,
        result: Dict[str, Optional[str]],
        lines: List[Dict[str, Any]],
        label_lines: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Optional[str]]:
        """Swap buyer/seller fields when label proximity indicates reversal."""
        buyer_name = result.get("buyer_name")
        seller_name = result.get("seller_name")

        if buyer_name and seller_name:
            buyer_line = self._find_line_for_value(buyer_name, lines)
            seller_line = self._find_line_for_value(seller_name, lines)
            if buyer_line and seller_line:
                buyer_class = self._classify_line_by_labels(buyer_line, label_lines)
                seller_class = self._classify_line_by_labels(seller_line, label_lines)
                if buyer_class == 'seller' and seller_class == 'buyer':
                    result["buyer_name"], result["seller_name"] = seller_name, buyer_name
                    logger.info("Swapped buyer/seller names based on label proximity")

        buyer_tax = result.get("buyer_tax_id")
        seller_tax = result.get("seller_tax_id")
        if buyer_tax and seller_tax:
            buyer_line = self._find_line_for_value(buyer_tax, lines)
            seller_line = self._find_line_for_value(seller_tax, lines)
            if buyer_line and seller_line:
                buyer_class = self._classify_line_by_labels(buyer_line, label_lines)
                seller_class = self._classify_line_by_labels(seller_line, label_lines)
                if buyer_class == 'seller' and seller_class == 'buyer':
                    result["buyer_tax_id"], result["seller_tax_id"] = seller_tax, buyer_tax
                    logger.info("Swapped buyer/seller tax IDs based on label proximity")

        return result

    def _extract_buyer_seller_fallback(self, text: str) -> Dict[str, Optional[str]]:
        """Fallback position-based extraction when no labels found.

        Uses original logic: first company name = buyer, second = seller.
        """
        result = {
            'buyer_name': None,
            'buyer_tax_id': None,
            'seller_name': None,
            'seller_tax_id': None,
        }

        # Pattern to match company names
        name_pattern = r'(?:名\s*)?称[：:]\s*([^销购\n]*?(?:有限公司|股份公司|集团|公司))'
        name_matches = re.findall(name_pattern, text)

        if len(name_matches) >= 2:
            result['buyer_name'] = self._clean_chinese_spaces(name_matches[0])
            result['seller_name'] = self._clean_chinese_spaces(name_matches[1])
            logger.info(f"Position-based fallback: buyer={result['buyer_name']}, seller={result['seller_name']}")
        elif len(name_matches) == 1:
            cleaned_name = self._clean_chinese_spaces(name_matches[0])
            # Try to determine from context
            if '购' in text[:text.find(name_matches[0])] if name_matches[0] in text else False:
                result['buyer_name'] = cleaned_name
            else:
                result['seller_name'] = cleaned_name

        # Tax IDs - position based
        tax_id_pattern = r'(?:纳税人识别号|统一社会信用代码|税号)[：:]\s*([A-Z0-9]{15,20})'
        tax_matches = re.findall(tax_id_pattern, text, re.IGNORECASE)

        if len(tax_matches) >= 2:
            result['buyer_tax_id'] = tax_matches[0].strip()
            result['seller_tax_id'] = tax_matches[1].strip()
        elif len(tax_matches) == 1:
            if result['buyer_name'] and not result['seller_name']:
                result['buyer_tax_id'] = tax_matches[0].strip()
            elif result['seller_name'] and not result['buyer_name']:
                result['seller_tax_id'] = tax_matches[0].strip()

        # Ultimate fallback: simpler pattern
        if not result['buyer_name'] and not result['seller_name']:
            simple_pattern = r'([^\n]*(?:有限公司|股份公司))'
            simple_matches = re.findall(simple_pattern, text)
            if len(simple_matches) >= 2:
                result['buyer_name'] = self._clean_chinese_spaces(simple_matches[0])
                result['seller_name'] = self._clean_chinese_spaces(simple_matches[1])
                logger.info(f"Ultimate fallback: buyer={result['buyer_name']}, seller={result['seller_name']}")

        return result

    def extract_fields(self, text: str, lines: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Extract all invoice fields from OCR text.

        Args:
            text: OCR extracted text
            lines: OCR line metadata (with bounding boxes)

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
            buyer_seller = self._extract_buyer_seller(text, lines)
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
