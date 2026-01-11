# 物流单据与合同审阅竞品深拆

## 范围与来源
- 物流单据：B/L（提单）、Packing List、POD 等，聚焦字段抽取、输出格式、集成与合规。
- 合同审阅/CLM：合同审查、CLM、Word 内审阅、合同 AI 工具，关注部署、安全、价格与集成能力。
- 说明：已补抓 Mindee B/L 新产品页、Docsumo B/L 替代页面与 Lawgeex 聚合页；Docsumo Packing List 仍缺公开页面。

## 物流单据赛道

### 典型字段与输出模式（跨厂商共性）
- B/L：提单号、承运人、托运人/收货人、货物描述、集装箱号、装卸港、运输日期、重量/件数等。[Mindee](https://www.mindee.com/blog/bill-of-lading-ocr-api-optimizing-freight-and-logistics-document-management) [Nanonets](https://nanonets.com/ocr-api/bill-of-lading-ocr) [Klippa](https://www.klippa.com/en/ocr/logistics-documents/bills-of-lading/)
- Packing List：PO/订单号、品名/SKU、数量/单位、箱数、重量体积、港口/运输类型等。[Nanonets](https://nanonets.com/document-ocr/packing-list) [Klippa](https://www.klippa.com/en/ocr/logistics-documents/packing-lists/)
- POD：签收人、地址、时间戳、件数、签名等。[Klippa](https://www.klippa.com/en/ocr/logistics-documents/proofs-of-delivery/) [OmniAI](https://getomni.ai/documents/proof-of-delivery)
- 输出：JSON/XML/CSV/XLSX 为主，普遍提供 API/SDK 或低代码集成入口。[Klippa](https://www.klippa.com/en/ocr/ocr-api/) [Nanonets](https://docs.nanonets.com/reference/overview)

### 物流竞品矩阵（摘要）
| 厂商/来源 | 文档类型 | 输出/集成 | 部署/合规 | 备注 |
| --- | --- | --- | --- | --- |
| Klippa | B/L, Packing List, POD 等物流文档 | JSON/XML/CSV/XLSX，API/SDK/低代码 | EU ISO 认证服务器、DPA、数据不留存声明 | 强调多文档覆盖与集成生态。[B/L](https://www.klippa.com/en/ocr/logistics-documents/bills-of-lading/) [POD](https://www.klippa.com/en/ocr/logistics-documents/proofs-of-delivery/)
| Mindee | B/L | JSON（试用展示），API 集成 | SaaS + 自托管 | 免费计划 250 份/月，按量计费；强调隐私优先。[Mindee](https://www.mindee.com/product/bill-of-lading-ocr-api)
| Docsumo | B/L | 校验+人审，导入多源 | 未披露 | 14 天试用；案例称每月节省 500+ 小时、>95% 直通率。[Docsumo](https://www.docsumo.com/blogs/data-extraction/from-bill-of-lading)
| Nanonets | B/L、Packing List | JSON，API 文档完善 | 未披露 | 强调导入/审阅/导出链路。[B/L](https://nanonets.com/ocr-api/bill-of-lading-ocr) [Packing](https://nanonets.com/document-ocr/packing-list)
| Veryfi | BOL/报关/货运单据 | REST API + 多语言 SDK | SOC2 Type2、GDPR/HIPAA/CCPA | 主打预训练 BOL 模型与行项目抽取。[Veryfi](https://www.veryfi.com/ocr-api-platform/freight-customs-documents-automation/)
| Unstract | 物流多文档 | JSON/API/ETL，Prompt Studio | 未披露 | LLMWhisperer 强调预处理与结构化输出。[Unstract](https://unstract.com/blog/document-processing-in-logistics/)
| KlearStack | 物流多文档 | ERP/WMS/TMS 集成 | 云端描述为主 | 强调规则校验与自动分类。[KlearStack](https://klearstack.com/ocr-in-logistics)
| HyperVerge | 物流多文档 | API-first，系统集成 | 合规徽章（SOC2/GDPR） | 更多为综述与能力主张。[HyperVerge](https://hyperverge.co/blog/ai-ocr-in-logistics-automation/)
| OmniAI | POD | 单一 API 端点 | SOC2 Type II | 主打 POD 字段抽取与 Excel/Sheets 导出。[OmniAI](https://getomni.ai/documents/proof-of-delivery)

### 物流赛道差距与机会
- **字段校验与业务规则缺口**：多数厂商强调抽取，但对“字段一致性/跨文档校验”叙述较少；这正是物流对账痛点。
- **模板迁移成本**：跨承运人/港口模板变化频繁，缺少“模板继承/迁移”机制。
- **POD 证据链**：签名/时间戳/照片等证据链校验与争议处理流程在宣传中不够细化。

## 合同审阅/CLM 赛道

### 形态分层
- **CLM 平台**：Icertis、Ironclad、Evisort 等，强调端到端生命周期与系统集成。[Icertis](https://www.icertis.com/) [Ironclad](https://ironcladapp.com/product/ai-based-contract-management)
- **审阅/尽调型工具**：Kira、Luminance、Lawgeex 等，强调条款识别、风险标注与 Word 集成。[Kira](https://www.litera.com/products/kira) [Luminance](https://www.luminance.com/m-ai-contract-review-software/) [Lawgeex](https://www.lawgeex.com/)
- **轻量化/邮件摘要型**：ContractCrab 等，强调上传→摘要→邮件交付。[ContractCrab](https://contractcrab.com/ai-contract-review/)

### 合同竞品矩阵（摘要）
| 厂商/来源 | 形态 | 输出/集成 | 部署/合规 | 价格线索 |
| --- | --- | --- | --- | --- |
| Kira (Litera) | 审阅/尽调 | 1,400+ 条款抽取，摘要/带引用问答 | 未公开部署细节 | Demo；GenAI 包含在订阅。[Kira](https://www.litera.com/products/kira)
| Luminance | 审阅/CLM | 条款识别+Word 集成 | 云/私有化，ISO27001/SOC2 | Demo，无公开价。[Luminance](https://www.luminance.com/m-ai-contract-review-software/)
| Lawgeex | 审阅自动化 | 数字化 playbook/风险等级 | 安全页需核验 | Demo；Forrester 报告背书，SaaSHub 侧强调效率与一致性。[Lawgeex](https://www.lawgeex.com/) [SaaSHub](https://www.saashub.com/lawgeex)
| Evisort | CLM | AI‑native CLM，合同数据智能 | 未公开部署细节 | Demo，无公开价。[Evisort](https://www.evisort.com/)
| LinkSquares | CLM | 生态集成+开放 API | 未公开部署细节 | 4.7/300+ reviews 标注，价未公开。[LinkSquares](https://linksquares.com/)
| Ironclad | CLM | 公共 API 与流程自动化 | SOC2 Type II | Demo 无公开价。[Ironclad](https://ironcladapp.com/product/ai-based-contract-management)
| Icertis | CLM | 合同智能+系统集成 | 未公开部署细节 | 需联系销售。[Icertis](https://www.icertis.com/)
| ContractPodAI/Leah | CLM/Agentic AI | 集成与安全合规强调 | SOC1/2、GDPR/CCPA | Demo 无公开价。[ContractPodAI](https://www.contractpodai.com/)
| Juro | 合同平台 | REST API + ChatGPT 集成 | Trust center 需核验 | 价格未公开。[Juro](https://juro.com/)
| Spellbook | Word 内审阅 | Review/Draft/Ask/Benchmarks | SOC2 Type II、HIPAA | 7 天试用，Custom pricing。[Spellbook](https://www.spellbook.legal/)
| e签宝 | 电子签/合同 | OpenAPI，对接签署 | 私有化表述存在 | 价未公开。[e签宝](https://www.esign.cn/)
| 法大大 | 电子合同 | 开放接口+存证 | SaaS + 合规要素 | 价未公开。[法大大](https://www.fadada.com/)
| 契约锁 | 电子签/存档 | API/SDK/沙箱 | 合规强调 | 免费试用线索。[契约锁](https://www.qiyuesuo.com/)
| Eesel Luminance Review | 评测 | Word 插件为核心 | 未披露 | 指出定价不透明、学习曲线等。[Eesel](https://www.eesel.ai/blog/luminance-ai-review)
| Signeasy 评测 | 榜单/评测 | OCR+NLP+条款抽取 | 私有服务器/加密 | $20/用户/月（文中提及）。[Signeasy](https://signeasy.com/blog/business/ai-contract-review-software)
| ContractCrab | 轻量审阅 | 上传→摘要→邮件 | 在线工具 | $3/份 或 $30/月。[ContractCrab](https://contractcrab.com/ai-contract-review/)

### 合同赛道差距与机会
- **价格透明度低**：多数 CLM/审阅平台不公开价格，采购决策成本高。[Luminance Review](https://www.eesel.ai/blog/luminance-ai-review)
- **集成细节不透明**：厂商普遍宣称“集成”但缺少技术细节与可复用连接器。
- **合同字段结构与输出标准缺乏**：条款抽取的 schema 规范不统一，难以跨系统互通。
- **中文场景“智能审查”深度不足**：国内平台更强调签署与管理，缺乏公开的条款抽取与风险识别指标。[e签宝](https://www.esign.cn/) [法大大](https://www.fadada.com/)

## 限制与待验证
- Docsumo Packing List 仍未找到公开页面；需通过站内搜索或销售资料补齐字段与输出说明。[Docsumo](https://www.docsumo.com/solutions/documents/bill-of-lading)
- Eesel Lawgeex review 404，已用 SaaSHub/SoftwareSuggest 聚合页补充，但缺少深度用户评价文本。[SaaSHub](https://www.saashub.com/lawgeex) [SoftwareSuggest](https://www.softwaresuggest.com/lawgeex/reviews)
