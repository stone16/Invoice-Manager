import React from 'react';
import { Tag } from 'antd';
import {
  ClockCircleOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  EyeOutlined,
  CheckSquareOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { KanbanStatus, KanbanStatusConfig } from '../../types/kanban';

interface StatusBadgeProps {
  status: KanbanStatus;
  size?: 'small' | 'default';
  showIcon?: boolean;
}

const StatusIcons: Record<KanbanStatus, React.ReactNode> = {
  [KanbanStatus.PENDING]: <ClockCircleOutlined />,
  [KanbanStatus.PROCESSING]: <LoadingOutlined spin />,
  [KanbanStatus.COMPLETED]: <CheckCircleOutlined />,
  [KanbanStatus.REVIEWING]: <EyeOutlined />,
  [KanbanStatus.CONFIRMED]: <CheckSquareOutlined />,
  [KanbanStatus.FAILED]: <CloseCircleOutlined />,
};

/**
 * StatusBadge - Displays document status with color and optional icon
 * Uses KanbanStatusConfig for consistent styling across the app
 */
export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'default',
  showIcon = true,
}) => {
  const config = KanbanStatusConfig[status];

  return (
    <Tag
      color={config.color}
      icon={showIcon ? StatusIcons[status] : undefined}
      style={{
        fontSize: size === 'small' ? 12 : 14,
        padding: size === 'small' ? '0 6px' : '2px 8px',
      }}
    >
      {config.label}
    </Tag>
  );
};

export default StatusBadge;
