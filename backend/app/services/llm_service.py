"""LLM-based invoice parsing service using OpenAI."""

import json
import logging
from typing import Optional, Dict, Any

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Invoice field extraction prompt
INVOICE_EXTRACTION_PROMPT = """你是一个专业的发票信息提取助手。请从以下OCR识别的发票文本中提取关键信息。

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

注意：
1. 金额字段只返回数字，不要包含¥、￥、$等符号
2. 日期统一转换为YYYY-MM-DD格式
3. 如果是免税发票，tax_rate返回"免税"，tax_amount返回"0"
4. 请仔细区分购买方和销售方

OCR识别文本：
{ocr_text}

请只返回JSON对象，不要包含其他文字说明。"""


class LLMService:
    """Handles LLM-based invoice parsing using OpenAI."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    @property
    def is_available(self) -> bool:
        """Check if LLM service is available (API key configured)."""
        return bool(settings.openai_api_key)

    def parse_invoice(self, ocr_text: str) -> Dict[str, Any]:
        """Parse invoice text using LLM.

        Args:
            ocr_text: OCR extracted text from invoice

        Returns:
            Dictionary of extracted fields
        """
        if not self.is_available:
            logger.warning("OpenAI API key not configured, skipping LLM parsing")
            return {}

        try:
            prompt = INVOICE_EXTRACTION_PROMPT.format(ocr_text=ocr_text)

            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "你是一个专业的发票信息提取助手，只返回JSON格式的结果。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000,
            )

            content = response.choices[0].message.content.strip()

            # Try to extract JSON from response
            if content.startswith("```"):
                # Remove markdown code blocks
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            fields = json.loads(content)
            logger.info(f"LLM extracted fields: {list(fields.keys())}")
            return fields

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            return {}


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
