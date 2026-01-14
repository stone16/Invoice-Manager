from app.services.ocr_service import FieldExtractor


def _line(text: str, x: float, y: float, width: float = 200, height: float = 12) -> dict:
    return {
        "text": text,
        "min_x": x,
        "max_x": x + width,
        "min_y": y,
        "max_y": y + height,
        "center_x": x + width / 2,
        "center_y": y + height / 2,
    }


def test_extract_buyer_seller_spaced_labels_text():
    text = (
        "电子发票（普通发票）\n"
        "发票号码：25952000000233223073\n"
        "开票日期：2025年11月05日\n"
        "购 名称：示例买方科技有限公司 销 名称：示例卖方服务有限公司分公司\n"
        "买 售\n"
        "方 方\n"
        "信 统一社会信用代码/纳税人识别号：123456789012345 "
        "信 统一社会信用代码/纳税人识别号：987654321098765432\n"
    )

    extractor = FieldExtractor()
    fields = extractor.extract_fields(text)

    assert fields["buyer_name"] == "示例买方科技有限公司"
    assert fields["seller_name"] == "示例卖方服务有限公司分公司"
    assert fields["buyer_tax_id"] == "123456789012345"
    assert fields["seller_tax_id"] == "987654321098765432"


def test_extract_buyer_seller_spaced_labels_lines():
    lines = [
        _line("购 名称：示例买方科技有限公司", x=10, y=10),
        _line("统一社会信用代码/纳税人识别号：123456789012345", x=10, y=24),
        _line("销 名称：示例卖方服务有限公司分公司", x=10, y=60),
        _line("统一社会信用代码/纳税人识别号：987654321098765432", x=10, y=74),
    ]
    text = "\n".join(line["text"] for line in lines)

    extractor = FieldExtractor()
    fields = extractor.extract_fields(text, lines)

    assert fields["buyer_name"] == "示例买方科技有限公司"
    assert fields["seller_name"] == "示例卖方服务有限公司分公司"
    assert fields["buyer_tax_id"] == "123456789012345"
    assert fields["seller_tax_id"] == "987654321098765432"
