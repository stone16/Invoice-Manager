"""Prompts for LLM-based invoice parsing."""

# Vision-based system prompt (for direct image analysis)
INVOICE_VISION_SYSTEM_PROMPT = "你是一个专业的中国发票信息提取助手。请直接分析发票图片，提取关键信息，只返回JSON格式的结果。"

# Vision-based extraction prompt (for direct image analysis)
INVOICE_VISION_PROMPT = """请直接分析这张中国发票图片，提取以下字段信息。

请以JSON格式返回以下字段（如果无法识别则返回null）：
- invoice_number: 发票号码
- invoice_code: 发票代码（如有）
- issue_date: 开票日期（格式：YYYY-MM-DD）
- buyer_name: 购买方名称
- buyer_tax_id: 购买方纳税人识别号
- seller_name: 销售方名称
- seller_tax_id: 销售方纳税人识别号
- item_name: 项目名称/货物名称
- total_with_tax: 价税合计金额（纯数字，不含货币符号）
- amount: 金额/不含税金额（纯数字）
- tax_amount: 税额（纯数字）
- tax_rate: 税率（如：6%、13%、免税）

【最重要】购买方与销售方的识别规则（必须严格遵守）：

1. 识别依据是标签文字，不是位置：
   - 购买方（Buyer）= 标注为"购买方"、"购方"、"购货单位"、或竖排的"购/买/方"的区域
   - 销售方（Seller）= 标注为"销售方"、"销方"、"销货单位"、或竖排的"销/售/方"的区域

2. 中国发票有多种格式：
   - 标准增值税发票：购买方在左上，销售方在左下（同一列）
   - 电子普通发票（深圳等地）：购买方在上部，销售方在底部（价税合计下方）
   - 全电发票：购买方和销售方可能左右并排

3. 关键判断技巧：
   - 找到"购"字或"购买方"标签 → 该区域的公司名称和税号属于购买方
   - 找到"销"字或"销售方"标签 → 该区域的公司名称和税号属于销售方
   - 销售方区域通常还有"开票人"、"收款人"、"复核"等字样
   - 不要被位置迷惑，请以标签为准

其他注意事项：
1. 金额字段只返回数字，不要包含¥、￥、$等符号
2. 日期统一转换为YYYY-MM-DD格式
3. 如果是免税发票，tax_rate返回"免税"，tax_amount返回"0"
4. 纳税人识别号通常为15-20位的数字字母组合

请只返回JSON对象，不要包含其他文字说明。"""
