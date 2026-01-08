"""Default schema definitions for common document types."""

from __future__ import annotations

from typing import Any, Dict


def get_chinese_invoice_schema() -> Dict[str, Any]:
    """Return the default Chinese invoice JSON schema.

    This schema covers standard Chinese VAT invoice fields with
    data_source tracking for field-level lineage.
    """
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Chinese Invoice Schema",
        "description": "Schema for Chinese VAT invoice data extraction",
        "type": "object",
        "properties": {
            "invoice_number": {
                "type": "string",
                "description": "发票号码 - Invoice number",
            },
            "invoice_code": {
                "type": "string",
                "description": "发票代码 - Invoice code",
            },
            "issue_date": {
                "type": "string",
                "format": "date",
                "description": "开票日期 - Issue date (YYYY-MM-DD)",
            },
            "buyer_name": {
                "type": "string",
                "description": "购买方名称 - Buyer name",
            },
            "buyer_tax_id": {
                "type": "string",
                "description": "购买方纳税人识别号 - Buyer tax ID",
            },
            "buyer_address_phone": {
                "type": "string",
                "description": "购买方地址电话 - Buyer address and phone",
            },
            "buyer_bank_account": {
                "type": "string",
                "description": "购买方开户行及账号 - Buyer bank account",
            },
            "seller_name": {
                "type": "string",
                "description": "销售方名称 - Seller name",
            },
            "seller_tax_id": {
                "type": "string",
                "description": "销售方纳税人识别号 - Seller tax ID",
            },
            "seller_address_phone": {
                "type": "string",
                "description": "销售方地址电话 - Seller address and phone",
            },
            "seller_bank_account": {
                "type": "string",
                "description": "销售方开户行及账号 - Seller bank account",
            },
            "items": {
                "type": "array",
                "description": "项目明细 - Line items",
                "items": {
                    "type": "object",
                    "properties": {
                        "item_name": {
                            "type": "string",
                            "description": "项目名称 - Item name",
                        },
                        "specification": {
                            "type": "string",
                            "description": "规格型号 - Specification",
                        },
                        "unit": {
                            "type": "string",
                            "description": "单位 - Unit",
                        },
                        "quantity": {
                            "type": "number",
                            "description": "数量 - Quantity",
                        },
                        "unit_price": {
                            "type": "number",
                            "description": "单价 - Unit price",
                        },
                        "amount": {
                            "type": "number",
                            "description": "金额 - Amount (without tax)",
                        },
                        "tax_rate": {
                            "type": "string",
                            "description": "税率 - Tax rate",
                        },
                        "tax_amount": {
                            "type": "number",
                            "description": "税额 - Tax amount",
                        },
                    },
                },
            },
            "total_amount": {
                "type": "number",
                "description": "合计金额 - Total amount (without tax)",
            },
            "total_tax": {
                "type": "number",
                "description": "合计税额 - Total tax",
            },
            "total_with_tax": {
                "type": "number",
                "description": "价税合计 - Total with tax",
            },
            "total_with_tax_cn": {
                "type": "string",
                "description": "价税合计（大写） - Total with tax in Chinese",
            },
            "remarks": {
                "type": "string",
                "description": "备注 - Remarks",
            },
            "payee": {
                "type": "string",
                "description": "收款人 - Payee",
            },
            "reviewer": {
                "type": "string",
                "description": "复核 - Reviewer",
            },
            "drawer": {
                "type": "string",
                "description": "开票人 - Drawer",
            },
        },
        "required": ["invoice_number", "issue_date", "seller_name", "total_with_tax"],
    }


def get_chinese_invoice_yaml() -> str:
    """Return the default Chinese invoice schema as YAML."""
    return '''
$schema: "http://json-schema.org/draft-07/schema#"
title: Chinese Invoice Schema
description: Schema for Chinese VAT invoice data extraction
type: object
properties:
  invoice_number:
    type: string
    description: "发票号码 - Invoice number"
  invoice_code:
    type: string
    description: "发票代码 - Invoice code"
  issue_date:
    type: string
    format: date
    description: "开票日期 - Issue date (YYYY-MM-DD)"
  buyer_name:
    type: string
    description: "购买方名称 - Buyer name"
  buyer_tax_id:
    type: string
    description: "购买方纳税人识别号 - Buyer tax ID"
  buyer_address_phone:
    type: string
    description: "购买方地址电话 - Buyer address and phone"
  buyer_bank_account:
    type: string
    description: "购买方开户行及账号 - Buyer bank account"
  seller_name:
    type: string
    description: "销售方名称 - Seller name"
  seller_tax_id:
    type: string
    description: "销售方纳税人识别号 - Seller tax ID"
  seller_address_phone:
    type: string
    description: "销售方地址电话 - Seller address and phone"
  seller_bank_account:
    type: string
    description: "销售方开户行及账号 - Seller bank account"
  items:
    type: array
    description: "项目明细 - Line items"
    items:
      type: object
      properties:
        item_name:
          type: string
          description: "项目名称 - Item name"
        specification:
          type: string
          description: "规格型号 - Specification"
        unit:
          type: string
          description: "单位 - Unit"
        quantity:
          type: number
          description: "数量 - Quantity"
        unit_price:
          type: number
          description: "单价 - Unit price"
        amount:
          type: number
          description: "金额 - Amount (without tax)"
        tax_rate:
          type: string
          description: "税率 - Tax rate"
        tax_amount:
          type: number
          description: "税额 - Tax amount"
  total_amount:
    type: number
    description: "合计金额 - Total amount (without tax)"
  total_tax:
    type: number
    description: "合计税额 - Total tax"
  total_with_tax:
    type: number
    description: "价税合计 - Total with tax"
  total_with_tax_cn:
    type: string
    description: "价税合计（大写） - Total with tax in Chinese"
  remarks:
    type: string
    description: "备注 - Remarks"
  payee:
    type: string
    description: "收款人 - Payee"
  reviewer:
    type: string
    description: "复核 - Reviewer"
  drawer:
    type: string
    description: "开票人 - Drawer"
required:
  - invoice_number
  - issue_date
  - seller_name
  - total_with_tax
'''.strip()
