# Digitization Platform - Technical Specification

**Version**: 1.0
**Last Updated**: 2026-01-06
**Purpose**: Complete technical specification to enable rebuilding the system from scratch

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Database Schema](#4-database-schema)
5. [Content Normalization Pipeline](#5-content-normalization-pipeline)
6. [RAG (Retrieval-Augmented Generation) System](#6-rag-retrieval-augmented-generation-system)
7. [Prompt Engineering](#7-prompt-engineering)
8. [LLM Integration](#8-llm-integration)
9. [Feedback Loop & Training Data](#9-feedback-loop--training-data)
10. [API & gRPC Services](#10-api--grpc-services)
11. [Message Queue Architecture](#11-message-queue-architecture)
12. [Schema Management](#12-schema-management)
13. [Observability & Monitoring](#13-observability--monitoring)
14. [Deployment Configuration](#14-deployment-configuration)
15. [OCR Processing Service](#15-ocr-processing-service)
16. [Feedback Loop Infrastructure](#16-feedback-loop-infrastructure)

---

## 1. Executive Summary

### 1.1 Purpose

The Digitization Platform is an **AI-powered document digitization backend service** that extracts structured data from documents (PDFs, Excel, Images) using Large Language Models (LLMs). It implements a **closed-loop workflow** with continuous improvement through:

- **RAG (Retrieval-Augmented Generation)** for few-shot learning
- **Human-in-the-loop feedback** for correction and validation
- **Automatic training data generation** for continuous improvement

### 1.2 Core Value Proposition

| Feature | Description |
|---------|-------------|
| **Anti-Hallucination** | Block ID-based source tracking ensures every extracted value links to specific document locations |
| **Continuous Learning** | Feedback automatically generates training data that improves future extractions |
| **Multi-Format Support** | PDF, Excel, Images with unified extraction pipeline |
| **Token Optimization** | Page pruning, text deduplication, and partial content reduce costs |

### 1.3 High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      External Systems                          │
│  (Frontend UI, Work Item Service, File Storage, etc.)         │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                    API Layer                                    │
│  ┌─────────────────┐     ┌─────────────────┐                  │
│  │   FastAPI       │     │    gRPC         │                  │
│  │   HTTP APIs     │     │    Services     │                  │
│  └─────────────────┘     └─────────────────┘                  │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                Service Layer                                    │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │           DigitizeWorkflowController                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │   Content    │  │     RAG      │  │ Digitization │   │ │
│  │  │ Normalizer   │→→│   Provider   │→→│   Executor   │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│               Message Queue Layer                               │
│  ┌──────────────────┐     ┌──────────────────┐                │
│  │ Digitization     │     │  RAG Training    │                │
│  │ Task Queue (SQS) │     │  Data Queue      │                │
│  └──────────────────┘     └──────────────────┘                │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│                Data Layer                                       │
│  ┌──────────────────┐     ┌──────────────────┐                │
│  │   PostgreSQL     │     │    pgvector      │                │
│  │   (SQLAlchemy)   │     │  (RAG Vectors)   │                │
│  └──────────────────┘     └──────────────────┘                │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. System Architecture

### 2.1 Project Structure

```
digitization_platform/
├── app/                          # Main backend application
│   ├── src/app/
│   │   ├── api/                  # FastAPI HTTP endpoints
│   │   ├── core/                 # Core models, config, database
│   │   │   ├── config.py         # Application settings
│   │   │   ├── database.py       # Database connection
│   │   │   ├── models/           # Pydantic/SQLModel models
│   │   │   └── repository/       # Data access layer
│   │   ├── grpc/                 # gRPC services
│   │   │   ├── server/           # gRPC server and servicers
│   │   │   ├── clients/          # gRPC client stubs
│   │   │   └── protos/           # Protocol buffer definitions
│   │   ├── llm/                  # LLM integration
│   │   │   └── openai_service.py # OpenAI API wrapper
│   │   ├── messagequeue/         # SQS consumers and publishers
│   │   ├── prompt/               # Prompt templates and engine
│   │   ├── schema/               # Schema management
│   │   └── service/              # Business logic
│   │       ├── workflow/         # Workflow components
│   │       │   ├── content_normalizer/
│   │       │   ├── executor/
│   │       │   └── rag_provider/
│   │       └── training_data/    # RAG training data generation
│   ├── migrations/               # Flyway SQL migrations
│   ├── tests/                    # Unit and integration tests
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── pyproject.toml            # Python dependencies (uv)
│
└── ocr/                          # OCR microservice (PaddleOCR)
    ├── src/
    ├── Dockerfile
    └── pyproject.toml
```

### 2.2 Core Components

| Component | Responsibility | Location |
|-----------|----------------|----------|
| **DigitizeWorkflowController** | Orchestrates the entire extraction pipeline | `service/digitize_workflow_controller.py` |
| **ContentNormalizer** | Converts documents to structured text blocks | `service/workflow/content_normalizer/` |
| **RAGProvider** | Retrieves similar examples for few-shot learning | `service/workflow/rag_provider/` |
| **DigitizationExecutor** | Builds prompts and invokes LLM | `service/workflow/executor/` |
| **FeedbackManagementService** | Processes human corrections | `service/digi_flow_feedback_management_service.py` |
| **RAGTrainingDataGenerator** | Creates training vectors from feedback | `service/training_data/rag_training_data_generator.py` |

### 2.3 Workflow Execution Flow

```
1. CreateDigiFlow Request
        │
        ▼
2. Load Config & Schema
        │
        ▼
3. Download Files from Storage
        │
        ▼
4. Content Normalization
   ├── PDF: PyMuPDF + PaddleOCR → Text Blocks with IDs
   ├── Excel: openpyxl → Cells with IDs
   └── Images: PaddleOCR → Text Blocks with IDs
        │
        ▼
5. Page Pruning (Optional)
   └── LLM classifies pages as relevant/irrelevant
        │
        ▼
6. RAG Example Retrieval
   ├── Generate embedding from document
   ├── Search similar examples in pgvector
   └── Build few-shot example prompt
        │
        ▼
7. Prompt Construction
   ├── System: Role + Task + Source Mapping Rules + RAG Example
   └── User: Document Content (plain text + text blocks)
        │
        ▼
8. LLM Invocation (GPT-4o/GPT-5.1)
   └── Structured output with data_source tracking
        │
        ▼
9. Schema Validation
        │
        ▼
10. Result Persistence
        │
        ▼
11. Human Review (External)
        │
        ▼
12. Feedback Processing → Training Data Generation
```

---

## 3. Technology Stack

### 3.1 Backend Technologies

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Language** | Python | 3.12 | Primary backend language |
| **Package Manager** | uv | latest | Fast Python package management |
| **Web Framework** | FastAPI | ^0.115 | HTTP API endpoints |
| **RPC Framework** | gRPC | ^1.67 | Service communication |
| **ORM** | SQLAlchemy + SQLModel | 2.0 | Database access |
| **Database** | PostgreSQL | 16+ | Primary data store |
| **Vector DB** | pgvector | 0.7+ | RAG embedding storage |

### 3.2 AI/ML Technologies

| Category | Technology | Model/Version | Purpose |
|----------|------------|---------------|---------|
| **LLM Provider** | OpenAI | GPT-4o, GPT-4o-mini, GPT-5.1 | Document extraction |
| **LLM Framework** | LangChain | ^0.3 | Structured output, model abstraction |
| **Observability** | LangSmith | latest | Tracing, feedback, evaluation |
| **OCR** | PaddleOCR | PP-OCRv5 | Text extraction from images |
| **PDF Processing** | PyMuPDF (fitz) | ^1.25 | PDF text and image extraction |
| **Embedding Model** | OpenAI | text-embedding-3-small | 1536-dim vectors for RAG |
| **Tokenization** | tiktoken | latest | Token counting and deduplication |

### 3.3 Infrastructure

| Category | Technology | Purpose |
|----------|------------|---------|
| **Containerization** | Docker | Application packaging |
| **Message Queue** | AWS SQS | Async task processing |
| **File Storage** | AWS S3 | Document storage |
| **Error Tracking** | Sentry | Error monitoring |
| **Metrics** | Datadog | Application monitoring |
| **Migrations** | Flyway | Database schema migrations |

### 3.4 Key Dependencies (pyproject.toml)

```toml
[project]
dependencies = [
    # Web & API
    "fastapi>=0.115.0",
    "grpcio>=1.67.0",
    "grpcio-tools>=1.67.0",
    "uvicorn>=0.32.0",

    # Database
    "sqlalchemy>=2.0.0",
    "sqlmodel>=0.0.22",
    "asyncpg>=0.30.0",
    "pgvector>=0.3.0",

    # AI/ML
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "langsmith>=0.1.0",
    "openai>=1.55.0",
    "tiktoken>=0.8.0",

    # Document Processing
    "pymupdf>=1.25.0",
    "openpyxl>=3.1.0",
    "markitdown>=0.0.1",

    # Data Validation
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",

    # AWS
    "boto3>=1.35.0",

    # Utilities
    "httpx>=0.28.0",
    "pyyaml>=6.0.0",
    "toon-format>=0.1.0",  # Compact JSON-like format
]
```

---

## 4. Database Schema

### 4.1 Entity Relationship Diagram

```
┌─────────────────────┐       ┌─────────────────────┐
│   digi_flow_schema  │       │   digi_flow_config  │
├─────────────────────┤       ├─────────────────────┤
│ id (PK)             │◄──────│ schema_id (FK)      │
│ slug                │       │ schema_version (FK) │
│ name                │       │ id (PK)             │
│ yaml_schema         │       │ slug                │
│ schema (JSON)       │       │ name                │
│ version             │       │ domain              │
│ status              │       │ source_content_type │
│ created_at/by       │       │ workflow_config     │
│ updated_at/by       │       │ prompt_config       │
│ deleted_at/by       │       │ schema_validation   │
└─────────────────────┘       │ version             │
                              │ status              │
                              │ created_at/by       │
                              └─────────┬───────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────┐
│                      digi_flow                          │
├─────────────────────────────────────────────────────────┤
│ id (PK)                                                 │
│ config_id (FK) → digi_flow_config                       │
│ config_version                                          │
│ schema_id (FK) → digi_flow_schema                       │
│ schema_version                                          │
│ content_type                                            │
│ content_context (JSONB)  # Source file references       │
│ content_metadata (JSONB) # Extracted text blocks        │
│ langsmith_trace_id                                      │
│ langsmith_metadata (JSONB)                              │
│ main_status                                             │
│ data_service_status                                     │
│ schema_validation_status                                │
│ created_at/by, updated_at/by                            │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  digi_flow_result                       │
├─────────────────────────────────────────────────────────┤
│ id (PK)                                                 │
│ flow_id (FK) → digi_flow                                │
│ data (JSONB)           # Extracted data with sources    │
│ plain_data (JSONB)     # Extracted data without sources │
│ text_blocks (JSONB)    # Text blocks used for extraction│
│ data_origin            # SYSTEM=0, USER=1               │
│ version                                                 │
│ updated_at/by                                           │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              digi_flow_result_field_audit               │
├─────────────────────────────────────────────────────────┤
│ id (PK)                                                 │
│ flow_id (FK)                                            │
│ result_id (FK)                                          │
│ result_version                                          │
│ field_path             # JSON path to corrected field   │
│ old_value (JSONB)                                       │
│ new_value (JSONB)                                       │
│ reason_code            # Correction reason              │
│ audited_at/by                                           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              rag_training_data_vector                   │
├─────────────────────────────────────────────────────────┤
│ id (PK)                                                 │
│ flow_id (FK) → digi_flow                                │
│ config_id (FK) → digi_flow_config                       │
│ schema_id (FK)                                          │
│ schema_version                                          │
│ result_id (FK)                                          │
│ result_version                                          │
│ source_content_context (JSONB)                          │
│ source_content_context_idx                              │
│ reference_input (JSONB)  # Input for few-shot example   │
│ reference_output (JSONB) # Output for few-shot example  │
│ embedding VECTOR(1536)   # Document embedding           │
│ created_at/by                                           │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Core Table Definitions

#### 4.2.1 digi_flow_schema

Stores extraction schemas that define the output structure.

```sql
CREATE TABLE digi_flow_schema (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY,
    slug VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL DEFAULT 'Unnamed Schema',
    yaml_schema TEXT,                    -- Human-readable YAML definition
    schema JSONB NOT NULL DEFAULT '{}'::jsonb,  -- JSON Schema for validation
    version INT NOT NULL DEFAULT 1,
    status INT NOT NULL DEFAULT 1,       -- 1=ACTIVE, 2=ARCHIVED
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC'),
    created_by JSONB,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    updated_by JSONB,
    deleted_at TIMESTAMP WITHOUT TIME ZONE,
    deleted_by JSONB,
    PRIMARY KEY (id, version)
);

CREATE UNIQUE INDEX idx_digi_flow_schema_active_slug
    ON digi_flow_schema (slug, version) WHERE deleted_at IS NULL;
```

#### 4.2.2 digi_flow_config

Stores workflow configurations including prompts, RAG settings, and extraction parameters.

```sql
CREATE TABLE digi_flow_config (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    slug VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    domain VARCHAR(64),
    schema_id BIGINT NOT NULL,
    schema_version INT NOT NULL,
    source_content_type INT NOT NULL,    -- 1=FILE, 2=TEXT
    workflow_config JSONB,               -- Digitization, RAG, Pruning settings
    prompt_config JSONB,                 -- Task description, data mapping, instructions
    schema_validation JSONB,             -- Validation rules
    version INT NOT NULL DEFAULT 1,
    status INT NOT NULL DEFAULT 1,       -- 1=ACTIVE, 2=ARCHIVED
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC'),
    created_by JSONB,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    updated_by JSONB,
    deleted_at TIMESTAMP WITHOUT TIME ZONE,
    deleted_by JSONB
);
```

#### 4.2.3 digi_flow

Stores individual digitization task instances.

```sql
CREATE TABLE digi_flow (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    config_id BIGINT NOT NULL,
    config_version INT NOT NULL,
    schema_id BIGINT NOT NULL,
    schema_version INT NOT NULL,
    content_type INT NOT NULL,
    content_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    content_metadata JSONB,
    langsmith_trace_id VARCHAR,
    langsmith_metadata JSONB,
    main_status INT NOT NULL DEFAULT 0,         -- 0=PENDING, 1=IN_PROGRESS, 2=COMPLETED, 3=FAILED
    data_service_status INT NOT NULL DEFAULT 0,
    schema_validation_status INT NOT NULL DEFAULT 0,
    schema_validation_result JSONB,
    extra_attributes JSONB,
    metadata JSONB,
    is_sampled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC'),
    created_by JSONB,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    updated_by JSONB
);

CREATE INDEX idx_digi_flow_config_version ON digi_flow (config_id, config_version);
CREATE INDEX idx_digi_flow_main_status ON digi_flow (main_status);
```

#### 4.2.4 digi_flow_result

Stores extraction results with versioning.

```sql
CREATE TABLE digi_flow_result (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    flow_id BIGINT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}'::jsonb,     -- Full result with data_source
    plain_data JSONB,                             -- Result without data_source
    text_blocks JSONB,                            -- Text blocks used
    data_origin INT NOT NULL DEFAULT 0,          -- 0=SYSTEM, 1=USER
    version INT NOT NULL DEFAULT 1,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC'),
    updated_by JSONB
);

CREATE UNIQUE INDEX idx_digi_flow_result_flow_id ON digi_flow_result (flow_id);
```

#### 4.2.5 rag_training_data_vector

Stores RAG training vectors with embeddings for similarity search.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE rag_training_data_vector (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    flow_id BIGINT NOT NULL,
    config_id BIGINT NOT NULL,
    schema_id BIGINT NOT NULL,
    schema_version INT NOT NULL,
    result_id BIGINT NOT NULL,
    result_version INT NOT NULL,
    source_content_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_content_context_idx INT NOT NULL DEFAULT 0,
    reference_input JSONB NOT NULL,              -- Pre-formatted input for few-shot
    reference_output JSONB NOT NULL,             -- Expected output for few-shot
    embedding VECTOR(1536) NOT NULL,             -- text-embedding-3-small
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    created_by JSONB
);

-- HNSW index for fast similarity search
CREATE INDEX idx_rag_training_data_vector_embedding_hnsw
    ON rag_training_data_vector USING hnsw (embedding vector_cosine_ops);

CREATE INDEX idx_rag_training_data_vector_config_id
    ON rag_training_data_vector (config_id, flow_id);

CREATE UNIQUE INDEX idx_rag_training_data_vector_flow_id_source_content_context_idx
    ON rag_training_data_vector (flow_id, source_content_context_idx);
```

### 4.3 Configuration JSONB Structures

#### 4.3.1 workflow_config

```python
class WorkflowConfig(BaseModel):
    digitization_config: DigitizationConfig | None = None
    rag_config: RAGConfig | None = None
    page_pruning_config: PagePruningConfig | None = None

class DigitizationConfig(BaseModel):
    model: str = "gpt-4o-mini"                    # LLM model
    reasoning_effort: str | None = None          # none/low/medium/high
    service_tier: str = "standard"               # standard/flex
    text_deduplication_enabled: bool = True

class RAGConfig(BaseModel):
    enabled: bool = True
    distance_threshold: float = 0.3              # Max cosine distance for matches
    training_data_source_fields: list[str] = ["plain_text", "text_blocks"]
    training_data_reference_fields: list[str] = ["output_values", "data_source_info"]
    zero_shot_example: str | None = None         # Fallback when no RAG match

class PagePruningConfig(BaseModel):
    enabled: bool = False
    model: str = "gpt-5-mini"
```

#### 4.3.2 prompt_config

```python
class PromptConfig(BaseModel):
    task_description: str | None = None          # Custom task description
    data_mapping: str | None = None              # Field mapping instructions
    extra_instructions: str | None = None        # Additional extraction rules
```

#### 4.3.3 source_content_context (DocumentContext)

```python
class DocumentContext(BaseModel):
    document_fids: list[str]                     # File object FIDs
    metadata: dict | None = None                 # Additional context
```

---

## 5. Content Normalization Pipeline

### 5.1 Overview

Content normalization transforms raw documents into structured text blocks with spatial positioning and unique IDs. This enables:

1. **Precise source tracking** - Every extracted value can reference its exact source location
2. **Anti-hallucination** - LLM must provide valid block_id for each extracted value
3. **Human verification** - Users can verify extractions against source blocks

### 5.2 Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    FileLoader                                │
│  Download files from S3/storage to temp directory            │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              Content Type Detection                          │
│  Determine file type: PDF, Excel, Image                      │
└──────────────────────────┬───────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │   PDF    │    │  Excel   │    │  Image   │
    │Extractor │    │Extractor │    │Extractor │
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
         ▼               ▼               ▼
┌──────────────────────────────────────────────────────────────┐
│              Spatial Clustering (DBSCAN)                     │
│  Group text blocks into rows and columns                     │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              Block ID Assignment                             │
│  Format: {document}.{page}.{row}:{column}:{index}           │
└──────────────────────────────────────────────────────────────┘
```

### 5.3 PDF Extraction (`PDFExtractor`)

**Location**: `app/src/app/service/workflow/content_normalizer/extractor/pdf_extractor.py`

#### 5.3.1 Text Extraction Flow

```python
async def extract(self, file: File) -> FileContentMetadata:
    """
    Extract content from PDF file.

    1. Open PDF with PyMuPDF (fitz)
    2. For each page:
       a. Extract text spans with bounding boxes
       b. Extract embedded images and run OCR
       c. Merge text + OCR bounding boxes
       d. Cluster into rows/columns using DBSCAN
       e. Assign block IDs: {doc}.{page}.{row}:{col}:{idx}
    3. Return FileContentMetadata with all pages
    """
```

#### 5.3.2 Text Span Extraction

```python
async def _extract_text_bboxes(self, page: fitz.Page) -> List[BoundingBox]:
    """Extract text spans from native PDF text layer."""
    bboxes = []
    text_dict = page.get_text("dict")

    for block in text_dict["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                is_valid, processed_text = self._normalize_text(span["text"])
                if not is_valid:
                    continue

                bbox = BoundingBox(
                    id="",  # Assigned later
                    raw_value=processed_text,
                    top_left_x=span["bbox"][0],
                    top_left_y=span["bbox"][1],
                    bottom_right_x=span["bbox"][2],
                    bottom_right_y=span["bbox"][3],
                )
                bboxes.append(bbox)

    return bboxes
```

#### 5.3.3 OCR for Embedded Images

```python
async def _extract_images_bboxes(self, page: fitz.Page, page_index: int) -> List[BoundingBox]:
    """Extract text from images embedded in PDF using PaddleOCR."""
    image_list = page.get_images(full=True)
    bboxes = []

    for img in image_list:
        xref = img[0]
        for rect in page.get_image_rects(xref):
            # Extract image and run OCR
            image_bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
            ocr_bboxes = await self._execute_ocr(
                pdf=page.parent,
                xref=xref,
                image_bbox=image_bbox
            )
            bboxes.extend(ocr_bboxes)

    return bboxes
```

#### 5.3.4 OCR Execution

```python
async def _execute_ocr(self, pdf, xref, image_bbox) -> List[BoundingBox]:
    """Execute OCR on extracted image."""
    # Extract image from PDF
    image_data = pdf.extract_image(xref)
    x0, y0, x1, y1 = image_bbox

    # Calculate scaling factors
    pdf_img_width = x1 - x0
    pdf_img_height = y1 - y0
    scale_x = pdf_img_width / image_data["width"]
    scale_y = pdf_img_height / image_data["height"]

    # Save image temporarily and run OCR
    with tempfile.NamedTemporaryFile(suffix=f".{image_data['ext']}") as temp:
        temp.write(image_data["image"])
        ocr_result = await self.ocr_service.ocr(temp.name)

    # Transform OCR coordinates to PDF page coordinates
    bboxes = []
    for region in ocr_result.regions:
        bbox = BoundingBox(
            id="",
            raw_value=region.text,
            top_left_x=region.bounding_box.top_left[0] * scale_x + x0,
            top_left_y=region.bounding_box.top_left[1] * scale_y + y0,
            bottom_right_x=region.bounding_box.bottom_right[0] * scale_x + x0,
            bottom_right_y=region.bounding_box.bottom_right[1] * scale_y + y0,
        )
        bboxes.append(bbox)

    return bboxes
```

### 5.4 DBSCAN Clustering

**Location**: `app/src/app/service/workflow/content_normalizer/extractor/dbscan_algorithm.py`

The DBSCAN algorithm clusters bounding boxes into logical rows and columns using a **custom O(n log n) implementation** with adaptive eps calculation and section-based re-clustering.

#### 5.4.1 Custom DBSCAN Implementation (O(n log n))

**CRITICAL**: Do NOT use `sklearn.cluster.DBSCAN`. Implement a custom 1D DBSCAN using sorted indices and sliding window:

```python
def dbscan(points: List[float], eps: float, min_samples: int) -> List[int]:
    """
    Optimized DBSCAN implementation for 1D points using sorted indices and sliding window.
    Time complexity: O(n log n) instead of O(n²).

    Algorithm:
    1. Sort points with their original indices
    2. Pre-compute neighbors using sliding window (O(n log n))
    3. Expand clusters iteratively

    Args:
        points: List of 1D points (y-coordinates or x-coordinates)
        eps: Maximum distance between two samples
        min_samples: Minimum number of samples in a neighborhood

    Returns:
        List of cluster labels (-1 for noise points)
    """
    n = len(points)
    if n == 0:
        return []

    labels = [-1] * n
    cluster_id = 0

    # Sort points with their original indices for efficient neighbor finding
    indexed_points = sorted(enumerate(points), key=lambda x: x[1])
    sorted_indices = [idx for idx, _ in indexed_points]
    sorted_points = [pt for _, pt in indexed_points]

    # Pre-compute neighbors using sliding window (O(n log n) instead of O(n²))
    neighbors_cache: dict[int, List[int]] = {i: [] for i in range(n)}
    for i in range(n):
        idx_i = sorted_indices[i]
        # Expand right and left to find all neighbors within eps
        left = right = i
        while right < n - 1 and sorted_points[right + 1] - sorted_points[i] <= eps:
            right += 1
        while left > 0 and sorted_points[i] - sorted_points[left - 1] <= eps:
            left -= 1
        # Collect neighbors
        for j in range(left, right + 1):
            if j != i:
                neighbors_cache[idx_i].append(sorted_indices[j])

    # Standard DBSCAN cluster expansion using pre-computed neighbors
    for orig_idx in range(n):
        if labels[orig_idx] != -1:
            continue
        neighbors = neighbors_cache[orig_idx]
        if len(neighbors) < min_samples:
            continue
        # Start new cluster and expand
        labels[orig_idx] = cluster_id
        seed_set = set(neighbors)
        processed = {orig_idx}
        while seed_set:
            j = seed_set.pop()
            if j in processed:
                continue
            processed.add(j)
            if labels[j] == -1:
                labels[j] = cluster_id
            j_neighbors = neighbors_cache[j]
            if len(j_neighbors) >= min_samples:
                seed_set.update(n for n in j_neighbors if n not in processed)
        cluster_id += 1

    return labels
```

#### 5.4.2 Adaptive Eps Calculation

Calculate eps dynamically based on median heights and inter-row spacing:

```python
# Configuration constants
ROW_EPS_MULTIPLIER = 0.8      # Base multiplier for median height
ROW_EPS_GAP_RATIO = 0.35      # Ratio of median gap used for eps
ROW_EPS_RANGE = (0.5, 1.1)    # (min, max) eps as ratio of median height
ROW_DEFAULT_EPS = 3.5         # Default eps when median height is 0

def _calculate_adaptive_eps(y_coords: List[float], heights: List[float]) -> float:
    """
    Calculate adaptive eps based on inter-row spacing and bbox heights.

    Algorithm:
    1. Calculate median height from sorted heights
    2. Calculate median gap from filtered inter-row gaps
    3. Use gap-based eps if available, otherwise height-based
    4. Clamp to ROW_EPS_RANGE as ratio of median height
    """
    if not y_coords or not heights:
        return ROW_DEFAULT_EPS

    # Calculate median height (single sort)
    sorted_heights = sorted(heights)
    median_height = sorted_heights[len(sorted_heights) // 2] if sorted_heights else 0.0

    if median_height == 0.0:
        return ROW_DEFAULT_EPS

    # Calculate gaps from sorted y-coords
    sorted_y = sorted(y_coords)
    if len(sorted_y) < 2:
        return max(median_height * ROW_EPS_MULTIPLIER, ROW_DEFAULT_EPS)

    # Filter gaps: only consider inter-row spacing (not intra-row)
    min_gap = median_height * 0.85  # Strict filtering
    max_gap = median_height * 2.5   # Exclude very large gaps
    filtered_gaps = [
        sorted_y[i + 1] - sorted_y[i]
        for i in range(len(sorted_y) - 1)
        if min_gap <= (sorted_y[i + 1] - sorted_y[i]) <= max_gap
    ]

    # Calculate eps from gaps or fallback to height-based
    if filtered_gaps:
        sorted_gaps = sorted(filtered_gaps)
        median_gap = sorted_gaps[len(sorted_gaps) // 2]
        eps = median_gap * ROW_EPS_GAP_RATIO
    else:
        eps = median_height * ROW_EPS_MULTIPLIER

    # Clamp eps to configured range
    eps_min, eps_max = ROW_EPS_RANGE
    eps = max(median_height * eps_min, min(eps, median_height * eps_max))

    return eps
```

#### 5.4.3 Section-Based Re-Clustering

Documents often have different column structures in different sections (header, body, footer). The algorithm identifies sections and re-clusters within each:

```python
# Configuration
ENABLE_SECTION_ADAPTIVE_ROWS = True
INITIAL_ROW_EPS_MULTIPLIER = 1.05
MIN_SECTION_BBOXES_FOR_ADAPTIVE = 5

def _identify_sections(rows: List[List[BoundingBox]], window_size: int = 3) -> List[List[int]]:
    """
    Identify sections by analyzing column structure differences between rows.

    Algorithm:
    1. Extract column positions for each row (x-coordinates of columns)
    2. Calculate structure similarity between adjacent rows
    3. Detect section boundaries where similarity drops below threshold
    4. Return list of sections (each section is list of row indices)
    """
    # ... implementation details

def cluster_into_coordinates(bboxes: List[BoundingBox], eps: float = None) -> List[Tuple[int, int, BoundingBox]]:
    """
    Cluster bboxes into rows and columns, handling multi-row text blocks.
    Uses section-based approach: first identifies sections by column structure,
    then clusters columns within each section using neighboring rows.

    Full Algorithm:
    1. Initial rough row clustering (more lenient eps for section identification)
    2. Identify sections based on column structure differences
    3. Adaptive row re-clustering within each section (section-specific eps)
    4. Process each section separately to identify columns
    5. Assign final (row, column, bbox) coordinates

    Returns:
        List of (row_index, column_index, bbox) sorted by position
    """
```

#### 5.4.4 Main Clustering Entry Point

```python
def cluster_into_coordinates(bboxes: List[BoundingBox], eps: float = None) -> List[Tuple[int, int, BoundingBox]]:
    """
    Main entry point for clustering bounding boxes into row/column coordinates.

    Args:
        bboxes: List of BoundingBox objects with position information
        eps: Optional eps value. If None, auto-calculate using adaptive method.

    Returns:
        List of (row_index, column_index, bbox) tuples sorted by position
    """
    if not bboxes:
        return []

    # Step 1: Initial row clustering
    y_coords = [(bbox.top_left_y + bbox.bottom_right_y) / 2.0 for bbox in bboxes]
    heights = [bbox.bottom_right_y - bbox.top_left_y for bbox in bboxes]

    if eps is None:
        base_eps = _calculate_adaptive_eps(y_coords, heights)
        if ENABLE_SECTION_ADAPTIVE_ROWS:
            eps = base_eps * INITIAL_ROW_EPS_MULTIPLIER
        else:
            eps = base_eps

    rows = cluster_into_rows(bboxes, eps, min_samples=1)
    rows = sorted(rows, key=lambda r: min(bbox.top_left_y for bbox in r))

    # Step 2: Identify sections based on column structure
    sections = _identify_sections(rows)

    # Step 3: Re-cluster rows within each section with section-specific eps
    if ENABLE_SECTION_ADAPTIVE_ROWS:
        # ... section-by-section re-clustering

    # Step 4: Cluster columns within each section
    # ... column clustering with template matching

    return result
```

### 5.5 Block ID Format

| Document Type | ID Format | Example |
|---------------|-----------|---------|
| **PDF/Image** | `{doc}.{page}.{row}:{col}:{idx}` | `1.2.3:1:5` (Doc 1, Page 2, Row 3, Col 1, Index 5) |
| **Excel** | `{doc}.{sheet}.{cell}` | `1.1.A1` (Doc 1, Sheet 1, Cell A1) |
| **Excel (Merged)** | `{doc}.{sheet}.{start}:{end}` | `1.1.B2:C2` (Merged cells B2 to C2) |

### 5.6 BoundingBox Data Model

```python
class BoundingBox(BaseModel):
    id: str                    # Block ID (e.g., "1.2.3:1:5")
    raw_value: str             # Extracted text content
    top_left_x: float          # X coordinate of top-left corner
    top_left_y: float          # Y coordinate of top-left corner
    bottom_right_x: float      # X coordinate of bottom-right corner
    bottom_right_y: float      # Y coordinate of bottom-right corner

class Page(BaseModel):
    id: int                    # 1-indexed page number
    width: int                 # Page width in points
    height: int                # Page height in points
    bounding_box: List[BoundingBox]

class PageContent(BaseModel):
    pages: List[Page]

class FileContentMetadata(BaseModel):
    index: int                 # Document index (1-indexed)
    file_object_fid: str       # File storage reference
    file_name: str
    file_bytes_size: int
    content_type: FileContentType
    languages: List[str]
    file_content: PageContent | SheetContent
```

### 5.7 Excel Extraction (`ExcelExtractor`)

**Location**: `app/src/app/service/workflow/content_normalizer/extractor/excel_extractor.py`

```python
async def extract(self, file: File) -> FileContentMetadata:
    """
    Extract content from Excel file using openpyxl.

    1. Open workbook
    2. For each sheet:
       a. Iterate through non-empty cells
       b. Handle merged cell ranges
       c. Assign cell IDs: {doc}.{sheet}.{cell}
    3. Return FileContentMetadata with all sheets
    """
```

### 5.8 Page Pruning

**Location**: `app/src/app/service/workflow/content_normalizer/pruner/pdf_pruner.py`

Page pruning uses an LLM to identify relevant pages before main extraction:

```python
async def prune(self, file: File, schema_id: SchemaIdentifier, config: PagePruningConfig) -> File:
    """
    Prune irrelevant pages from PDF to reduce token usage.

    Algorithm:
    1. Skip if document has < 3 pages
    2. Build page pruning prompt with schema field tree
    3. LLM classifies each page with fields it contains
    4. Analyze which pages have "new" information:
       - Pages with array/object fields → always include
       - Pages with simple fields not yet seen → include
       - Pages with only repeated simple fields → skip
    5. Create pruned PDF and content metadata
    """
```

---

## 6. RAG (Retrieval-Augmented Generation) System

### 6.1 Overview

The RAG system provides **few-shot learning** by finding similar past extractions and including them as examples in the prompt. This dramatically improves extraction accuracy without fine-tuning.

### 6.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   RAG Provider V2                           │
│  Location: service/workflow/rag_provider/file_rag_provider_v2.py
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  build_example()                            │
│  1. Generate embedding from current document                │
│  2. Search for similar examples in pgvector                 │
│  3. Build few-shot example prompt                           │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Embedding Generation

**Model**: OpenAI `text-embedding-3-small` (1536 dimensions)

```python
async def _generate_file_embedding(self, source_content_metadata: SourceContentMetadata) -> list[float]:
    """
    Generate embedding for document content.

    1. Extract plain text from all pages
    2. Wrap with labels: <page_1>...</page_1>
    3. Build weighted embedding text (prioritize important content)
    4. Call OpenAI embeddings API
    """
    texts = build_plain_text(source_content_metadata)
    labeled_texts = wrap_with_label(texts, "page")
    weight_embedding_text = build_weighted_embedding_text(labeled_texts, max_token=8192)
    return await self.embedding_service.generate_embeddings(weight_embedding_text)
```

### 6.4 Weighted Embedding Text

```python
def build_weighted_embedding_text(
    labeled_pages: List[List[str]],
    max_token: int = 8192
) -> str:
    """
    Build weighted text for embedding, prioritizing:
    1. First page (usually contains key info)
    2. Last page (often has summary)
    3. Middle pages (fill remaining space)
    """
```

### 6.5 Similarity Search

**Location**: `app/src/app/core/repository/rag_training_data_vector_repository.py`

```python
async def get_by_similarity_search(
    self,
    session: AsyncSession,
    vector_input: list[float],
    k: int = 1,
    distance_threshold: float = 0.3,
    filters: dict | None = None,
) -> list[tuple[RAGTrainingDataVector, float]]:
    """
    Search for similar training vectors using pgvector.

    SQL:
    SELECT *, embedding <=> :query_vector AS distance
    FROM rag_training_data_vector
    WHERE config_id = :config_id
      AND (embedding <=> :query_vector) < :threshold
    ORDER BY distance
    LIMIT :k
    """
```

### 6.6 Few-Shot Example Construction

```python
async def _build_rag_example(self, rag_config: RAGConfig, training_data: TrainingData) -> RAGExample:
    """
    Build few-shot example from training data.

    Output format:
    # Few-Shot Example

    <example>

    <instruction>
    This example demonstrates the strict mapping...
    </instruction>

    <name>booking_confirmation.pdf</name>

    <plain_text_input>
    <page_1>
    Booking No: 123456 | Vessel: MOCK VESSEL...
    </page_1>
    </plain_text_input>

    <input_text_block>
    <page_1>
    [{"id":"1.1.1:1:1","text":"Booking No:","x_center":100,"y_center":50}...]
    </page_1>
    </input_text_block>

    <expected_output>
    {"booking_number":{"value":"123456","data_source":{"block_id":"1.1.1:2:2"}}...}
    </expected_output>

    </example>
    """
```

### 6.7 Zero-Shot Fallback

When no similar examples are found (distance > threshold), the system uses a zero-shot example:

```python
@staticmethod
def build_zero_shot_example(output_json: str) -> str:
    """Build zero-shot example with output JSON wrapped in expected_output tags."""
    return "\n".join([
        "# Zero-Shot Example",
        "<expected_output>",
        output_json,
        "</expected_output>",
    ])
```

### 6.8 RAG Configuration Options

| Parameter | Type | Description |
|-----------|------|-------------|
| `enabled` | bool | Enable/disable RAG |
| `distance_threshold` | float | Max cosine distance (0.0-1.0), lower = stricter matching |
| `training_data_source_fields` | list | Fields to include in input: `plain_text`, `text_blocks` |
| `training_data_reference_fields` | list | Fields to include in output: `output_values`, `data_source_info` |
| `zero_shot_example` | str | Fallback example when no RAG match |

### 6.9 Token Optimization

**Location**: `app/src/app/core/models/source_content_metadata/embedding_text_builder.py`

Token optimization reduces LLM costs and improves extraction accuracy by eliminating redundant content.

#### 6.9.1 Tiktoken Encoder Caching

**CRITICAL**: Use a global encoder cache to avoid repeated initialization:

```python
import tiktoken

_ENCODER_CACHE: tiktoken.Encoding | None = None
_ENCODER_MODEL = "text-embedding-3-small"

def _get_encoder() -> tiktoken.Encoding:
    """Get cached tiktoken encoder. Initialize once, reuse everywhere."""
    global _ENCODER_CACHE
    if _ENCODER_CACHE is None:
        _ENCODER_CACHE = tiktoken.encoding_for_model(_ENCODER_MODEL)
    return _ENCODER_CACHE
```

#### 6.9.2 Tiktoken-Based Line Deduplication

Remove duplicate lines across pages using **token-based Jaccard similarity** (NOT word-based):

```python
SIMILARITY_THRESHOLD = 0.95  # Lines with >= 95% similarity are duplicates

def _remove_duplicated_lines(
    page_lines_list: List[List[str]],
    similarity_threshold: float = 0.95,
) -> List[List[str]]:
    """
    Remove duplicate lines across all pages using tiktoken-based similarity.

    Algorithm:
    1. Maintain a set of seen lines and their normalized forms
    2. For each line, check if it's an exact duplicate (normalized)
    3. If not exact, calculate tiktoken-based Jaccard similarity
    4. Skip lines that are >= similarity_threshold similar to any seen line
    """
    seen_lines: List[str] = []
    seen_normalized: set[str] = set()
    result: List[List[str]] = []

    for page_lines in page_lines_list:
        filtered_lines: List[str] = []
        for line in page_lines:
            if not line.strip():
                filtered_lines.append(line)
                continue

            normalized = " ".join(line.lower().split())
            if normalized in seen_normalized:
                continue  # Exact duplicate

            is_duplicate = False
            for seen_line in seen_lines:
                similarity = _calculate_line_similarity_fast(line, normalized, seen_line, similarity_threshold)
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                filtered_lines.append(line)
                seen_lines.append(line)
                seen_normalized.add(normalized)

        result.append(filtered_lines)

    return result

def _calculate_line_similarity_fast(line1: str, normalized1: str, line2: str, threshold: float) -> float:
    """
    Calculate tiktoken-based Jaccard similarity between two lines.

    IMPORTANT: Use tiktoken tokens, NOT word tokens.
    """
    enc = _get_encoder()
    if not line2.strip():
        return 0.0 if normalized1 else 1.0

    normalized2 = " ".join(line2.lower().split())
    if normalized1 == normalized2:
        return 1.0

    # Convert to token sets using tiktoken
    tokens1 = set(enc.encode(normalized1))
    tokens2 = set(enc.encode(normalized2))

    if not tokens1 or not tokens2:
        return 0.0

    # Jaccard similarity: |A ∩ B| / |A ∪ B|
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)

    return intersection / union if union > 0 else 0.0
```

#### 6.9.3 Weighted Page Truncation

Allocate more tokens to earlier pages (usually more important):

```python
def _apply_weighted_truncation(
    pages: List[List[str]],
    encoded_tokens: List[List[int]],
    token_counts: List[int],
    max_token: int,
    decay_factor: float = 1.0,
) -> List[str]:
    """
    Apply weighted truncation to pages, prioritizing earlier pages.

    Weight formula: weight[i] = 1.0 / ((i + 1) ** decay_factor)
    - Page 1: 1.0
    - Page 2: 0.5 (with decay_factor=1.0)
    - Page 3: 0.33
    - etc.

    Args:
        pages: List of pages, each page is list of lines
        encoded_tokens: Pre-encoded tokens for each page
        token_counts: Token count for each page
        max_token: Maximum total tokens allowed
        decay_factor: Controls how quickly weight decreases (1.0 = linear decay)

    Returns:
        List of truncated page strings
    """
    n = len(pages)
    if n == 0:
        return []

    # Calculate weights with decay
    weights = [1.0 / ((i + 1) ** decay_factor) for i in range(n)]
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    # Allocate tokens proportionally
    allocated_tokens = [int(w * max_token) for w in normalized_weights]

    # Handle rounding excess
    total_allocated = sum(allocated_tokens)
    if total_allocated > max_token:
        diff = total_allocated - max_token
        for i in range(n - 1, -1, -1):
            if diff <= 0:
                break
            reduction = min(diff, allocated_tokens[i])
            allocated_tokens[i] -= reduction
            diff -= reduction

    # Truncate each page to its allocation
    truncated_texts: List[str] = []
    for page_lines, tokens, original_count, allocated in zip(pages, encoded_tokens, token_counts, allocated_tokens):
        if allocated <= 0:
            continue
        if original_count <= allocated:
            truncated_texts.append("\n".join(page_lines))
        else:
            truncated_text = _truncate(page_lines, tokens, allocated)
            truncated_texts.append(truncated_text)

    return truncated_texts
```

#### 6.9.4 XML Tag Preservation During Truncation

**CRITICAL**: When truncating content, preserve XML tags (e.g., `<page_1>`, `</page_1>`):

```python
def _is_xml_tag(line: str) -> bool:
    """Check if line is an XML tag."""
    stripped = line.strip()
    return stripped.startswith("<") and stripped.endswith(">") and len(stripped) > 2

def _truncate(page_lines: List[str], tokens: List[int], max_tokens: int) -> str:
    """
    Truncate page content while preserving XML tags.

    Algorithm:
    1. Identify opening and closing tags
    2. Reserve tokens for tags
    3. Truncate content to fit remaining token budget
    4. Reconstruct with tags intact
    """
    enc = _get_encoder()
    if not page_lines:
        truncated_tokens = tokens[:max_tokens]
        return enc.decode(truncated_tokens)

    first_line = page_lines[0]
    last_line = page_lines[-1] if len(page_lines) > 1 else ""
    has_opening_tag = _is_xml_tag(first_line)
    has_closing_tag = len(page_lines) > 1 and _is_xml_tag(last_line)

    if not (has_opening_tag and has_closing_tag):
        # No tags to preserve, simple truncation
        truncated_tokens = tokens[:max_tokens]
        return enc.decode(truncated_tokens)

    opening_tag = first_line
    closing_tag = last_line
    content_lines = page_lines[1:-1] if len(page_lines) > 2 else []

    # Calculate token budget for tags
    opening_tokens = enc.encode(opening_tag)
    closing_tokens = enc.encode(closing_tag)
    newline_token = enc.encode("\n")
    tag_tokens = len(opening_tokens) + len(closing_tokens) + len(newline_token)
    if content_lines:
        tag_tokens += len(newline_token)

    if max_tokens <= tag_tokens:
        return opening_tag

    # Truncate content to fit
    content_max_tokens = max_tokens - tag_tokens
    content = "\n".join(content_lines)
    content_tokens = enc.encode(content)

    if len(content_tokens) <= content_max_tokens:
        return "\n".join(page_lines)

    truncated_content_tokens = content_tokens[:content_max_tokens]
    truncated_content = enc.decode(truncated_content_tokens)

    return f"{opening_tag}\n{truncated_content}\n{closing_tag}"
```

---

## 7. Prompt Engineering

### 7.1 Prompt Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM PROMPT                            │
├─────────────────────────────────────────────────────────────┤
│ 1. Role & Objective                                         │
│    - Expert Logistics Content Digitization Specialist       │
│                                                             │
│ 2. Task Description                                         │
│    - Analyze → Extract → Verify workflow                    │
│                                                             │
│ 3. Source Mapping Protocol (CRITICAL)                       │
│    - Block ID formats for PDF vs Excel                      │
│    - Value vs Label rule (anti-hallucination)               │
│    - Granularity requirements                               │
│                                                             │
│ 4. Extraction Constraints                                   │
│    - Optional fields handling                               │
│    - Data source structure                                  │
│                                                             │
│ 5. Custom Instructions (from config)                        │
│    - Task description                                       │
│    - Data mapping                                           │
│    - Extra instructions                                     │
│                                                             │
│ 6. Few-Shot Example (from RAG)                             │
│    - Input: plain text + text blocks                        │
│    - Output: expected JSON with data_source                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     USER PROMPT                             │
├─────────────────────────────────────────────────────────────┤
│ # Begin Extraction                                          │
│                                                             │
│ <document_1>                                                │
│ <name>booking_confirmation.pdf</name>                       │
│                                                             │
│ <plain_text_input>                                          │
│ [Page 1] Booking No: 123456 | Vessel: MOCK VESSEL...       │
│ </plain_text_input>                                         │
│                                                             │
│ <text_block_input>                                          │
│ <page_1>                                                    │
│ [{"id":"1.1.1:1:1","text":"Booking No:","x_center":100}...] │
│ </page_1>                                                   │
│ </text_block_input>                                         │
│                                                             │
│ </document_1>                                               │
│                                                             │
│ Now, please perform the extraction task...                  │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Default Prompts

**Location**: `app/src/app/prompt/default_digitization_prompt.py`

#### 7.2.1 Role & Objective

```python
DEFAULT_ROLE_AND_OBJECTIVE = """# Role & Objective

You are an expert **Logistics Content Digitization Specialist**. Your task is to extract structured data from the provided text blocks on the given schema.
"""
```

#### 7.2.2 Task Description

```python
DEFAULT_TASK_DESCRIPTION = """
Follow these 3 steps strictly:
1.  **Analyze**: Understand target output structure and related source content based on given example(s).
2.  **Extract**: Extract all fields into valid JSON within one tool call. **Every** extracted value must include a specific `data_source` object.
    - _Self-Correction_: Before finalizing, cross-check against the "Extra Instruction" section below (if applicable).
3.  **Verify**: Double-check array structures to avoid duplicates and hallucinations (if applicable).
"""
```

#### 7.2.3 Source Mapping Protocol (Anti-Hallucination)

```python
DEFAULT_SOURCE_MAPPING_PROTOCOL = """# CRITICAL: Source Mapping Protocol

> **You must strictly adhere to these rules to prevent hallucinations.**

**1. Detect Input Format & Apply ID Rule**

> Check the input data format and apply the corresponding ID rule STRICTLY:

- **Scenario A: OCR/PDF Document (Text Blocks)**
  - **ID Format**: `{document}.{page}.{row}:{column}:{id}`
  - **Example**: `"1.2.3:1:5"` (Doc 1, Page 2, Grid Pos 3:1, Block 5)
- **Scenario B: Spreadsheet/Excel (Cells)**
  - **ID Format**: `{document}.{sheet}.{cell/cell_range}`
  - **Example (Single Cell)**: `"1.1.A1"`
  - **Example (Merged)**: `"1.1.B2:C2"`

**2. Value vs. Label Rule (Anti-Hallucination)**
- **Target the Value**: The `data_source.block_id` must point to the specific location containing the **ACTUAL VALUE**, not the header/label.
  - Label block `"1.1.1:1:1"`says "Booking No:", Value block `"1.1.1:2:2"` says "123". Source = Block `"1.1.1:2:2"`.
  - Cell `"1.1.A1"` says "Booking No:", Cell `"1.1.A2"` says "123". Source = `"1.1.A2"`.

**3. Granularity**
- For **Arrays/Objects**, provide `data_source` for **EACH individual field**, not for the container object.
- If a value spans multiple blocks/cells, use the ID of the **primary source** (or the range for Excel).
"""
```

### 7.3 Token Optimization

#### 7.3.1 Text Deduplication

**Location**: `app/src/app/prompt/prompt_engine.py`

```python
SIMILARITY_THRESHOLD = 0.98

def _deduplicate_rows(text_input: str) -> str:
    """
    Remove duplicate rows using tiktoken-based Jaccard similarity.

    Algorithm:
    1. Split text into rows
    2. For each row, tokenize with tiktoken
    3. Compare with previously seen rows using Jaccard similarity
    4. Skip rows with similarity >= 98%
    """
    enc = tiktoken.encoding_for_model("gpt-4o")
    seen_rows = []

    for row in rows:
        row_text = row.strip()
        if not row_text:
            continue

        # Check similarity with all seen rows
        is_duplicate = any(
            _calculate_row_similarity(row_text, seen, enc) >= SIMILARITY_THRESHOLD
            for seen in seen_rows
        )

        if not is_duplicate:
            seen_rows.append(row_text)

    return "\n".join(seen_rows)

def _calculate_row_similarity(n1: str, n2: str, enc) -> float:
    """Calculate Jaccard similarity using tiktoken tokens."""
    tokens1 = set(enc.encode(n1))
    tokens2 = set(enc.encode(n2))
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    return intersection / union if union > 0 else 0.0
```

#### 7.3.2 TOON Format

The system uses **TOON format** for compact representation of bounding boxes:

```python
from toon_format import encode

# Instead of verbose JSON:
# [{"id":"1.1.1:1:1","text":"Booking","x_center":100.5,"y_center":50.0,"width":80.0,"height":12.0}]

# TOON produces compact representation:
# id|text|x_center|y_center|width|height
# 1.1.1:1:1|Booking|100.5|50|80|12
```

#### 7.3.3 Partial Content Metadata

For RAG examples, only include text blocks that were actually used in the extraction:

```python
async def build_partial_content_metadata(
    self,
    source_content_metadata: SourceContentMetadata,
    result: dict
) -> SourceContentMetadata | None:
    """
    Build partial content metadata containing only blocks referenced in result.

    1. Extract all block_ids from result.data_source fields
    2. For each page, keep only blocks with matching IDs
    3. Add context window (±1 block) for context
    """
```

---

## 8. LLM Integration

### 8.1 OpenAI Service

**Location**: `app/src/app/llm/openai_service.py`

```python
class OpenAIService:
    # Supported models
    MODEL_GPT_4O = "gpt-4o"
    MODEL_GPT_4O_MINI = "gpt-4o-mini"
    MODEL_GPT_5_1 = "gpt-5.1"
    MODEL_GPT_5_MINI = "gpt-5-mini"

    # Models supporting reasoning_effort parameter
    REASONING_MODELS = {MODEL_GPT_5_1, MODEL_GPT_5, MODEL_GPT_5_MINI}
```

### 8.2 Structured Output Generation

```python
async def generate_digitization_structured_output(
    self,
    system_prompt: str,
    user_prompt: str,
    schema_id: SchemaIdentifier,
    file_ids: List[str],
    model: str = "gpt-4o-mini",
    reasoning_effort: Literal["none", "low", "medium", "high"] | None = None,
    service_tier: Literal["standard", "flex"] = "standard",
    base64_images: list[dict] | None = None,
) -> dict:
    """
    Generate structured output using LangChain's with_structured_output.

    Key features:
    1. Load Pydantic model from schema_id
    2. Use LangChain's .with_structured_output() for JSON schema enforcement
    3. Support file uploads (PDF) and base64 images
    4. Configure reasoning_effort for reasoning models
    5. Configure service_tier (flex = 50% cost reduction)
    """
    schema_model = await self.schema_manager.get_model(schema_id)

    # Build message content with files/images
    content_items = [{"type": "text", "text": user_prompt}]
    content_items.extend([{"type": "file", "file": {"file_id": fid}} for fid in file_ids])
    content_items.extend([
        {"type": "image_url", "image_url": {"url": f"data:{img['mime_type']};base64,{img['base64']}"}}
        for img in (base64_images or [])
    ])

    # Get client with structured output
    structured_client = self.get_client_with_model(model).with_structured_output(schema_model)

    # Configure reasoning and tier
    extra_body = {}
    if service_tier == "flex":
        extra_body["service_tier"] = "flex"
    if reasoning_effort and model in self.REASONING_MODELS:
        extra_body["reasoning_effort"] = reasoning_effort
    if extra_body:
        structured_client = structured_client.bind(extra_body=extra_body)

    # Invoke with timeout
    timeout = 1200.0 if service_tier == "flex" else 120.0
    result = await asyncio.wait_for(
        structured_client.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_items},
        ]),
        timeout=timeout,
    )

    return result.model_dump()
```

### 8.3 Embedding Generation

```python
def create_embeddings(self, text: str) -> list[float]:
    """
    Create embeddings using OpenAI's text-embedding-3-small model.

    - Model: text-embedding-3-small
    - Dimensions: 1536
    - Max tokens: 8192 (auto-truncated)
    """
    text = self.truncate_text(text, max_tokens=8192)
    response = self.openai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding  # 1536-dim vector
```

### 8.4 File Upload for Vision

```python
def _prepare_files_for_llm(
    self,
    file_paths: List[str],
    file_upload_enabled: bool,
    pdf_to_image_enabled: bool
) -> tuple[list[str], list[dict]]:
    """
    Prepare files for LLM consumption.

    Options:
    1. file_upload_enabled=False: Don't upload files (use text extraction only)
    2. file_upload_enabled=True, pdf_to_image_enabled=False: Upload PDF to OpenAI
    3. file_upload_enabled=True, pdf_to_image_enabled=True: Convert PDF pages to base64 images
    """
```

---

## 9. Feedback Loop & Training Data

### 9.1 Feedback Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  Human Review UI                            │
│  (External system - not part of this platform)              │
└──────────────────────────┬──────────────────────────────────┘
                           │ SubmitDigiFlowResultFeedback
                           │ (gRPC)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           DigiFlowFeedbackManagementService                 │
│  Location: service/digi_flow_feedback_management_service.py │
├─────────────────────────────────────────────────────────────┤
│  1. Validate corrected result                               │
│  2. Create field-level audit records                        │
│  3. Update digi_flow_result with new data                   │
│  4. Send feedback to LangSmith (optional)                   │
│  5. Create RAG training data task                           │
└──────────────────────────┬──────────────────────────────────┘
                           │ SQS Message
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              RAG Training Data Task Queue                   │
│  Queue: rag_training_data_task_queue                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           RAGTrainingDataManagementService                  │
│  Location: service/rag_training_data_management_service.py  │
├─────────────────────────────────────────────────────────────┤
│  Process task:                                              │
│  - ADD: Generate training vector and store                  │
│  - REMOVE: Delete training vector                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              RAGTrainingDataGenerator                       │
│  Location: service/training_data/rag_training_data_generator.py
├─────────────────────────────────────────────────────────────┤
│  1. Build weighted embedding text from document             │
│  2. Generate 1536-dim embedding via OpenAI                  │
│  3. Build reference_input (plain text + partial blocks)     │
│  4. Build reference_output (corrected data)                 │
│  5. Create RAGTrainingDataVector and store                  │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Feedback Processing

```python
async def process_feedback(
    self,
    digi_flow_id: int,
    corrected_result: dict,
    field_mapping_feedback: list[dict],
    feedback_source: FeedbackSource,
    audited_by: Actor,
    mark_as_correct: bool = False,
) -> DigiFlowResult:
    """
    Process feedback submission.

    1. Get existing result
    2. Compare with corrected result to find changes
    3. Create field audit records for each change
    4. Update result with corrected data
    5. Create RAG training data task (async via SQS)
    """
```

### 9.3 Field Audit Record

```python
class DigiFlowResultFieldAudit(SQLModel, table=True):
    id: int
    flow_id: int
    result_id: int
    result_version: int
    field_path: str              # JSON path, e.g., "booking_number.value"
    old_value: dict | None       # Previous value
    new_value: dict | None       # Corrected value
    reason_code: AuditReasonCode # INCORRECT, MISSING, EXTRA, etc.
    audited_at: datetime
    audited_by: Actor
```

### 9.4 Training Data Generation

```python
async def build_training_vector(
    self,
    digi_flow: DigiFlow,
    result: DigiFlowResult,
    source_content_context: SourceContentContextType,
    source_content_metadata: SourceContentMetadata,
    context_idx: int,
) -> RAGTrainingDataVector:
    """
    Build a single RAG training data vector.

    1. Build embedding text:
       - Extract plain text from pages
       - Wrap with labels: <page_1>...</page_1>
       - Build weighted text (prioritize first/last pages)

    2. Generate embedding (1536-dim)

    3. Build reference_input:
       - name: file name
       - deduplicated_plain_text: formatted plain text
       - partial_content_metadata: only blocks used in result

    4. Build reference_output:
       - output_data: corrected extraction result

    5. Create vector:
       - flow_id, config_id, schema_id, result_id
       - source_content_context
       - reference_input, reference_output
       - embedding
    """
```

### 9.5 Reference Input Structure

```python
class ReferenceInput(BaseModel):
    name: str | None                    # File name
    deduplicated_plain_text: str        # Formatted: <plain_text_input>...</plain_text_input>
    partial_content_metadata: str       # Formatted: <input_text_block>...</input_text_block>
```

Example:

```xml
<plain_text_input>

<page_1>
Booking No: 123456 | Vessel: MOCK VESSEL | ETD: 2025-01-15
</page_1>

</plain_text_input>

<input_text_block>

<page_1>
id|text|x_center|y_center|width|height
1.1.1:1:1|Booking No:|100|50|80|12
1.1.1:2:2|123456|200|50|60|12
</page_1>

</input_text_block>
```

---

## 10. API & gRPC Services

### 10.1 gRPC Service Definition

**Location**: `app/src/app/grpc/server/service/digitization_platform_service.py`

```protobuf
service DigitizationPlatformAPI {
    // Schema Management
    rpc GetDigiFlowSchema(GetDigiFlowSchemaRequest) returns (GetDigiFlowSchemaResponse);
    rpc SaveDigiFlowSchema(SaveDigiFlowSchemaRequest) returns (SaveDigiFlowSchemaResponse);
    rpc SetDigiFlowSchemaStatus(SetDigiFlowSchemaStatusRequest) returns (SetDigiFlowSchemaStatusResponse);
    rpc ListDigiFlowSchema(ListDigiFlowSchemaRequest) returns (ListDigiFlowSchemaResponse);
    rpc PreviewDigiFlowSchema(PreviewDigiFlowSchemaRequest) returns (PreviewDigiFlowSchemaResponse);

    // Config Management
    rpc GetDigiFlowConfig(GetDigiFlowConfigRequest) returns (GetDigiFlowConfigResponse);
    rpc SaveDigiFlowConfig(SaveDigiFlowConfigRequest) returns (SaveDigiFlowConfigResponse);
    rpc SetDigiFlowConfigStatus(SetDigiFlowConfigStatusRequest) returns (SetDigiFlowConfigStatusResponse);
    rpc ListDigiFlowConfigs(ListDigiFlowConfigsRequest) returns (ListDigiFlowConfigsResponse);

    // DigiFlow Operations
    rpc CreateDigiFlow(CreateDigiFlowRequest) returns (CreateDigiFlowResponse);
    rpc GetDigiFlow(GetDigiFlowRequest) returns (GetDigiFlowResponse);
    rpc GetDigiFlowResult(GetDigiFlowResultRequest) returns (GetDigiFlowResultResponse);

    // Feedback
    rpc SubmitDigiFlowResultFeedback(SubmitDigiFlowResultFeedbackRequest) returns (SubmitDigiFlowResultFeedbackResponse);
    rpc SubmitDigiFlowValidationResult(SubmitDigiFlowValidationResultRequest) returns (SubmitDigiFlowValidationResultResponse);

    // Schema Validation
    rpc SchemaValidation(SchemaValidationRequest) returns (SchemaValidationResponse);
}
```

### 10.2 Key API Operations

#### 10.2.1 CreateDigiFlow

Creates a new digitization task:

```python
async def CreateDigiFlow(self, request: CreateDigiFlowRequest, context) -> CreateDigiFlowResponse:
    """
    Create new digitization task.

    Request:
    - config_id or config_slug: Which extraction config to use
    - document_context: Files to process
    - actor: Who is creating this task

    Response:
    - digi_flow: Created task with ID

    Flow:
    1. Load config by ID or slug
    2. Create digi_flow record
    3. Publish task to SQS queue for async processing
    4. Return immediately with flow ID
    """
```

#### 10.2.2 SubmitDigiFlowResultFeedback

Process human corrections:

```python
async def SubmitDigiFlowResultFeedback(
    self,
    request: SubmitDigiFlowResultFeedbackRequest,
    context
) -> SubmitDigiFlowResultFeedbackResponse:
    """
    Submit human corrections to extraction result.

    Request:
    - digi_flow_id: Which flow to update
    - corrected_result: Full corrected JSON
    - field_mapping_feedback: Per-field correction reasons
    - feedback_source: UI, API, AUTO
    - mark_as_correct: Whether to generate training data

    Processing:
    1. Validate corrected result against schema
    2. Diff with existing result
    3. Create field audit records
    4. Update result
    5. If mark_as_correct: create RAG training task
    """
```

### 10.3 FastAPI HTTP Endpoints

**Location**: `app/src/app/api/`

```python
# Health check
@router.get("/health")
async def health():
    return {"status": "healthy"}

# Metrics endpoint for Datadog
@router.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

---

## 11. Message Queue Architecture

### 11.1 SQS Queues

| Queue | Purpose | Consumer |
|-------|---------|----------|
| `digitization_task_dispatcher_queue` | Async workflow execution | `DigitizationTaskConsumer` |
| `rag_training_data_task_queue` | Training data generation | `RAGTrainingDataTaskConsumer` |

### 11.2 Digitization Task Flow

```python
# Publisher (when CreateDigiFlow is called)
async def publish_digitization_task(flow_id: int):
    message = {
        "flow_id": flow_id,
        "retry_count": 0,
    }
    await sqs_publisher.publish(
        queue_name="digitization_task_dispatcher_queue",
        message=message,
    )

# Consumer
class DigitizationTaskConsumer:
    async def process(self, message: dict):
        flow_id = message["flow_id"]
        retry_count = message.get("retry_count", 0)

        try:
            await self.workflow_controller.run_digitization_workflow(id=flow_id)
        except RetriableError as e:
            if retry_count < 3:
                # Re-queue with incremented retry count
                await self.republish_with_delay(flow_id, retry_count + 1)
            else:
                await self.mark_failed(flow_id, str(e))
```

### 11.3 RAG Training Data Task Flow

```python
class RAGTrainingDataTaskType(str, Enum):
    ADD = "ADD"       # Generate and store training vector
    REMOVE = "REMOVE" # Delete training vector

# Publisher (when feedback is marked as correct)
async def create_rag_training_data_task(
    flow_id: int,
    config_id: int,
    task_type: RAGTrainingDataTaskType,
):
    await sqs_publisher.publish(
        queue_name="rag_training_data_task_queue",
        message={
            "flow_id": flow_id,
            "config_id": config_id,
            "task_type": task_type.value,
        },
    )

# Consumer
class RAGTrainingDataTaskConsumer:
    async def process(self, message: dict):
        if message["task_type"] == "ADD":
            await self._process_add_task(message)
        elif message["task_type"] == "REMOVE":
            await self._process_remove_task(message)

    async def _process_add_task(self, message: dict):
        # Load digi_flow and result
        # Generate training vector
        # Store in rag_training_data_vector table
        pass
```

---

## 12. Schema Management

### 12.1 YAML Schema Definition

Schemas are defined in YAML for human readability, then converted to JSON Schema for validation:

```yaml
# Example: Shipping Order Schema
booking_number:
  type: string
  description: The booking confirmation number

vessel_name:
  type: string
  description: Name of the vessel

voyage_number:
  type: string
  description: Voyage identifier

containers:
  type: array
  description: List of containers in the booking
  items:
    container_number:
      type: string
    size_type:
      type: string
    quantity:
      type: integer
```

### 12.2 Schema Conversion

**Location**: `app/src/app/schema/yaml_to_pydantic_converter.py`

```python
class YamlToPydanticConverter:
    def yaml_schema_to_pydantic(self, yaml_schema: dict) -> Type[BaseModel]:
        """
        Convert YAML schema to Pydantic model.

        Features:
        1. Wrap each field with FieldValueWithSource:
           - value: The actual extracted value
           - data_source: { block_id: str }

        2. Support nested objects and arrays

        3. Generate JSON Schema for LLM structured output
        """
```

### 12.3 FieldValueWithSource Wrapper

Every extracted field is wrapped with data source tracking:

```python
class DataSource(BaseModel):
    block_id: str  # e.g., "1.2.3:1:5"

class FieldValueWithSource(BaseModel, Generic[T]):
    value: T
    data_source: DataSource
```

Example output:

```json
{
  "booking_number": {
    "value": "123456",
    "data_source": {
      "block_id": "1.1.1:2:2"
    }
  },
  "containers": [
    {
      "container_number": {
        "value": "ABCD1234567",
        "data_source": {
          "block_id": "1.2.5:1:10"
        }
      }
    }
  ]
}
```

---

## 13. Observability & Monitoring

### 13.1 LangSmith Integration

Every workflow execution is traced in LangSmith using `@traceable` decorators.

#### 13.1.1 Basic @traceable Usage

```python
from langsmith import traceable, get_current_run_tree

@traceable(name="ExecuteFileDigitization")
async def execute(self, context: ExecutorContext) -> ExecutorContext:
    # Automatically traces:
    # - Input parameters
    # - LLM calls (prompts, responses, tokens)
    # - Output results
    # - Latency

    trace_run = get_current_run_tree()
    # Store trace_id in database for linking
    context.langsmith_trace_id = trace_run.id
```

#### 13.1.2 Custom Input/Output Processing

**IMPORTANT**: Use `process_inputs` and `process_outputs` to control what gets traced (avoid logging large payloads):

```python
def _process_deduplicate_input(inputs: dict) -> dict:
    """Process input for deduplicate trace - avoid logging full content."""
    source_content_metadata = inputs.get("source_content_metadata")
    block_count = _count_blocks(source_content_metadata) if source_content_metadata else 0
    has_pruned = bool(source_content_metadata.pruned_content_metadata if source_content_metadata else None)
    return {
        "input_block_count": block_count,
        "has_pruned_content_metadata": has_pruned,
    }

def _process_deduplicate_output(outputs: SourceContentMetadata) -> dict:
    """Process output for deduplicate trace."""
    output_block_count = _count_blocks(outputs) if outputs else 0
    has_pruned = bool(outputs.pruned_content_metadata if outputs else None)
    return {
        "output_block_count": output_block_count,
        "has_pruned_content_metadata": has_pruned,
    }

@traceable(
    name="DeduplicateTextBlocks",
    process_inputs=_process_deduplicate_input,
    process_outputs=_process_deduplicate_output,
)
async def deduplicate_text_blocks(
    source_content_metadata: SourceContentMetadata
) -> SourceContentMetadata:
    # Implementation
    pass
```

#### 13.1.3 Functions That MUST Have @traceable

Apply `@traceable` to these key functions:

| Function | Module | Trace Name |
|----------|--------|------------|
| `execute` | `file_digitization_executor.py` | `ExecuteFileDigitization` |
| `build_system_prompt` | `prompt_engine.py` | `BuildSystemPrompt` |
| `build_user_prompt` | `prompt_engine.py` | `BuildUserPrompt` |
| `build_example` | `file_rag_provider_v2.py` | `BuildRAGExample` |
| `deduplicate_text_blocks` | `prompt_engine.py` | `DeduplicateTextBlocks` |
| `prune` | `pdf_pruner.py` | `PrunePDFPages` |
| `extract` | `pdf_extractor.py` | `ExtractPDFContent` |
| `extract` | `excel_extractor.py` | `ExtractExcelContent` |
| `generate_embeddings` | `embedding_service.py` | `GenerateEmbeddings` |
| `_llm_invoke` | `llm_service.py` | `LLMInvoke` |

#### 13.1.4 LangSmith Configuration

```python
# Environment variables required
LANGSMITH_API_KEY = "lsv2_pt_..."
LANGSMITH_PROJECT = "digitization-platform"
LANGSMITH_TRACING_V2 = "true"

# Import and use
from langsmith import traceable

# Tracing is automatically enabled when environment variables are set
```

### 13.2 Datadog Metrics

**Location**: `app/src/app/core/utils/metrics.py`

```python
from datadog import statsd

def increment(metric_name: str, tags: list[str] = []):
    statsd.increment(metric_name, tags=tags)

def histogram(metric_name: str, value: float, tags: list[str] = []):
    statsd.histogram(metric_name, value, tags=tags)

# Usage
metrics.increment("digitization.workflow.completed", tags=["config:shipping_order"])
metrics.histogram("rag.distance", value=0.15, tags=["config:shipping_order"])
```

### 13.3 Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `digitization.workflow.started` | Counter | Workflows initiated |
| `digitization.workflow.completed` | Counter | Successful completions |
| `digitization.workflow.failed` | Counter | Failed workflows |
| `digitization.workflow.duration` | Histogram | End-to-end latency |
| `rag.search_similar_examples` | Counter | RAG searches (has_similar tag) |
| `rag.distance` | Histogram | Cosine distance of matches |
| `pdf.extraction.text_blocks_count` | Histogram | Text blocks per PDF |
| `pdf.extraction.images_count` | Histogram | Images per PDF |

### 13.4 Sentry Error Tracking

```python
import sentry_sdk

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT,
    traces_sample_rate=0.1,
)
```

---

## 14. Deployment Configuration

### 14.1 Docker Configuration

**Location**: `app/Dockerfile`

```dockerfile
# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy source
COPY src ./src

# Runtime stage
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src ./src

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Expose ports
EXPOSE 80 50060

# Run
CMD ["python", "-m", "app.main"]
```

### 14.2 Docker Compose (Local Development)

**Location**: `app/docker-compose.yml`

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:80"
      - "50060:50060"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/digitization
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - db
      - localstack

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: digitization
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  localstack:
    image: localstack/localstack
    ports:
      - "4566:4566"
    environment:
      - SERVICES=sqs,s3
      - DEFAULT_REGION=us-west-2

  flyway:
    image: flyway/flyway
    command: migrate
    volumes:
      - ./migrations:/flyway/sql
    environment:
      - FLYWAY_URL=jdbc:postgresql://db:5432/digitization
      - FLYWAY_USER=postgres
      - FLYWAY_PASSWORD=postgres
    depends_on:
      - db

volumes:
  postgres_data:
```

### 14.3 Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/digitization

# OpenAI
OPENAI_API_KEY=sk-...

# AWS
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-west-2

# SQS Queues
SQS_DIGITIZATION_TASK_QUEUE_URL=https://sqs.../digitization_task_dispatcher_queue
SQS_RAG_TRAINING_DATA_TASK_QUEUE_URL=https://sqs.../rag_training_data_task_queue

# LangSmith
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=digitization-platform

# Monitoring
SENTRY_DSN=...
DD_AGENT_HOST=...

# Feature Flags
MOCK_OPENAI_RESPONSE=false
```

### 14.4 OCR Service

**Location**: `ocr/`

The OCR service is a separate microservice running PaddleOCR:

```dockerfile
# ocr/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install PaddleOCR dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir paddleocr paddlepaddle grpcio

COPY src ./src

EXPOSE 50061

CMD ["python", "-m", "ocr.server"]
```

---

## 15. OCR Processing Service

### 15.1 Overview

The OCR service extracts text from images (standalone or embedded in PDFs) using PaddleOCR PP-OCRv5. It runs as either an embedded service or standalone microservice.

### 15.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       OCR Service                            │
│  Location: app/src/app/service/workflow/content_normalizer/ │
│            ocr/ocr_service.py                                │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Singleton OCR Engine                        ││
│  │  - PaddleOCR PP-OCRv5 with ONNX runtime                 ││
│  │  - Language detection (CJK support)                      ││
│  │  - Concurrency limiting via semaphore                    ││
│  └─────────────────────────────────────────────────────────┘│
│                            │                                 │
│  ┌─────────────────────────▼───────────────────────────────┐│
│  │            Image Preprocessing Pipeline                  ││
│  │  - Rotation correction (deskew)                          ││
│  │  - Contrast enhancement                                  ││
│  │  - Noise reduction                                       ││
│  │  - Resolution normalization                              ││
│  └─────────────────────────────────────────────────────────┘│
│                            │                                 │
│  ┌─────────────────────────▼───────────────────────────────┐│
│  │           Coordinate Transformation                      ││
│  │  - OCR coords → PDF page coords                          ││
│  │  - Scale factor calculation                              ││
│  │  - Origin offset handling                                ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 15.3 OCR Service Implementation

**Location**: `app/src/app/service/workflow/content_normalizer/ocr/ocr_service.py`

```python
import asyncio
from typing import Optional, List
from pathlib import Path

# PaddleOCR imports
from paddleocr import PaddleOCR

class OCRRegion:
    """Represents a single OCR detection result."""
    text: str
    confidence: float
    bounding_box: "OCRBoundingBox"

class OCRBoundingBox:
    """Bounding box from OCR detection."""
    top_left: tuple[float, float]      # (x, y)
    top_right: tuple[float, float]
    bottom_right: tuple[float, float]
    bottom_left: tuple[float, float]

class OCRResult:
    """Complete OCR result for an image."""
    regions: List[OCRRegion]
    image_width: int
    image_height: int

class OCRService:
    """
    Singleton OCR service using PaddleOCR PP-OCRv5.

    Features:
    - Singleton pattern ensures single model load
    - Semaphore-limited concurrency (prevents OOM)
    - Multi-language support (CJK + Latin)
    - ONNX runtime for CPU efficiency
    """

    _instance: Optional["OCRService"] = None
    _lock = asyncio.Lock()

    # Configuration
    MAX_CONCURRENT_OCR = 3  # Limit concurrent OCR operations
    USE_ANGLE_CLS = True    # Enable text angle classification
    USE_GPU = False         # CPU-only by default

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_OCR)
        self._ocr_engine: Optional[PaddleOCR] = None
        self._initialized = True

    def _get_or_create_engine(self) -> PaddleOCR:
        """Lazy initialization of PaddleOCR engine."""
        if self._ocr_engine is None:
            self._ocr_engine = PaddleOCR(
                use_angle_cls=self.USE_ANGLE_CLS,
                lang="en",  # Default, can be overridden
                use_gpu=self.USE_GPU,
                show_log=False,
                # PP-OCRv5 model paths (auto-downloaded)
                det_model_dir=None,  # Use default PP-OCRv5 detection
                rec_model_dir=None,  # Use default PP-OCRv5 recognition
                cls_model_dir=None,  # Use default angle classifier
            )
        return self._ocr_engine

    async def ocr(
        self,
        image_path: str,
        language: str = "en",
    ) -> OCRResult:
        """
        Perform OCR on an image file.

        Args:
            image_path: Path to image file
            language: Language code (en, ch, japan, korean, etc.)

        Returns:
            OCRResult with detected text regions
        """
        async with self._semaphore:
            # Run in executor to avoid blocking
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._ocr_sync,
                image_path,
                language,
            )

    def _ocr_sync(self, image_path: str, language: str) -> OCRResult:
        """Synchronous OCR execution."""
        engine = self._get_or_create_engine()

        # Execute OCR
        result = engine.ocr(image_path, cls=self.USE_ANGLE_CLS)

        if not result or not result[0]:
            return OCRResult(regions=[], image_width=0, image_height=0)

        # Parse results
        regions = []
        for line in result[0]:
            box, (text, confidence) = line

            # box is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            region = OCRRegion(
                text=text,
                confidence=confidence,
                bounding_box=OCRBoundingBox(
                    top_left=tuple(box[0]),
                    top_right=tuple(box[1]),
                    bottom_right=tuple(box[2]),
                    bottom_left=tuple(box[3]),
                ),
            )
            regions.append(region)

        return OCRResult(
            regions=regions,
            image_width=0,  # Set from image if needed
            image_height=0,
        )


# Module-level singleton instance
ocr_service = OCRService()
```

### 15.4 Image Preprocessing

**Location**: `app/src/app/service/workflow/content_normalizer/ocr/image_preprocessor.py`

```python
import cv2
import numpy as np
from pathlib import Path

class ImagePreprocessor:
    """
    Preprocesses images before OCR for better accuracy.

    Preprocessing steps:
    1. Grayscale conversion
    2. Noise reduction (Gaussian blur)
    3. Contrast enhancement (CLAHE)
    4. Deskew (rotation correction)
    5. Resolution normalization
    """

    # Configuration
    TARGET_DPI = 300
    CLAHE_CLIP_LIMIT = 2.0
    CLAHE_TILE_SIZE = (8, 8)
    GAUSSIAN_KERNEL = (3, 3)

    def preprocess(self, image_path: str) -> str:
        """
        Preprocess image for OCR.

        Args:
            image_path: Path to original image

        Returns:
            Path to preprocessed image (temp file)
        """
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            return image_path

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur for noise reduction
        blurred = cv2.GaussianBlur(gray, self.GAUSSIAN_KERNEL, 0)

        # Apply CLAHE for contrast enhancement
        clahe = cv2.createCLAHE(
            clipLimit=self.CLAHE_CLIP_LIMIT,
            tileGridSize=self.CLAHE_TILE_SIZE
        )
        enhanced = clahe.apply(blurred)

        # Deskew if needed
        deskewed = self._deskew(enhanced)

        # Save to temp file
        output_path = Path(image_path).parent / f"preprocessed_{Path(image_path).name}"
        cv2.imwrite(str(output_path), deskewed)

        return str(output_path)

    def _deskew(self, image: np.ndarray, max_angle: float = 10.0) -> np.ndarray:
        """
        Correct image skew using Hough transform.

        Args:
            image: Grayscale image
            max_angle: Maximum rotation angle to correct

        Returns:
            Deskewed image
        """
        # Edge detection
        edges = cv2.Canny(image, 50, 150, apertureSize=3)

        # Hough line detection
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)

        if lines is None:
            return image

        # Calculate average angle
        angles = []
        for line in lines[:20]:  # Use first 20 lines
            rho, theta = line[0]
            angle = np.degrees(theta) - 90
            if abs(angle) < max_angle:
                angles.append(angle)

        if not angles:
            return image

        avg_angle = np.median(angles)

        # Rotate image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, avg_angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )

        return rotated
```

### 15.5 Coordinate Transformation

```python
def transform_ocr_coords_to_pdf(
    ocr_bbox: OCRBoundingBox,
    pdf_image_rect: tuple[float, float, float, float],
    image_width: int,
    image_height: int,
) -> BoundingBox:
    """
    Transform OCR coordinates to PDF page coordinates.

    Args:
        ocr_bbox: Bounding box from OCR (image coordinates)
        pdf_image_rect: (x0, y0, x1, y1) position of image on PDF page
        image_width: Original image width in pixels
        image_height: Original image height in pixels

    Returns:
        BoundingBox in PDF page coordinates
    """
    x0, y0, x1, y1 = pdf_image_rect

    # Calculate scale factors
    pdf_width = x1 - x0
    pdf_height = y1 - y0
    scale_x = pdf_width / image_width
    scale_y = pdf_height / image_height

    # Transform coordinates
    # OCR gives 4 corners, we use top_left and bottom_right
    top_left_x = ocr_bbox.top_left[0] * scale_x + x0
    top_left_y = ocr_bbox.top_left[1] * scale_y + y0
    bottom_right_x = ocr_bbox.bottom_right[0] * scale_x + x0
    bottom_right_y = ocr_bbox.bottom_right[1] * scale_y + y0

    return BoundingBox(
        id="",  # Assigned later
        raw_value="",  # Set from OCR text
        top_left_x=top_left_x,
        top_left_y=top_left_y,
        bottom_right_x=bottom_right_x,
        bottom_right_y=bottom_right_y,
    )
```

### 15.6 Image Extractor

**Location**: `app/src/app/service/workflow/content_normalizer/extractor/image_extractor.py`

```python
from pathlib import Path
from typing import List
from langsmith import traceable

from ..ocr.ocr_service import ocr_service, OCRResult
from ..ocr.image_preprocessor import ImagePreprocessor
from ...models import (
    BoundingBox,
    Page,
    PageContent,
    FileContentMetadata,
    FileContentType,
    SourceContentMetadata,
)


def _process_extract_input(inputs: dict) -> dict:
    """Process input for image extraction trace."""
    file_path = inputs.get("file_path", "")
    return {"file_path": str(file_path).split("/")[-1] if file_path else ""}


def _process_extract_output(output: SourceContentMetadata) -> dict:
    """Process output for image extraction trace."""
    if not output or not output.content_metadata:
        return {"region_count": 0}
    file_content = output.content_metadata.file_content
    if hasattr(file_content, "pages"):
        region_count = sum(len(p.bounding_box) for p in file_content.pages)
        return {"region_count": region_count}
    return {"region_count": 0}


class ImageExtractor:
    """
    Extracts text from image files using OCR.

    Supports: PNG, JPG, JPEG, TIFF, BMP, WEBP
    """

    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}

    def __init__(self):
        self.ocr_service = ocr_service
        self.preprocessor = ImagePreprocessor()

    @traceable(
        name="ExtractImageContent",
        process_inputs=_process_extract_input,
        process_outputs=_process_extract_output,
    )
    def extract(self, file_path: str) -> SourceContentMetadata:
        """
        Extract text content from image file.

        Args:
            file_path: Path to image file

        Returns:
            SourceContentMetadata with extracted text regions
        """
        path = Path(file_path)

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported image format: {path.suffix}")

        # Preprocess image
        preprocessed_path = self.preprocessor.preprocess(file_path)

        # Run OCR
        import asyncio
        ocr_result = asyncio.get_event_loop().run_until_complete(
            self.ocr_service.ocr(preprocessed_path)
        )

        # Convert to bounding boxes
        bboxes = self._convert_ocr_to_bboxes(ocr_result, doc_index=1, page_index=1)

        # Cluster into rows/columns and assign IDs
        from ..extractor.dbscan_clustering import cluster_into_coordinates
        coordinates = cluster_into_coordinates(bboxes)

        # Assign IDs based on coordinates
        for row_idx, col_idx, bbox in coordinates:
            bbox.id = f"1.1.{row_idx}:{col_idx}:{coordinates.index((row_idx, col_idx, bbox))}"

        # Build page content
        page = Page(
            id=1,
            width=ocr_result.image_width or 0,
            height=ocr_result.image_height or 0,
            bounding_box=[bbox for _, _, bbox in coordinates],
        )

        content_metadata = FileContentMetadata(
            index=1,
            file_object_fid="",
            file_name=path.name,
            file_bytes_size=path.stat().st_size,
            content_type=FileContentType.IMAGE,
            languages=["en"],  # Detect from OCR if needed
            file_content=PageContent(pages=[page]),
        )

        return SourceContentMetadata(
            content_metadata=content_metadata,
            pruned_content_metadata=None,
        )

    def _convert_ocr_to_bboxes(
        self,
        ocr_result: OCRResult,
        doc_index: int,
        page_index: int,
    ) -> List[BoundingBox]:
        """Convert OCR regions to BoundingBox objects."""
        bboxes = []

        for region in ocr_result.regions:
            bbox = BoundingBox(
                id="",  # Assigned after clustering
                raw_value=region.text,
                top_left_x=region.bounding_box.top_left[0],
                top_left_y=region.bounding_box.top_left[1],
                bottom_right_x=region.bounding_box.bottom_right[0],
                bottom_right_y=region.bounding_box.bottom_right[1],
            )
            bboxes.append(bbox)

        return bboxes


# Module-level instance
image_extractor = ImageExtractor()
```

---

## 16. Feedback Loop Infrastructure

### 16.1 Overview

The feedback loop enables continuous improvement through:
1. **Inline feedback submission** - Corrections to extraction results
2. **Field-level audit tracking** - Record what changed and why
3. **Training data generation** - Convert corrections to RAG examples
4. **LangSmith feedback sync** - Optional feedback to LLM provider

### 16.2 Feedback Submission Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    External Review UI                        │
│  (Human reviews and corrects extraction results)            │
└──────────────────────────┬──────────────────────────────────┘
                           │ SubmitDigiFlowResultFeedback (gRPC)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           DigiFlowFeedbackManagementService                 │
├─────────────────────────────────────────────────────────────┤
│  async def submit_inline_feedback(                           │
│      flow_id: int,                                           │
│      corrected_result: dict,                                 │
│      field_mapping_feedback: List[FieldFeedback],           │
│      feedback_source: FeedbackSource,                        │
│      actor: Actor,                                           │
│      mark_as_correct: bool = False,                          │
│  ):                                                          │
│      1. Load existing digi_flow and result                   │
│      2. Compute JSON diff between old and new                │
│      3. Create field-level audit records                     │
│      4. Update digi_flow_result with corrected data          │
│      5. If mark_as_correct: create RAG training task         │
│      6. Optionally sync feedback to LangSmith                │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Audit DB   │   │ Training    │   │  LangSmith  │
│  Records    │   │ Data Queue  │   │  Feedback   │
└─────────────┘   └─────────────┘   └─────────────┘
```

### 16.3 JSON Diff Computation

**Location**: `app/src/app/service/digi_flow_feedback_management_service.py`

```python
from typing import List, Tuple, Any
from deepdiff import DeepDiff
import json

class FieldChange:
    """Represents a single field change."""
    field_path: str           # JSON path, e.g., "booking_number.value"
    old_value: Any
    new_value: Any
    change_type: str          # "changed", "added", "removed"


def compute_json_diff(
    old_result: dict,
    new_result: dict,
) -> List[FieldChange]:
    """
    Compute detailed diff between old and new extraction results.

    Uses DeepDiff library for recursive comparison with path tracking.

    Args:
        old_result: Previous extraction result
        new_result: Corrected extraction result

    Returns:
        List of FieldChange objects describing each modification
    """
    diff = DeepDiff(old_result, new_result, view='tree')
    changes: List[FieldChange] = []

    # Process changed values
    for item in diff.get('values_changed', []):
        changes.append(FieldChange(
            field_path=_convert_path(item.path()),
            old_value=item.t1,
            new_value=item.t2,
            change_type="changed",
        ))

    # Process added items
    for item in diff.get('dictionary_item_added', []):
        changes.append(FieldChange(
            field_path=_convert_path(item.path()),
            old_value=None,
            new_value=item.t2,
            change_type="added",
        ))

    # Process removed items
    for item in diff.get('dictionary_item_removed', []):
        changes.append(FieldChange(
            field_path=_convert_path(item.path()),
            old_value=item.t1,
            new_value=None,
            change_type="removed",
        ))

    # Process array changes
    for item in diff.get('iterable_item_added', []):
        changes.append(FieldChange(
            field_path=_convert_path(item.path()),
            old_value=None,
            new_value=item.t2,
            change_type="added",
        ))

    for item in diff.get('iterable_item_removed', []):
        changes.append(FieldChange(
            field_path=_convert_path(item.path()),
            old_value=item.t1,
            new_value=None,
            change_type="removed",
        ))

    return changes


def _convert_path(deepdiff_path: str) -> str:
    """Convert DeepDiff path format to JSON path format."""
    # DeepDiff: root['field']['subfield'][0]['item']
    # JSON Path: field.subfield[0].item
    path = deepdiff_path.replace("root", "")
    path = path.replace("['", ".").replace("']", "")
    path = path.lstrip(".")
    return path
```

### 16.4 Audit Record Creation

```python
from datetime import datetime
from sqlmodel import SQLModel, Field
from typing import Optional

class DigiFlowResultFieldAudit(SQLModel, table=True):
    """
    Stores field-level audit records for each correction.

    Enables:
    - Tracking what was corrected and when
    - Analytics on error patterns
    - Quality monitoring by field
    """
    __tablename__ = "digi_flow_result_field_audit"

    id: Optional[int] = Field(default=None, primary_key=True)
    flow_id: int = Field(foreign_key="digi_flow.id", index=True)
    result_id: int = Field(foreign_key="digi_flow_result.id")
    result_version: int
    field_path: str                          # JSON path to field
    old_value: Optional[dict] = None         # Previous value (JSONB)
    new_value: Optional[dict] = None         # Corrected value (JSONB)
    reason_code: int                         # AuditReasonCode enum
    reason_text: Optional[str] = None        # Free-text explanation
    audited_at: datetime = Field(default_factory=datetime.utcnow)
    audited_by: dict                         # Actor JSONB


class AuditReasonCode(IntEnum):
    """Reason codes for field corrections."""
    INCORRECT = 1      # Value was wrong
    MISSING = 2        # Value was not extracted
    EXTRA = 3          # Value was hallucinated
    FORMAT = 4         # Value format was wrong
    DATA_SOURCE = 5    # Block ID was wrong
    OTHER = 99


async def create_audit_records(
    session: AsyncSession,
    flow_id: int,
    result_id: int,
    result_version: int,
    changes: List[FieldChange],
    field_mapping_feedback: List[dict],
    actor: Actor,
) -> List[DigiFlowResultFieldAudit]:
    """
    Create audit records for all field changes.

    Args:
        session: Database session
        flow_id: DigiFlow ID
        result_id: DigiFlowResult ID
        result_version: Result version number
        changes: Computed field changes
        field_mapping_feedback: User-provided feedback per field
        actor: Who made the corrections

    Returns:
        List of created audit records
    """
    feedback_by_path = {f["field_path"]: f for f in field_mapping_feedback}
    audits = []

    for change in changes:
        feedback = feedback_by_path.get(change.field_path, {})

        audit = DigiFlowResultFieldAudit(
            flow_id=flow_id,
            result_id=result_id,
            result_version=result_version,
            field_path=change.field_path,
            old_value={"value": change.old_value} if change.old_value else None,
            new_value={"value": change.new_value} if change.new_value else None,
            reason_code=_map_change_to_reason(change, feedback),
            reason_text=feedback.get("reason_text"),
            audited_by=actor.model_dump(),
        )
        session.add(audit)
        audits.append(audit)

    await session.flush()
    return audits


def _map_change_to_reason(change: FieldChange, feedback: dict) -> int:
    """Map field change to appropriate reason code."""
    if feedback.get("reason_code"):
        return feedback["reason_code"]

    if change.change_type == "added":
        return AuditReasonCode.MISSING
    elif change.change_type == "removed":
        return AuditReasonCode.EXTRA
    else:
        return AuditReasonCode.INCORRECT
```

### 16.5 LangSmith Feedback Sync

```python
from langsmith import Client
from typing import Optional

class LangSmithFeedbackService:
    """
    Syncs feedback to LangSmith for model improvement tracking.

    This enables:
    - Tracking accuracy over time
    - A/B testing different prompts
    - Dataset creation for evaluations
    """

    def __init__(self):
        self.client = Client()

    async def submit_feedback(
        self,
        trace_id: str,
        score: float,
        comment: Optional[str] = None,
        correction: Optional[dict] = None,
    ):
        """
        Submit feedback for a specific trace.

        Args:
            trace_id: LangSmith trace ID (stored in digi_flow)
            score: 0.0 = incorrect, 1.0 = correct
            comment: Optional explanation
            correction: Optional corrected output
        """
        if not trace_id:
            return

        try:
            self.client.create_feedback(
                run_id=trace_id,
                key="accuracy",
                score=score,
                comment=comment,
                correction=correction,
            )
        except Exception as e:
            # Log but don't fail - feedback is optional
            logger.warning(f"Failed to submit LangSmith feedback: {e}")

    async def submit_correction_feedback(
        self,
        trace_id: str,
        original_result: dict,
        corrected_result: dict,
        changes: List[FieldChange],
    ):
        """
        Submit detailed correction feedback to LangSmith.

        Creates both a score (based on change count) and the correction.
        """
        if not trace_id or not changes:
            return

        # Calculate score based on how much was corrected
        # 0 changes = 1.0, more changes = lower score
        field_count = self._count_fields(original_result)
        change_count = len(changes)
        score = max(0.0, 1.0 - (change_count / max(field_count, 1)))

        # Build comment summarizing changes
        change_summary = ", ".join([
            f"{c.field_path}: {c.change_type}"
            for c in changes[:5]  # Limit to first 5
        ])
        if len(changes) > 5:
            change_summary += f" (+{len(changes) - 5} more)"

        await self.submit_feedback(
            trace_id=trace_id,
            score=score,
            comment=f"Corrected {len(changes)} fields: {change_summary}",
            correction=corrected_result,
        )

    def _count_fields(self, obj: Any, depth: int = 0) -> int:
        """Count total fields in nested structure."""
        if depth > 10:  # Prevent infinite recursion
            return 0

        if isinstance(obj, dict):
            count = 0
            for key, value in obj.items():
                if key not in ("data_source", "value"):
                    count += 1 + self._count_fields(value, depth + 1)
            return count
        elif isinstance(obj, list):
            return sum(self._count_fields(item, depth + 1) for item in obj)
        return 0


# Module-level instance
langsmith_feedback_service = LangSmithFeedbackService()
```

### 16.6 Training Data Task Queue

```python
from enum import Enum
from typing import Optional

class RAGTrainingDataTaskType(str, Enum):
    """Types of training data operations."""
    ADD = "ADD"         # Generate and store training vector
    REMOVE = "REMOVE"   # Delete training vector (e.g., if marked incorrect)


class RAGTrainingDataTask(BaseModel):
    """Message format for training data queue."""
    flow_id: int
    config_id: int
    task_type: RAGTrainingDataTaskType
    result_version: int
    created_at: datetime
    created_by: Actor


async def create_training_data_task(
    flow_id: int,
    config_id: int,
    result_version: int,
    task_type: RAGTrainingDataTaskType,
    actor: Actor,
):
    """
    Create async task to generate/remove training data.

    Published to SQS queue for background processing.
    """
    task = RAGTrainingDataTask(
        flow_id=flow_id,
        config_id=config_id,
        task_type=task_type,
        result_version=result_version,
        created_at=datetime.utcnow(),
        created_by=actor,
    )

    await sqs_publisher.publish(
        queue_name="rag_training_data_task_queue",
        message=task.model_dump(),
    )


class RAGTrainingDataTaskConsumer:
    """
    Processes training data tasks from queue.

    ADD tasks:
    1. Load digi_flow, result, content_metadata
    2. Generate embedding from document content
    3. Build reference_input (deduplicated text + partial blocks)
    4. Build reference_output (corrected extraction)
    5. Store in rag_training_data_vector table

    REMOVE tasks:
    1. Find existing vector by flow_id
    2. Delete from rag_training_data_vector
    """

    async def process(self, message: dict):
        task = RAGTrainingDataTask(**message)

        if task.task_type == RAGTrainingDataTaskType.ADD:
            await self._process_add(task)
        elif task.task_type == RAGTrainingDataTaskType.REMOVE:
            await self._process_remove(task)

    async def _process_add(self, task: RAGTrainingDataTask):
        """Generate and store training vector."""
        # See Section 9.4 for detailed implementation
        pass

    async def _process_remove(self, task: RAGTrainingDataTask):
        """Remove training vector."""
        async with self.session_maker() as session:
            await self.vector_repo.delete_by_flow_id(
                session=session,
                flow_id=task.flow_id,
            )
            await session.commit()
```

### 16.7 Complete Feedback Service

```python
class DigiFlowFeedbackManagementService:
    """
    Complete feedback management service.

    Coordinates:
    - Result validation
    - Diff computation
    - Audit record creation
    - Result update
    - Training data task creation
    - LangSmith feedback sync
    """

    def __init__(
        self,
        session_maker: async_sessionmaker,
        flow_repo: DigiFlowRepository,
        result_repo: DigiFlowResultRepository,
        audit_repo: DigiFlowResultFieldAuditRepository,
        langsmith_service: LangSmithFeedbackService,
    ):
        self.session_maker = session_maker
        self.flow_repo = flow_repo
        self.result_repo = result_repo
        self.audit_repo = audit_repo
        self.langsmith_service = langsmith_service

    async def submit_inline_feedback(
        self,
        flow_id: int,
        corrected_result: dict,
        field_mapping_feedback: List[dict],
        feedback_source: FeedbackSource,
        actor: Actor,
        mark_as_correct: bool = False,
    ) -> DigiFlowResult:
        """
        Submit inline feedback with corrections.

        Args:
            flow_id: DigiFlow ID to update
            corrected_result: Full corrected extraction result
            field_mapping_feedback: Per-field feedback with reason codes
            feedback_source: UI, API, or AUTO
            actor: Who submitted the feedback
            mark_as_correct: Whether to generate training data

        Returns:
            Updated DigiFlowResult
        """
        async with self.session_maker() as session:
            # 1. Load existing flow and result
            flow = await self.flow_repo.get_by_id(session, flow_id)
            if not flow:
                raise ValueError(f"DigiFlow {flow_id} not found")

            result = await self.result_repo.get_by_flow_id(session, flow_id)
            if not result:
                raise ValueError(f"DigiFlowResult for flow {flow_id} not found")

            old_result = result.data

            # 2. Compute diff
            changes = compute_json_diff(old_result, corrected_result)

            # 3. Create audit records
            await create_audit_records(
                session=session,
                flow_id=flow_id,
                result_id=result.id,
                result_version=result.version,
                changes=changes,
                field_mapping_feedback=field_mapping_feedback,
                actor=actor,
            )

            # 4. Update result
            result.data = corrected_result
            result.plain_data = self._strip_data_source(corrected_result)
            result.data_origin = DataOrigin.USER
            result.version += 1
            result.updated_at = datetime.utcnow()
            result.updated_by = actor.model_dump()

            await session.flush()

            # 5. Create training data task (if marked correct)
            if mark_as_correct:
                await create_training_data_task(
                    flow_id=flow_id,
                    config_id=flow.config_id,
                    result_version=result.version,
                    task_type=RAGTrainingDataTaskType.ADD,
                    actor=actor,
                )

            # 6. Sync to LangSmith (async, non-blocking)
            if flow.langsmith_trace_id and changes:
                asyncio.create_task(
                    self.langsmith_service.submit_correction_feedback(
                        trace_id=flow.langsmith_trace_id,
                        original_result=old_result,
                        corrected_result=corrected_result,
                        changes=changes,
                    )
                )

            await session.commit()
            return result

    def _strip_data_source(self, data: Any) -> Any:
        """Recursively remove data_source from result."""
        if isinstance(data, dict):
            if "value" in data and "data_source" in data:
                return self._strip_data_source(data["value"])
            return {
                k: self._strip_data_source(v)
                for k, v in data.items()
                if k != "data_source"
            }
        elif isinstance(data, list):
            return [self._strip_data_source(item) for item in data]
        return data
```

---

## Appendix A: Complete Data Models

### A.1 Enums

```python
class FileContentType(IntEnum):
    INVALID = 0
    PDF = 1
    EXCEL = 2
    IMAGE = 3

class SourceContentType(IntEnum):
    INVALID = 0
    FILE = 1
    TEXT = 2

class MainStatus(IntEnum):
    PENDING = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3

class DataServiceStatus(IntEnum):
    NONE = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3

class DataOrigin(IntEnum):
    SYSTEM = 0
    USER = 1

class ConfigStatus(IntEnum):
    ACTIVE = 1
    ARCHIVED = 2

class FeedbackSource(IntEnum):
    UI = 1
    API = 2
    AUTO = 3

class AuditReasonCode(IntEnum):
    INCORRECT = 1
    MISSING = 2
    EXTRA = 3
    FORMAT = 4
    OTHER = 5
```

### A.2 Actor Model

```python
class Actor(BaseModel):
    type: str  # "user", "system", "service"
    id: str
    name: str | None = None
```

---

## Appendix B: Error Handling

### B.1 Retriable Errors

```python
class RetriableError(Exception):
    """Error that can be retried (e.g., timeout, rate limit)."""
    pass

class FatalError(Exception):
    """Error that should not be retried (e.g., invalid input)."""
    pass
```

### B.2 Retry Strategy

```python
# SQS Consumer retry logic
MAX_RETRIES = 3
RETRY_DELAYS = [60, 300, 900]  # 1min, 5min, 15min

async def process_with_retry(message: dict):
    retry_count = message.get("retry_count", 0)

    try:
        await process(message)
    except RetriableError:
        if retry_count < MAX_RETRIES:
            delay = RETRY_DELAYS[retry_count]
            await republish_with_delay(message, retry_count + 1, delay)
        else:
            await mark_permanently_failed(message)
    except FatalError:
        await mark_permanently_failed(message)
```

---

## Appendix C: Testing Strategy

### C.1 Test Structure

```
tests/
├── unit/
│   ├── service/
│   │   ├── test_digi_flow_management_service.py
│   │   └── test_workflow_controller.py
│   ├── core/
│   │   └── test_models.py
│   └── prompt/
│       └── test_prompt_engine.py
├── integration/
│   ├── test_grpc_service.py
│   └── test_sqs_consumer.py
└── fixtures/
    ├── sample_pdfs/
    ├── sample_excels/
    └── mock_responses/
```

### C.2 Testing Configuration

```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def db_session():
    engine = create_async_engine("postgresql+asyncpg://...")
    async with AsyncSession(engine) as session:
        yield session

@pytest.fixture
def mock_openai(mocker):
    return mocker.patch("app.llm.openai_service.OpenAIService")
```

---

**End of Technical Specification**

*This document provides all the information needed to rebuild the Digitization Platform from scratch. For implementation, start with the database schema, then build the core services layer by layer, testing each component in isolation before integration.*
