import axios from 'axios';
import type {
  Invoice,
  InvoiceDetail,
  InvoiceListResponse,
  Statistics,
  UploadResponse,
  LLMStatusResponse,
  LLMConfigRequest,
  LLMConfigResponse,
  LLMTestResponse,
} from '../types/invoice';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health check
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

// Upload invoices
export const uploadInvoices = async (files: File[]): Promise<UploadResponse[]> => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await api.post('/invoices/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// List invoices
export interface ListParams {
  page?: number;
  page_size?: number;
  status?: string;
  owner?: string;
  start_date?: string;
  end_date?: string;
}

export const listInvoices = async (params: ListParams = {}): Promise<InvoiceListResponse> => {
  const response = await api.get('/invoices', { params });
  return response.data;
};

// Get invoice detail
export const getInvoice = async (id: number): Promise<InvoiceDetail> => {
  const response = await api.get(`/invoices/${id}`);
  return response.data;
};

// Get invoice file URL
export const getInvoiceFileUrl = (id: number): string => {
  return `/api/invoices/${id}/file`;
};

// Update invoice
export const updateInvoice = async (
  id: number,
  data: Partial<Invoice>
): Promise<Invoice> => {
  const response = await api.put(`/invoices/${id}`, data);
  return response.data;
};

// Batch update
export const batchUpdateInvoices = async (
  invoiceIds: number[],
  status?: string,
  owner?: string
): Promise<{ message: string; updated_count: number }> => {
  const response = await api.post('/invoices/batch-update', {
    invoice_ids: invoiceIds,
    status,
    owner,
  });
  return response.data;
};

// Delete invoice
export const deleteInvoice = async (id: number): Promise<void> => {
  await api.delete(`/invoices/${id}`);
};

// Batch delete invoices
export const batchDeleteInvoices = async (
  invoiceIds: number[]
): Promise<{ message: string; deleted_count: number }> => {
  const response = await api.post('/invoices/batch-delete', {
    invoice_ids: invoiceIds,
  });
  return response.data;
};

// Get statistics
export const getStatistics = async (
  invoiceIds?: number[],
  status?: string,
  owner?: string
): Promise<Statistics> => {
  const params: Record<string, string> = {};
  if (invoiceIds && invoiceIds.length > 0) {
    params.invoice_ids = invoiceIds.join(',');
  }
  if (status) {
    params.status = status;
  }
  if (owner) {
    params.owner = owner;
  }

  const response = await api.get('/invoices/statistics', { params });
  return response.data;
};

// Resolve parsing diff
export const resolveDiff = async (
  invoiceId: number,
  diffId: number,
  source: 'ocr' | 'llm' | 'custom',
  customValue?: string
): Promise<{ message: string; field_name: string; final_value: string; all_resolved: boolean }> => {
  const response = await api.post(`/invoices/${invoiceId}/diffs/${diffId}/resolve`, {
    source,
    custom_value: customValue,
  });
  return response.data;
};

// Confirm invoice
export const confirmInvoice = async (
  invoiceId: number
): Promise<{ message: string; resolved_count: number }> => {
  const response = await api.post(`/invoices/${invoiceId}/confirm`);
  return response.data;
};

// Re-process invoice (run OCR/LLM again)
export const reprocessInvoice = async (
  invoiceId: number
): Promise<{ message: string; invoice_id: number }> => {
  const response = await api.post(`/invoices/${invoiceId}/process`);
  return response.data;
};

// Batch reprocess invoices (clear old results and re-run OCR/LLM)
export const batchReprocessInvoices = async (
  invoiceIds: number[]
): Promise<{ message: string; count: number }> => {
  const response = await api.post('/invoices/batch-reprocess', {
    invoice_ids: invoiceIds,
  });
  return response.data;
};

// LLM Configuration APIs

// Get LLM status
export const getLLMStatus = async (): Promise<LLMStatusResponse> => {
  const response = await api.get('/settings/llm/status');
  return response.data;
};

// Configure LLM provider
export const configureLLM = async (
  config: LLMConfigRequest
): Promise<LLMConfigResponse> => {
  const response = await api.post('/settings/llm/configure', config);
  return response.data;
};

// Test LLM connection
export const testLLMConnection = async (): Promise<LLMTestResponse> => {
  const response = await api.post('/settings/llm/test');
  return response.data;
};

// ============================================
// Digitization Platform APIs
// ============================================

import type {
  DigiFlowSchema,
  DigiFlowSchemaCreate,
  DigiFlowSchemaUpdate,
  DigiFlowConfig,
  DigiFlowConfigCreate,
  DigiFlowConfigUpdate,
  DigiFlowCreate,
  DigiFlowWithResult,
  FeedbackSubmission,
  FeedbackResponse,
  SchemaListResponse,
  ConfigListResponse,
  FlowListResponse,
} from '../types/digitization';

// Schema Management APIs

export interface SchemaListParams {
  page?: number;
  page_size?: number;
  status?: number;
  slug?: string;
}

export const listSchemas = async (params: SchemaListParams = {}): Promise<SchemaListResponse> => {
  const response = await api.get('/schemas', { params });
  return response.data;
};

export const getSchema = async (id: number, version?: number): Promise<DigiFlowSchema> => {
  const params = version ? { version } : {};
  const response = await api.get(`/schemas/${id}`, { params });
  return response.data;
};

export const createSchema = async (data: DigiFlowSchemaCreate): Promise<DigiFlowSchema> => {
  const response = await api.post('/schemas', data);
  return response.data;
};

export const updateSchema = async (id: number, data: DigiFlowSchemaUpdate): Promise<DigiFlowSchema> => {
  const response = await api.put(`/schemas/${id}`, data);
  return response.data;
};

export const deleteSchema = async (id: number): Promise<void> => {
  await api.delete(`/schemas/${id}`);
};

// Config Management APIs

export interface ConfigListParams {
  page?: number;
  page_size?: number;
  status?: number;
  schema_id?: number;
  domain?: string;
}

export const listConfigs = async (params: ConfigListParams = {}): Promise<ConfigListResponse> => {
  const response = await api.get('/configs', { params });
  return response.data;
};

export const getConfig = async (id: number, version?: number): Promise<DigiFlowConfig> => {
  const params = version ? { version } : {};
  const response = await api.get(`/configs/${id}`, { params });
  return response.data;
};

export const createConfig = async (data: DigiFlowConfigCreate): Promise<DigiFlowConfig> => {
  const response = await api.post('/configs', data);
  return response.data;
};

export const updateConfig = async (id: number, data: DigiFlowConfigUpdate): Promise<DigiFlowConfig> => {
  const response = await api.put(`/configs/${id}`, data);
  return response.data;
};

// Flow Management APIs

export interface FlowListParams {
  page?: number;
  page_size?: number;
  config_id?: number;
  main_status?: number;
  start_date?: string;
  end_date?: string;
}

export const listFlows = async (params: FlowListParams = {}): Promise<FlowListResponse> => {
  const response = await api.get('/flows', { params });
  return response.data;
};

export const getFlow = async (id: number): Promise<DigiFlowWithResult> => {
  const response = await api.get(`/flows/${id}`);
  return response.data;
};

export const createFlow = async (data: DigiFlowCreate): Promise<DigiFlowWithResult> => {
  const response = await api.post('/flows', data);
  return response.data;
};

export const uploadFlow = async (
  configId: number,
  files: File[]
): Promise<DigiFlowWithResult[]> => {
  const formData = new FormData();
  formData.append('config_id', configId.toString());
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await api.post('/flows/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// Feedback APIs

export const submitFeedback = async (
  flowId: number,
  feedback: FeedbackSubmission
): Promise<FeedbackResponse> => {
  const response = await api.post(`/flows/${flowId}/feedback`, feedback);
  return response.data;
};

// LangSmith trace URL helper
export const getLangSmithTraceUrl = (traceId: string): string => {
  return `https://smith.langchain.com/public/${traceId}`;
};

export default api;
