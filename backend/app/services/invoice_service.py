"""Invoice processing service."""

import logging
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.invoice import Invoice, OcrResult, LlmResult, ParsingDiff, InvoiceStatus
from app.services.ocr_service import get_ocr_service, get_field_extractor
from app.services.llm_service import get_llm_service
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Fields to compare between OCR and LLM
COMPARABLE_FIELDS = [
    'invoice_number',
    'issue_date',
    'buyer_name',
    'buyer_tax_id',
    'seller_name',
    'seller_tax_id',
    'item_name',
    'total_with_tax',
    'amount',
    'tax_amount',
    'tax_rate',
]


async def process_invoice(invoice_id: int, db: AsyncSession) -> bool:
    """Process an invoice: run OCR, optionally LLM, and compare results.

    Args:
        invoice_id: ID of the invoice to process
        db: Database session

    Returns:
        True if processing succeeded, False otherwise
    """
    try:
        # Get invoice
        query = select(Invoice).where(Invoice.id == invoice_id)
        result = await db.execute(query)
        invoice = result.scalar_one_or_none()

        if not invoice:
            logger.error(f"Invoice {invoice_id} not found")
            return False

        # Run OCR
        ocr_service = get_ocr_service()
        extractor = get_field_extractor()

        if invoice.file_type == 'pdf':
            raw_text, confidence = ocr_service.process_pdf(invoice.file_data)
        else:
            raw_text, confidence = ocr_service.process_image(invoice.file_data)

        # Extract fields from OCR
        ocr_fields = extractor.extract_fields(raw_text)

        # Save OCR result
        ocr_result = OcrResult(
            invoice_id=invoice_id,
            raw_text=raw_text,
            invoice_number=ocr_fields.get('invoice_number'),
            issue_date=ocr_fields.get('issue_date'),
            buyer_name=ocr_fields.get('buyer_name'),
            buyer_tax_id=ocr_fields.get('buyer_tax_id'),
            seller_name=ocr_fields.get('seller_name'),
            seller_tax_id=ocr_fields.get('seller_tax_id'),
            item_name=ocr_fields.get('item_name'),
            total_with_tax=ocr_fields.get('total_with_tax'),
            amount=ocr_fields.get('amount'),
            tax_amount=ocr_fields.get('tax_amount'),
            tax_rate=ocr_fields.get('tax_rate'),
        )
        db.add(ocr_result)

        # Run LLM parsing if available
        llm_service = get_llm_service()
        llm_fields = {}
        has_llm = False

        if llm_service.is_available:
            logger.info(f"Running LLM parsing for invoice {invoice_id}")
            llm_fields = llm_service.parse_invoice(raw_text)
            has_llm = bool(llm_fields)

            if has_llm:
                # Save LLM result
                llm_result = LlmResult(
                    invoice_id=invoice_id,
                    invoice_number=llm_fields.get('invoice_number'),
                    issue_date=llm_fields.get('issue_date'),
                    buyer_name=llm_fields.get('buyer_name'),
                    buyer_tax_id=llm_fields.get('buyer_tax_id'),
                    seller_name=llm_fields.get('seller_name'),
                    seller_tax_id=llm_fields.get('seller_tax_id'),
                    item_name=llm_fields.get('item_name'),
                    total_with_tax=llm_fields.get('total_with_tax'),
                    amount=llm_fields.get('amount'),
                    tax_amount=llm_fields.get('tax_amount'),
                    tax_rate=llm_fields.get('tax_rate'),
                )
                db.add(llm_result)
        else:
            logger.info(f"LLM service not available, using OCR results only")

        # Compare OCR and LLM results, create diffs
        final_fields, diffs = _compare_and_resolve(ocr_fields, llm_fields, has_llm)

        # Save parsing diffs
        for diff in diffs:
            parsing_diff = ParsingDiff(
                invoice_id=invoice_id,
                field_name=diff['field_name'],
                ocr_value=diff['ocr_value'],
                llm_value=diff['llm_value'],
                final_value=diff['final_value'],
                source=diff['source'],
                resolved=0 if diff['needs_review'] else 1,
            )
            db.add(parsing_diff)

        # Update invoice with final data
        _update_invoice_from_fields(invoice, final_fields)

        # Set status based on whether review is needed
        # Check for conflicts in diffs
        has_conflicts = any(d['needs_review'] for d in diffs)

        # Check for missing critical fields (these require review)
        critical_fields = ['invoice_number', 'issue_date', 'total_with_tax', 'seller_name']
        missing_critical = any(not final_fields.get(f) for f in critical_fields)

        needs_review = has_conflicts or missing_critical
        if needs_review:
            invoice.status = InvoiceStatus.REVIEWING
        else:
            invoice.status = InvoiceStatus.CONFIRMED

        await db.commit()
        logger.info(f"Invoice {invoice_id} processed successfully (needs_review={needs_review})")
        return True

    except Exception as e:
        logger.error(f"Failed to process invoice {invoice_id}: {e}")
        await db.rollback()
        return False


def _compare_and_resolve(
    ocr_fields: Dict[str, Any],
    llm_fields: Dict[str, Any],
    has_llm: bool
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Compare OCR and LLM results, resolve differences.

    Args:
        ocr_fields: Fields extracted by OCR
        llm_fields: Fields extracted by LLM
        has_llm: Whether LLM results are available

    Returns:
        Tuple of (final_fields, diffs_list)
    """
    final_fields = {}
    diffs = []

    for field_name in COMPARABLE_FIELDS:
        ocr_value = _normalize_value(ocr_fields.get(field_name))
        llm_value = _normalize_value(llm_fields.get(field_name)) if has_llm else None

        # Determine final value and whether review is needed
        if not has_llm:
            # No LLM available, use OCR value directly
            final_value = ocr_value
            source = 'ocr'
            needs_review = False
        elif ocr_value == llm_value:
            # Values match, no conflict
            final_value = ocr_value or llm_value
            source = 'matched'
            needs_review = False
        elif ocr_value and llm_value:
            # Both have values but they differ - needs manual review
            final_value = None  # Leave blank for manual review
            source = 'conflict'
            needs_review = True
        elif llm_value and not ocr_value:
            # LLM found something OCR missed - prefer LLM
            final_value = llm_value
            source = 'llm'
            needs_review = False
        else:
            # OCR found something LLM missed - prefer OCR
            final_value = ocr_value
            source = 'ocr'
            needs_review = False

        final_fields[field_name] = final_value

        # Record diff if there's a discrepancy or both have values
        if has_llm and (ocr_value or llm_value):
            diffs.append({
                'field_name': field_name,
                'ocr_value': ocr_value,
                'llm_value': llm_value,
                'final_value': final_value,
                'source': source,
                'needs_review': needs_review,
            })

    return final_fields, diffs


def _normalize_value(value: Any) -> Optional[str]:
    """Normalize a value to string for comparison."""
    if value is None:
        return None
    value_str = str(value).strip()
    if not value_str:
        return None
    return value_str


def _update_invoice_from_fields(invoice: Invoice, fields: dict) -> None:
    """Update invoice fields from extracted data."""
    from datetime import datetime
    from decimal import Decimal

    if fields.get('invoice_number'):
        invoice.invoice_number = fields['invoice_number']

    if fields.get('issue_date'):
        try:
            invoice.issue_date = datetime.strptime(fields['issue_date'], '%Y-%m-%d').date()
        except ValueError:
            pass

    if fields.get('buyer_name'):
        invoice.buyer_name = fields['buyer_name']

    if fields.get('buyer_tax_id'):
        invoice.buyer_tax_id = fields['buyer_tax_id']

    if fields.get('seller_name'):
        invoice.seller_name = fields['seller_name']

    if fields.get('seller_tax_id'):
        invoice.seller_tax_id = fields['seller_tax_id']

    if fields.get('item_name'):
        invoice.item_name = fields['item_name']

    if fields.get('total_with_tax'):
        try:
            invoice.total_with_tax = Decimal(fields['total_with_tax'])
        except (ValueError, TypeError):
            pass

    if fields.get('amount'):
        try:
            invoice.amount = Decimal(fields['amount'])
        except (ValueError, TypeError):
            pass

    if fields.get('tax_amount'):
        try:
            invoice.tax_amount = Decimal(fields['tax_amount'])
        except (ValueError, TypeError):
            pass

    if fields.get('tax_rate'):
        invoice.tax_rate = fields['tax_rate']


def check_llm_available() -> bool:
    """Check if LLM service is available."""
    return get_llm_service().is_available
