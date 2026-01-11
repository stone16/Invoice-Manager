// Kanban Types - Unified Document Management
// Maps Flow status to 6 Kanban columns for visual management

import { MainStatus, type DigiFlowWithResult, type DigiFlowConfig } from './digitization';

/**
 * Unified Kanban Status - 6 columns for document lifecycle
 * Maps both Invoice and Flow statuses to a unified view
 */
export enum KanbanStatus {
  PENDING = 'pending',        // Gray - Awaiting processing
  PROCESSING = 'processing',  // Blue - Currently processing
  COMPLETED = 'completed',    // Green - Processing complete, needs review
  REVIEWING = 'reviewing',    // Orange - Under manual review
  CONFIRMED = 'confirmed',    // Cyan - Verified and confirmed
  FAILED = 'failed',          // Red - Processing failed
}

/**
 * Status display configuration
 */
export interface StatusConfig {
  label: string;
  color: string;
  bgColor: string;
  icon: string;
  allowDragIn: boolean;  // Can cards be dragged into this column
  allowDragOut: boolean; // Can cards be dragged out of this column
}

export const KanbanStatusConfig: Record<KanbanStatus, StatusConfig> = {
  [KanbanStatus.PENDING]: {
    label: '待处理',
    color: '#8c8c8c',
    bgColor: '#fafafa',
    icon: 'clock-circle',
    allowDragIn: true,  // Can retry failed items
    allowDragOut: false, // System moves to processing
  },
  [KanbanStatus.PROCESSING]: {
    label: '处理中',
    color: '#1890ff',
    bgColor: '#e6f7ff',
    icon: 'loading',
    allowDragIn: false, // System controlled
    allowDragOut: false, // System controlled
  },
  [KanbanStatus.COMPLETED]: {
    label: '已完成',
    color: '#52c41a',
    bgColor: '#f6ffed',
    icon: 'check-circle',
    allowDragIn: false, // System controlled
    allowDragOut: true, // Can move to reviewing or confirmed
  },
  [KanbanStatus.REVIEWING]: {
    label: '待审核',
    color: '#fa8c16',
    bgColor: '#fff7e6',
    icon: 'eye',
    allowDragIn: true,  // From completed
    allowDragOut: true, // To confirmed
  },
  [KanbanStatus.CONFIRMED]: {
    label: '已确认',
    color: '#13c2c2',
    bgColor: '#e6fffb',
    icon: 'check-square',
    allowDragIn: true,  // From completed or reviewing
    allowDragOut: false, // Terminal state
  },
  [KanbanStatus.FAILED]: {
    label: '失败',
    color: '#ff4d4f',
    bgColor: '#fff1f0',
    icon: 'close-circle',
    allowDragIn: false, // System controlled
    allowDragOut: true, // Can retry to pending
  },
};

/**
 * Unified Document - Common interface for all document types on Kanban
 */
export interface UnifiedDocument {
  id: number;
  type: 'flow'; // Document source type, now only 'flow'

  // Display info
  title: string;           // File name or description
  subtitle?: string;       // Document type name (from config)
  preview?: string;        // Preview text or summary

  // Status
  status: KanbanStatus;
  originalStatus: MainStatus;

  // Metadata
  configId?: number;
  configName?: string;
  schemaName?: string;
  version?: number;

  // Content info
  fileType?: string;       // pdf, excel, image
  pageCount?: number;

  // Tracing
  langsmithTraceId?: string;
  blockCount?: number;     // Number of text blocks extracted

  // Timestamps
  createdAt: string;
  updatedAt?: string;

  // Original data reference
  raw: DigiFlowWithResult;
}

/**
 * Kanban column with documents
 */
export interface KanbanColumn {
  status: KanbanStatus;
  config: StatusConfig;
  documents: UnifiedDocument[];
  count: number;
}

/**
 * Map MainStatus (Flow) to KanbanStatus
 */
export function mapFlowStatusToKanban(status: MainStatus): KanbanStatus {
  switch (status) {
    case MainStatus.PENDING:
      return KanbanStatus.PENDING;
    case MainStatus.IN_PROGRESS:
      return KanbanStatus.PROCESSING;
    case MainStatus.COMPLETED:
      return KanbanStatus.COMPLETED;
    case MainStatus.FAILED:
      return KanbanStatus.FAILED;
    default:
      return KanbanStatus.PENDING;
  }
}

/**
 * Map KanbanStatus back to MainStatus for API calls
 */
export function mapKanbanToFlowStatus(status: KanbanStatus): MainStatus | null {
  switch (status) {
    case KanbanStatus.PENDING:
      return MainStatus.PENDING;
    case KanbanStatus.PROCESSING:
      return MainStatus.IN_PROGRESS;
    case KanbanStatus.COMPLETED:
    case KanbanStatus.REVIEWING:
    case KanbanStatus.CONFIRMED:
      return MainStatus.COMPLETED;
    case KanbanStatus.FAILED:
      return MainStatus.FAILED;
    default:
      return null;
  }
}

/**
 * Convert DigiFlowWithResult to UnifiedDocument
 */
export function flowToUnifiedDocument(
  flow: DigiFlowWithResult,
  config?: DigiFlowConfig
): UnifiedDocument {
  const fileName = flow.content_context?.file_name || `Flow #${flow.id}`;
  const configName = config?.name || flow.config?.name;

  return {
    id: flow.id,
    type: 'flow',
    title: fileName,
    subtitle: configName,
    preview: flow.content_context?.text?.slice(0, 100),
    status: mapFlowStatusToKanban(flow.main_status),
    originalStatus: flow.main_status,
    configId: flow.config_id,
    configName,
    schemaName: flow.schema?.name,
    version: flow.result?.version,
    fileType: flow.content_context?.file_type,
    pageCount: flow.content_context?.pages,
    langsmithTraceId: flow.langsmith_trace_id,
    blockCount: flow.result?.text_blocks?.length,
    createdAt: flow.created_at,
    updatedAt: flow.updated_at,
    raw: flow,
  };
}

/**
 * Group documents by Kanban status
 */
export function groupDocumentsByStatus(
  documents: UnifiedDocument[]
): Record<KanbanStatus, UnifiedDocument[]> {
  const grouped: Record<KanbanStatus, UnifiedDocument[]> = {
    [KanbanStatus.PENDING]: [],
    [KanbanStatus.PROCESSING]: [],
    [KanbanStatus.COMPLETED]: [],
    [KanbanStatus.REVIEWING]: [],
    [KanbanStatus.CONFIRMED]: [],
    [KanbanStatus.FAILED]: [],
  };

  documents.forEach((doc) => {
    grouped[doc.status].push(doc);
  });

  return grouped;
}

/**
 * Check if drag operation is allowed
 */
export function isDragAllowed(from: KanbanStatus, to: KanbanStatus): boolean {
  const fromConfig = KanbanStatusConfig[from];
  const toConfig = KanbanStatusConfig[to];

  if (!fromConfig.allowDragOut || !toConfig.allowDragIn) {
    return false;
  }

  // Define valid transitions
  const validTransitions: Record<KanbanStatus, KanbanStatus[]> = {
    [KanbanStatus.PENDING]: [], // System controls
    [KanbanStatus.PROCESSING]: [], // System controls
    [KanbanStatus.COMPLETED]: [KanbanStatus.REVIEWING, KanbanStatus.CONFIRMED],
    [KanbanStatus.REVIEWING]: [KanbanStatus.CONFIRMED],
    [KanbanStatus.CONFIRMED]: [], // Terminal state
    [KanbanStatus.FAILED]: [KanbanStatus.PENDING], // Retry
  };

  return validTransitions[from]?.includes(to) ?? false;
}

/**
 * Kanban filter options
 */
export interface KanbanFilters {
  configId?: number;
  searchText?: string;
  dateRange?: [string, string];
}

/**
 * Kanban board state
 */
export interface KanbanBoardState {
  columns: Record<KanbanStatus, KanbanColumn>;
  filters: KanbanFilters;
  selectedDocumentId?: number;
  isLoading: boolean;
  error?: string;
}

/**
 * All Kanban statuses in display order
 */
export const KANBAN_STATUS_ORDER: KanbanStatus[] = [
  KanbanStatus.PENDING,
  KanbanStatus.PROCESSING,
  KanbanStatus.COMPLETED,
  KanbanStatus.REVIEWING,
  KanbanStatus.CONFIRMED,
  KanbanStatus.FAILED,
];
