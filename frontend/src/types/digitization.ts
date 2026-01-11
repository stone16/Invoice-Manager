// Digitization Platform Types
// Based on backend models in app/models/digi_flow.py

// Enums matching backend IntEnum values
export enum FileContentType {
  INVALID = 0,
  PDF = 1,
  EXCEL = 2,
  IMAGE = 3,
}

export enum SourceContentType {
  INVALID = 0,
  FILE = 1,
  TEXT = 2,
}

export enum MainStatus {
  PENDING = 0,
  IN_PROGRESS = 1,
  COMPLETED = 2,
  FAILED = 3,
}

export enum DataServiceStatus {
  NONE = 0,
  IN_PROGRESS = 1,
  COMPLETED = 2,
  FAILED = 3,
}

export enum DataOrigin {
  SYSTEM = 0,
  USER = 1,
}

export enum ConfigStatus {
  ACTIVE = 1,
  ARCHIVED = 2,
}

export enum FeedbackSource {
  UI = 1,
  API = 2,
  AUTO = 3,
}

export enum AuditReasonCode {
  INCORRECT = 1,
  MISSING = 2,
  EXTRA = 3,
  FORMAT = 4,
  DATA_SOURCE = 5,
  OTHER = 99,
}

// Block ID data source structure
export interface DataSource {
  block_id: string;
  confidence?: number;
  raw_value?: string;
}

// Field with data source tracking
export interface FieldWithSource<T = string> {
  value: T;
  data_source?: DataSource;
}

// Schema Definition
export interface DigiFlowSchema {
  id: number;
  slug: string;
  name: string;
  yaml_schema?: string;
  schema: Record<string, unknown>;
  version: number;
  status: ConfigStatus;
  created_at: string;
  created_by?: Record<string, unknown>;
  updated_at?: string;
  updated_by?: Record<string, unknown>;
  deleted_at?: string;
  deleted_by?: Record<string, unknown>;
}

export interface DigiFlowSchemaCreate {
  slug: string;
  name: string;
  yaml_schema?: string;
  schema?: Record<string, unknown>;
}

export interface DigiFlowSchemaUpdate {
  name?: string;
  yaml_schema?: string;
  schema?: Record<string, unknown>;
  status?: ConfigStatus;
}

// Config Definition
export interface WorkflowConfig {
  rag_enabled?: boolean;
  rag_top_k?: number;
  rag_threshold?: number;
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface PromptConfig {
  task_description?: string;
  custom_instructions?: string;
  examples?: Array<{
    input: string;
    output: Record<string, unknown>;
  }>;
}

export interface SchemaValidation {
  strict_mode?: boolean;
  allow_extra_fields?: boolean;
  required_fields?: string[];
}

export interface DigiFlowConfig {
  id: number;
  slug: string;
  name: string;
  description?: string;
  domain?: string;
  schema_id: number;
  schema_version: number;
  source_content_type: SourceContentType;
  workflow_config?: WorkflowConfig;
  prompt_config?: PromptConfig;
  schema_validation?: SchemaValidation;
  version: number;
  status: ConfigStatus;
  created_at: string;
  created_by?: Record<string, unknown>;
  updated_at?: string;
  updated_by?: Record<string, unknown>;
  deleted_at?: string;
  deleted_by?: Record<string, unknown>;
}

export interface DigiFlowConfigCreate {
  slug: string;
  name: string;
  description?: string;
  domain?: string;
  schema_id: number;
  schema_version: number;
  source_content_type: SourceContentType;
  workflow_config?: WorkflowConfig;
  prompt_config?: PromptConfig;
  schema_validation?: SchemaValidation;
}

export interface DigiFlowConfigUpdate {
  name?: string;
  description?: string;
  domain?: string;
  workflow_config?: WorkflowConfig;
  prompt_config?: PromptConfig;
  schema_validation?: SchemaValidation;
  status?: ConfigStatus;
}

// Text Block from content normalization
export interface TextBlock {
  block_id: string;
  text: string;
  page: number;
  row: number;
  col: number;
  bbox?: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  };
}

// Content Context
export interface ContentContext {
  file_path?: string;
  file_name?: string;
  file_type?: string;
  text?: string;
  pages?: number;
}

// Flow Definition
export interface DigiFlow {
  id: number;
  config_id: number;
  config_version: number;
  schema_id: number;
  schema_version: number;
  content_type: FileContentType;
  content_context: ContentContext;
  content_metadata?: Record<string, unknown>;
  langsmith_trace_id?: string;
  langsmith_metadata?: Record<string, unknown>;
  main_status: MainStatus;
  data_service_status: DataServiceStatus;
  schema_validation_status: number;
  schema_validation_result?: Record<string, unknown>;
  extra_attributes?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  is_sampled?: boolean;
  created_at: string;
  created_by?: Record<string, unknown>;
  updated_at?: string;
  updated_by?: Record<string, unknown>;
}

export interface DigiFlowCreate {
  config_id: number;
  config_version?: number;
  content_type: FileContentType;
  content_context: ContentContext;
}

// Flow Result with data_source tracking
export interface DigiFlowResult {
  id: number;
  flow_id: number;
  data: Record<string, FieldWithSource>;
  plain_data?: Record<string, unknown>;
  text_blocks?: TextBlock[];
  data_origin: DataOrigin;
  version: number;
  updated_at: string;
  updated_by?: Record<string, unknown>;
}

// Flow with result included
export interface DigiFlowWithResult extends DigiFlow {
  result?: DigiFlowResult;
  config?: DigiFlowConfig;
  schema?: DigiFlowSchema;
}

// Field Audit for corrections
export interface DigiFlowResultFieldAudit {
  id: number;
  flow_id: number;
  result_id: number;
  result_version: number;
  field_path: string;
  old_value?: unknown;
  new_value?: unknown;
  reason_code: AuditReasonCode;
  reason_text?: string;
  audited_at: string;
  audited_by?: Record<string, unknown>;
}

export interface AuditHistoryResponse {
  items: DigiFlowResultFieldAudit[];
  total: number;
}

// Feedback submission
export interface FeedbackSubmission {
  corrections: Array<{
    field_path: string;
    new_value: unknown;
    reason_code: AuditReasonCode;
    reason_text?: string;
  }>;
  source?: FeedbackSource;
}

export interface FeedbackResponse {
  success: boolean;
  message: string;
  result_version: number;
  audits_created: number;
}

// RAG Training Data
export interface RagTrainingDataVector {
  id: number;
  flow_id: number;
  config_id: number;
  schema_id: number;
  schema_version: number;
  result_id: number;
  result_version: number;
  source_content_context: ContentContext;
  source_content_context_idx: number;
  reference_input: Record<string, unknown>;
  reference_output: Record<string, unknown>;
  created_at: string;
  created_by?: Record<string, unknown>;
}

// List responses
export interface SchemaListResponse {
  items: DigiFlowSchema[];
  total: number;
}

export interface ConfigListResponse {
  items: DigiFlowConfig[];
  total: number;
}

export interface FlowListResponse {
  items: DigiFlowWithResult[];
  total: number;
}

export interface SkippedFile {
  file_name: string;
  reason: string;
}

export interface FlowUploadResponse {
  items: DigiFlowWithResult[];
  skipped_files: SkippedFile[];
}

// Status labels for display
export const MainStatusLabels: Record<MainStatus, string> = {
  [MainStatus.PENDING]: '待处理',
  [MainStatus.IN_PROGRESS]: '处理中',
  [MainStatus.COMPLETED]: '已完成',
  [MainStatus.FAILED]: '失败',
};

export const ConfigStatusLabels: Record<ConfigStatus, string> = {
  [ConfigStatus.ACTIVE]: '启用',
  [ConfigStatus.ARCHIVED]: '已归档',
};

export const FileContentTypeLabels: Record<FileContentType, string> = {
  [FileContentType.INVALID]: '无效',
  [FileContentType.PDF]: 'PDF',
  [FileContentType.EXCEL]: 'Excel',
  [FileContentType.IMAGE]: '图片',
};

export const SourceContentTypeLabels: Record<SourceContentType, string> = {
  [SourceContentType.INVALID]: '无效',
  [SourceContentType.FILE]: '文件',
  [SourceContentType.TEXT]: '文本',
};

export const AuditReasonCodeLabels: Record<AuditReasonCode, string> = {
  [AuditReasonCode.INCORRECT]: '值不正确',
  [AuditReasonCode.MISSING]: '值缺失',
  [AuditReasonCode.EXTRA]: '多余的值',
  [AuditReasonCode.FORMAT]: '格式错误',
  [AuditReasonCode.DATA_SOURCE]: '来源错误',
  [AuditReasonCode.OTHER]: '其他',
};
