import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import {
  ClockCircleOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  EyeOutlined,
  CheckSquareOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { KanbanStatus, KanbanStatusConfig, KANBAN_STATUS_ORDER } from '../../types/kanban';

interface StatsOverviewProps {
  stats: Record<KanbanStatus, number>;
  onStatClick?: (status: KanbanStatus) => void;
}

const StatusIcons: Record<KanbanStatus, React.ReactNode> = {
  [KanbanStatus.PENDING]: <ClockCircleOutlined />,
  [KanbanStatus.PROCESSING]: <LoadingOutlined />,
  [KanbanStatus.COMPLETED]: <CheckCircleOutlined />,
  [KanbanStatus.REVIEWING]: <EyeOutlined />,
  [KanbanStatus.CONFIRMED]: <CheckSquareOutlined />,
  [KanbanStatus.FAILED]: <CloseCircleOutlined />,
};

/**
 * StatsOverview - Dashboard statistics cards
 * Shows document count for each Kanban status
 */
export const StatsOverview: React.FC<StatsOverviewProps> = ({
  stats,
  onStatClick,
}) => {
  const total = Object.values(stats).reduce((sum, count) => sum + count, 0);

  return (
    <Row gutter={[16, 16]}>
      {/* Total count */}
      <Col xs={24} sm={12} md={8} lg={4}>
        <Card
          hoverable
          style={{ textAlign: 'center', borderTop: '3px solid #1890ff' }}
        >
          <Statistic
            title="总计"
            value={total}
            valueStyle={{ color: '#1890ff' }}
          />
        </Card>
      </Col>

      {/* Status counts */}
      {KANBAN_STATUS_ORDER.map((status) => {
        const config = KanbanStatusConfig[status];
        const count = stats[status] || 0;

        return (
          <Col key={status} xs={12} sm={8} md={6} lg={3}>
            <Card
              hoverable
              onClick={() => onStatClick?.(status)}
              style={{
                textAlign: 'center',
                borderTop: `3px solid ${config.color}`,
                cursor: 'pointer',
              }}
            >
              <Statistic
                title={config.label}
                value={count}
                prefix={StatusIcons[status]}
                valueStyle={{ color: config.color }}
              />
            </Card>
          </Col>
        );
      })}
    </Row>
  );
};

export default StatsOverview;
