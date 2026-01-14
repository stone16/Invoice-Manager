import json

from app.services.llm_service import LLMService


def test_llm_response_normalization():
    content = json.dumps({
        "invoice_number": " 25952000000233223073 ",
        "invoice_code": "1234-5678-9012",
        "issue_date": "2025年11月05日",
        "buyer_name": "示例买方科技有限公司",
        "buyer_tax_id": " 123456789012345 ",
        "seller_name": "示例卖方服务有限公司",
        "seller_tax_id": "ABCD1234567890123",
        "item_name": "服务费",
        "total_with_tax": "¥8,600.00",
        "amount": "8600.00",
        "tax_amount": "0",
        "tax_rate": "免税",
    })

    service = LLMService()
    fields = service._parse_json_response(content, "test")

    assert fields["invoice_number"] == "25952000000233223073"
    assert fields["invoice_code"] == "123456789012"
    assert fields["issue_date"] == "2025-11-05"
    assert fields["buyer_tax_id"] == "123456789012345"
    assert fields["seller_tax_id"] == "ABCD1234567890123"
    assert fields["total_with_tax"] == "8600.00"
    assert fields["tax_rate"] == "免税"


def test_llm_response_invalid_fields_to_none():
    content = json.dumps({
        "invoice_number": "ABC",
        "invoice_code": "INVALID",
        "issue_date": "2025/11/05",
        "buyer_name": "示例买方科技有限公司",
        "buyer_tax_id": "123",
        "seller_name": "示例卖方服务有限公司",
        "seller_tax_id": "SELLERID",
        "item_name": "服务费",
        "total_with_tax": "not-a-number",
        "amount": "",
        "tax_amount": None,
        "tax_rate": "6 %",
    })

    service = LLMService()
    fields = service._parse_json_response(content, "test")

    assert fields["invoice_number"] is None
    assert fields["invoice_code"] is None
    assert fields["issue_date"] == "2025-11-05"
    assert fields["buyer_tax_id"] is None
    assert fields["seller_tax_id"] is None
    assert fields["total_with_tax"] is None
    assert fields["amount"] is None
    assert fields["tax_amount"] is None
    assert fields["tax_rate"] is None
