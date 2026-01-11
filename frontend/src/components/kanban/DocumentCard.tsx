import React from 'react';
import { Card, Typography, Space, Tooltip } from 'antd';
import {
  FileTextOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  FileImageOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { UnifiedDocument, KanbanStatusConfig } from '../../types/kanban';
import { StatusBadge } from './StatusBadge';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { Text, Paragraph } = Typography;

interface DocumentCardProps {
  document: UnifiedDocument;
  onClick?: (doc: UnifiedDocument) => void;
  isDragging?: boolean;
}

const FileTypeIcons: Record<string, React.ReactNode> = {
  pdf: <FilePdfOutlined style={{ color: '#ff4d4f' }} />,
  excel: <FileExcelOutlined style={{ color: '#52c41a' }} />,
  image: <FileImageOutlined style={{ color: '#1890ff' }} />,
  default: <FileTextOutlined style={{ color: '#8c8c8c' }} />,
};

/**
 * DocumentCard - Compact card for Kanban board display
 * Shows document title, type, status, and key metadata
 */
export const DocumentCard: React.FC<DocumentCardProps> = ({
  document,
  onClick,
  isDragging = false,
}) => {
  const statusConfig = KanbanStatusConfig[document.status];
  const fileIcon = FileTypeIcons[document.fileType || 'default'] || FileTypeIcons.default;

  const handleClick = () => {
    onClick?.(document);
  };

  return (
    <Card
      size="small"
      hoverable
      onClick={handleClick}
      style={{
        marginBottom: 8,
        borderLeft: `3px solid ${statusConfig.color}`,
        opacity: isDragging ? 0.5 : 1,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
      }}
      bodyStyle={{ padding: '12px' }}
    >
      {/* Header: File icon + Title */}
      <Space align="start" style={{ width: '100%', marginBottom: 8 }}>
        <span style={{ fontSize: 18 }}>{fileIcon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Tooltip title={document.title}>
            <Text
              strong
              ellipsis
              style={{ display: 'block', maxWidth: '100%' }}
            >
              {document.title}
            </Text>
          </Tooltip>
          {document.subtitle && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {document.subtitle}
            </Text>
          )}
        </div>
      </Space>

      {/* Preview text if available */}
      {document.preview && (
        <Paragraph
          type="secondary"
          ellipsis={{ rows: 2 }}
          style={{ fontSize: 12, marginBottom: 8 }}
        >
          {document.preview}
        </Paragraph>
      )}

      {/* Footer: Status + Time */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <StatusBadge status={document.status} size="small" showIcon={false} />
        <Tooltip title={dayjs(document.createdAt).format('YYYY-MM-DD HH:mm:ss')}>
          <Text type="secondary" style={{ fontSize: 11 }}>
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            {dayjs(document.createdAt).fromNow()}
          </Text>
        </Tooltip>
      </div>
    </Card>
  );
};

export default DocumentCard;
