import React from 'react';
import { Badge, Typography, Space, Empty } from 'antd';
import { KanbanStatus, KanbanStatusConfig, UnifiedDocument } from '../../types/kanban';
import { DocumentCard } from './DocumentCard';

const { Title } = Typography;

interface KanbanColumnProps {
  status: KanbanStatus;
  documents: UnifiedDocument[];
  onDocumentClick?: (doc: UnifiedDocument) => void;
  onDragStart?: (doc: UnifiedDocument) => void;
  onDragEnd?: () => void;
  onDrop?: (status: KanbanStatus) => void;
  isDragOver?: boolean;
}

/**
 * KanbanColumn - Single column in the Kanban board
 * Displays documents of a specific status with drag-drop support
 */
export const KanbanColumn: React.FC<KanbanColumnProps> = ({
  status,
  documents,
  onDocumentClick,
  onDragStart,
  onDragEnd,
  onDrop,
  isDragOver = false,
}) => {
  const config = KanbanStatusConfig[status];

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    onDrop?.(status);
  };

  const handleDragStart = (doc: UnifiedDocument) => (e: React.DragEvent) => {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(doc.id));
    onDragStart?.(doc);
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      style={{
        width: 280,
        minWidth: 280,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: isDragOver ? config.bgColor : '#f5f5f5',
        borderRadius: 8,
        border: isDragOver ? `2px dashed ${config.color}` : '2px solid transparent',
        transition: 'all 0.2s ease',
      }}
    >
      {/* Column Header */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: `3px solid ${config.color}`,
          backgroundColor: config.bgColor,
          borderTopLeftRadius: 6,
          borderTopRightRadius: 6,
        }}
      >
        <Space>
          <Title level={5} style={{ margin: 0, color: config.color }}>
            {config.label}
          </Title>
          <Badge
            count={documents.length}
            style={{
              backgroundColor: config.color,
            }}
          />
        </Space>
      </div>

      {/* Column Content */}
      <div
        style={{
          flex: 1,
          padding: 12,
          overflowY: 'auto',
          overflowX: 'hidden',
        }}
      >
        {documents.length > 0 ? (
          documents.map((doc) => (
            <div
              key={doc.id}
              draggable={config.allowDragOut}
              onDragStart={handleDragStart(doc)}
              onDragEnd={onDragEnd}
              style={{
                cursor: config.allowDragOut ? 'grab' : 'default',
              }}
            >
              <DocumentCard
                document={doc}
                onClick={onDocumentClick}
              />
            </div>
          ))
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无文档"
            style={{ marginTop: 40 }}
          />
        )}
      </div>
    </div>
  );
};

export default KanbanColumn;
