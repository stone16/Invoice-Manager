# MVP 探索与定价试验方案（文档处理平台）

## 1) 目标与假设
- H1：物流单据“字段级稳定输出 + 校验 + 审核闭环”能显著降低人工录入成本，并高于单纯 OCR 价值。[Klippa](https://www.klippa.com/en/ocr/logistics-documents/bills-of-lading/) [Nanonets](https://nanonets.com/ocr-api/bill-of-lading-ocr)
- H2：合同审阅场景中，用户愿意为“可解释条款抽取 + 风险提示 + 红线建议”付费，但需要更透明的价格与集成方式。[Luminance Review](https://www.eesel.ai/blog/luminance-ai-review) [Lawgeex](https://www.lawgeex.com/)
- H3：2C 仍存在“复杂版式/手写/低质量扫描可用性差”的痛点，若给到“表格结构化 + 隐私模式 + 低学习成本”，有订阅机会。[r/datacurator](https://www.reddit.com/r/datacurator/comments/11roy7u/ocr_software_that_works/lk58pum/)

## 2) 目标用户与 MVP 切入点
- 2B 物流：货代/清关/仓储运营，痛点是 B/L、Packing List、POD 的字段抽取与对账效率。[Mindee](https://www.mindee.com/blog/bill-of-lading-ocr-api-optimizing-freight-and-logistics-document-management) [Klippa-POD](https://www.klippa.com/en/ocr/logistics-documents/proofs-of-delivery/)
- 2B 法务：法务/法务运营/采购合同审阅人员，痛点是条款抽取与风险识别的稳定性与可解释输出。[Kira](https://www.litera.com/products/kira) [Spellbook](https://www.spellbook.legal/)
- 2C：个人扫描/票据整理/合同阅读，痛点是“能看懂/可用输出”，而非 OCR 字符准确率本身。[r/ios](https://www.reddit.com/r/ios/comments/dhvwvx/best_scanner_app/f3samtp/)

## 3) MVP 形态与范围
**统一入口（2B/2C 共用）**
- 文档上传/导入（Web/Email/API/云盘）。
- 文档分类：B/L、Packing List、POD、合同。
- 字段抽取：标准 schema + 低置信度高亮。
- 校验规则：跨字段一致性（件数/重量/日期）、格式校验（港口/货币/地址）。
- 审核台：一键确认/修正，自动回写并记录审计。
- 导出：JSON/CSV/XLSX + Webhook（对接 ERP/WMS/TMS/CLM）。

**范围内（优先）**
- 物流三类文档（B/L、Packing List、POD）。
- 合同：关键条款抽取 + 风险提示（不做完整 CLM）。

**范围外（先不做）**
- 全量 CLM（审批/签署/存证）与深度电子签生态。
- 复杂 RPA 流程编排与多系统流程管理。

## 4) 核心 Schema（最小字段包）
- **B/L**：B/L 号、托运人、收货人、承运人、装/卸港、集装箱号、件数/重量/体积、货物描述、日期。
- **Packing List**：PO/订单号、SKU/品名、数量/单位、箱数、重量/体积、港口、运输方式。
- **POD**：运单号、收件人、签名、时间戳、地址、件数、异常标记。
- **合同**：双方主体、期限、终止条款、付款条款、责任上限、适用法、保密条款。

## 5) 质量与反馈闭环
- 引入“文档质量评分”，低于阈值提示重拍/重传。
- 用“字段置信度 + 规则校验”驱动人工审核优先级。
- 建立“错例回流”机制，仅标注错例即可持续提升模板/模型。

## 6) 认证/计费最小闭环（与产品耦合）
- 账号体系：项目/团队与 API Key；支持多租户隔离。
- 计费维度实验：按文档数/页数/字段数；结合“审核席位”溢价。
- 审计与账单：每次抽取记录字段、置信度与成本，便于用户对账。

## 7) 定价试验设计（探索性）
**2B（物流/法务）**
- A 组：按文档计费（基础价 + 行项目溢价）。
- B 组：按字段计费（关键字段更高权重）。
- C 组：按团队席位 + 免费额度（绑定审核台与权限管理）。

**2C**
- 订阅制 vs 点数包：
  - 订阅：月度处理上限 + 隐私模式。
  - 点数包：按文档/页数扣点，避免订阅疲劳。

## 8) 验证节奏（6 周节拍）
1. Week 1-2：Landing + 需求访谈（物流/法务各 5-8 人），确定字段优先级。
2. Week 2-3：MVP 原型（上传→抽取→审核→导出），用真实样本跑通。
3. Week 3-4：小规模 Beta（3-5 家客户），建立准确率与审核时长基线。
4. Week 5-6：定价 AB 测试与留存验证，确定首个商业化包。

## 9) 主要风险与应对
- **准确率不稳定**：通过规则校验 + 审核台 + 错例回流缓冲。
- **模板多样性**：提供模板继承与“同类模板聚合”降低维护成本。
- **合规与数据安全**：默认不留存 + 私有化选项 + 审计日志。
- **价格敏感**：提供低门槛试用 + 透明计费试验，避免黑箱定价引发流失。

