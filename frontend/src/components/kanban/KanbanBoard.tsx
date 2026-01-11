import React, { useState, useCallback } from 'react';
import { message } from 'antd';
import {
  KanbanStatus,
  UnifiedDocument,
  KANBAN_STATUS_ORDER,
  isDragAllowed,
  groupDocumentsByStatus,
} from '../../types/kanban';
import { KanbanColumn } from './KanbanColumn';
import { DetailDrawer } from './DetailDrawer';

interface KanbanBoardProps {
  documents: UnifiedDocument[];
  onStatusChange?: (docId: number, newStatus: KanbanStatus) => Promise<void>;
  onDocumentEdit?: (doc: UnifiedDocument) => void;
  isLoading?: boolean;
}

/**
 * KanbanBoard - Main board component with 6 columns
 * Handles drag-drop between columns and document selection
 */
export const KanbanBoard: React.FC<KanbanBoardProps> = ({
  documents,
  onStatusChange,
  onDocumentEdit,
  isLoading = false,
}) => {
  const [draggingDoc, setDraggingDoc] = useState<UnifiedDocument | null>(null);
  const [dragOverStatus, setDragOverStatus] = useState<KanbanStatus | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<UnifiedDocument | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Group documents by status
  const groupedDocs = groupDocumentsByStatus(documents);

  const handleDragStart = useCallback((doc: UnifiedDocument) => {
    setDraggingDoc(doc);
  }, []);

  const handleDragEnd = useCallback(() => {
    setDraggingDoc(null);
    setDragOverStatus(null);
  }, []);

  const handleDrop = useCallback(async (targetStatus: KanbanStatus) => {
    if (!draggingDoc) return;

    const sourceStatus = draggingDoc.status;

    // Check if drag is allowed
    if (!isDragAllowed(sourceStatus, targetStatus)) {
      message.warning(`不能将文档从 "${sourceStatus}" 移动到 "${targetStatus}"`);
      handleDragEnd();
      return;
    }

    // Call status change handler
    if (onStatusChange) {
      try {
        await onStatusChange(draggingDoc.id, targetStatus);
        message.success('状态已更新');
      } catch (error) {
        message.error('状态更新失败');
      }
    }

    handleDragEnd();
  }, [draggingDoc, onStatusChange, handleDragEnd]);

  const handleDocumentClick = useCallback((doc: UnifiedDocument) => {
    setSelectedDoc(doc);
    setDrawerOpen(true);
  }, []);

  const handleDrawerClose = useCallback(() => {
    setDrawerOpen(false);
  }, []);

  const handleDocumentEdit = useCallback((doc: UnifiedDocument) => {
    setDrawerOpen(false);
    onDocumentEdit?.(doc);
  }, [onDocumentEdit]);

  return (
    <>
      <div
        style={{
          display: 'flex',
          gap: 16,
          height: 'calc(100vh - 180px)',
          overflowX: 'auto',
          overflowY: 'hidden',
          padding: '16px 0',
          opacity: isLoading ? 0.5 : 1,
          pointerEvents: isLoading ? 'none' : 'auto',
        }}
      >
        {KANBAN_STATUS_ORDER.map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            documents={groupedDocs[status]}
            onDocumentClick={handleDocumentClick}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onDrop={handleDrop}
            isDragOver={dragOverStatus === status}
          />
        ))}
      </div>

      <DetailDrawer
        document={selectedDoc}
        open={drawerOpen}
        onClose={handleDrawerClose}
        onEdit={handleDocumentEdit}
      />
    </>
  );
};

export default KanbanBoard;
