# Invoice Manager UI Redesign

## Design Overview

This document describes the redesigned UI/UX for the Invoice Manager application, created using Pencil design tool.

## Design System

**Style Guide**: Swiss Clean Web Dashboard
- **Typography**: Space Grotesk (headings), Inter (body)
- **Color Palette**:
  - Primary Red: `#E42313` (brand accent)
  - Black: `#0D0D0D` (primary text)
  - Muted: `#7A7A7A` (secondary text)
  - Background: `#FFFFFF` / `#FAFAFA`
  - Border: `#E8E8E8`
  - Success: `#22C55E` / `#16A34A`
  - Warning: `#F59E0B` / `#D97706`
  - Error: `#EF4444` / `#DC2626`
- **Corner Radius**: 0-8px (minimal)
- **Borders**: 1px solid, clean separation

## Pages Designed

### 1. Invoice List Page (`FiWE2`)

**Layout**: Sidebar (240px) + Main Content

**Components**:
- **Sidebar**: Logo, navigation (发票列表, 上传发票, 设置), user profile
- **Header**: Page title "发票列表" with export and upload buttons
- **Metrics Cards**: 4 cards showing key statistics
  - 发票数量 (Invoice Count): 20
  - 金额合计 (Total Amount): ¥11,438.99
  - 税额合计 (Total Tax): ¥371.31
  - 价税合计 (Total with Tax): ¥11,810.30
- **Control Bar**: Search input, status filter, date filter
- **Data Table**: Columns for invoice number, date, seller, item, amount, status, actions
- **Status Badges**:
  - 已确认 (Confirmed) - Green
  - 待审核 (Pending Review) - Yellow
  - 处理中 (Processing) - Blue
- **Pagination**: Page numbers with prev/next controls

### 2. Invoice Detail Page (`gC9om`)

**Layout**: Sidebar (240px) + Main Content (Split View)

**Components**:
- **Header**:
  - Back button "返回列表"
  - Invoice title with number and metadata
  - Action buttons: 拒绝 (Reject), 确认发票 (Confirm Invoice)

- **Left Panel - Data Section**:
  - **Invoice Info Card**: Basic information with status badge
    - 发票号码, 开票日期, 金额, 税额
  - **Comparison Card** (Key UX Improvement):
    - Header showing match status "5/6 字段匹配"
    - Side-by-side table: OCR识别结果 vs LLM解析结果
    - **Visual mismatch highlighting**: Red background for discrepant fields
    - Status icons: ✓ (match) / ✗ (mismatch)
    - Fields compared: 发票号码, 开票日期, 销售方名称, 金额, 税额

- **Right Panel - PDF Preview**:
  - Header with zoom controls (+/-) and download button
  - PDF document preview area
  - File info display

### 3. Upload Page (`sgsSN`)

**Layout**: Sidebar (240px) + Main Content

**Components**:
- **Sidebar**: Same navigation as other pages with "上传发票" highlighted
- **Header**: Page title "上传发票"
- **Upload Card**:
  - Large drag-and-drop zone with dashed border
  - Upload icon (↑ arrow in circle)
  - Primary text: "点击或拖拽文件到此区域上传"
  - Supporting text: "支持 PDF、JPG、PNG 格式，单个文件最大 10MB，支持批量上传"
- **Action Buttons**:
  - "开始上传" (disabled by default until files selected)
  - "返回列表" (secondary button)

## Key UX Improvements

1. **Clear Visual Hierarchy**: Information organized by importance
2. **Status Visualization**: Color-coded badges for quick status recognition
3. **OCR vs LLM Comparison**: Side-by-side view with visual diff highlighting
4. **Mismatch Highlighting**: Red background immediately draws attention to discrepancies
5. **Action Clarity**: Primary/secondary button styling for confirm/reject actions
6. **PDF Context**: Preview panel allows reference while reviewing data

## Design Files

- **Pencil File**: `invoice-manager.pen` (open in VS Code with Pencil extension)
- **Node IDs**:
  - Invoice List: `FiWE2`
  - Invoice Detail: `gC9om`
  - Upload Page: `sgsSN`

## Comparison with Current Implementation

| Aspect | Current UI | New Design |
|--------|------------|------------|
| Navigation | Horizontal top bar | Vertical sidebar (240px) |
| Layout | Full-width content | Sidebar + Main content split |
| Metrics | None | 4 summary cards (count, amounts, tax) |
| Branding | Blue theme | Swiss clean with vermillion red accent |
| Typography | System fonts | Space Grotesk + Inter |
| OCR/LLM Comparison | Table with inline buttons | Visual mismatch highlighting (red background) |
| Upload | Basic Ant Design | Clean branded dropzone |

## Next Steps

1. Review and approve designs
2. Export high-resolution screenshots if needed
3. Proceed with code implementation based on approved designs
