# 发票管理系统 (Invoice Manager)

基于 OCR 的中国发票识别与管理系统。

## 功能特性

- 📤 **发票上传**: 支持 PDF、JPG、PNG 格式，批量上传
- 🔍 **OCR 识别**: 使用 PaddleOCR 自动识别发票内容
- 📝 **字段提取**: 自动提取发票号码、金额、日期等关键信息
- 📊 **统计报表**: 按状态、归属人统计，支持数据导出
- ✏️ **手动编辑**: 支持人工校对和修改识别结果
- 🏷️ **状态管理**: 待处理/待审核/已确认/已报销/未报销

## 技术栈

- **后端**: FastAPI + SQLAlchemy + PostgreSQL
- **前端**: React + TypeScript + Ant Design
- **OCR**: PaddleOCR
- **部署**: Docker Compose

## 快速开始

### 前置要求

- Docker & Docker Compose
- (可选) OpenAI API Key (用于 LLM 辅助解析)

### 启动服务

```bash
# 克隆项目
cd invoice_manager

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 访问地址

- 前端界面: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 项目结构

```
invoice_manager/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── models/         # 数据库模型
│   │   ├── routers/        # API 路由
│   │   ├── services/       # 业务逻辑
│   │   ├── schemas/        # Pydantic 模型
│   │   ├── config.py       # 配置
│   │   ├── database.py     # 数据库连接
│   │   └── main.py         # 应用入口
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React 前端
│   ├── src/
│   │   ├── components/     # 组件
│   │   ├── pages/          # 页面
│   │   ├── services/       # API 调用
│   │   └── types/          # TypeScript 类型
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## API 接口

### 发票操作

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/invoices/upload | 上传发票 |
| GET | /api/invoices | 获取发票列表 |
| GET | /api/invoices/{id} | 获取发票详情 |
| PUT | /api/invoices/{id} | 更新发票信息 |
| POST | /api/invoices/{id}/process | 触发 OCR 解析 |
| DELETE | /api/invoices/{id} | 删除发票 |
| POST | /api/invoices/batch-update | 批量更新状态 |
| GET | /api/invoices/statistics | 获取统计数据 |

## 发票字段

### 必填字段
- 发票号码 (invoice_number)
- 开票日期 (issue_date)
- 购买方名称 (buyer_name)
- 购买方纳税人识别号 (buyer_tax_id)
- 销售方名称 (seller_name)
- 销售方纳税人识别号 (seller_tax_id)
- 项目名称 (item_name)
- 价税合计 (total_with_tax)

### 可选字段
- 规格型号 (specification)
- 单位 (unit)
- 数量 (quantity)
- 单价 (unit_price)
- 金额 (amount)
- 税率 (tax_rate)
- 税额 (tax_amount)

## 开发指南

### 本地开发

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

### 环境变量

```env
# backend/.env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/invoice_db
OPENAI_API_KEY=your_api_key_here
DEBUG=true
```

## License

MIT
