import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Typography, List, Empty, Button, Space, Spin, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  FolderOutlined,
  ArrowRightOutlined,
  PlusOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { StatsOverview } from '../components/kanban/StatsOverview';
import { DocumentCard } from '../components/kanban/DocumentCard';
import {
  KanbanStatus,
  UnifiedDocument,
  flowToUnifiedDocument,
  groupDocumentsByStatus,
} from '../types/kanban';
import { DigiFlowConfig } from '../types/digitization';
import { listFlows, listConfigs } from '../services/api';

const { Text } = Typography;

/**
 * DashboardPage - Main dashboard with stats, document types, and recent docs
 */
const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [configs, setConfigs] = useState<DigiFlowConfig[]>([]);
  const [documents, setDocuments] = useState<UnifiedDocument[]>([]);
  const [stats, setStats] = useState<Record<KanbanStatus, number>>({
    [KanbanStatus.PENDING]: 0,
    [KanbanStatus.PROCESSING]: 0,
    [KanbanStatus.COMPLETED]: 0,
    [KanbanStatus.REVIEWING]: 0,
    [KanbanStatus.CONFIRMED]: 0,
    [KanbanStatus.FAILED]: 0,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load configs and flows in parallel
      const [configsResponse, flowsResponse] = await Promise.all([
        listConfigs({ status: 1 }),
        listFlows({ limit: 50, offset: 0 }),
      ]);

      setConfigs(configsResponse.items);

      // Convert flows to unified documents
      const docs = flowsResponse.items.map((flow) => {
        const config = configsResponse.items.find((c) => c.id === flow.config_id);
        return flowToUnifiedDocument(flow, config);
      });

      setDocuments(docs);

      // Calculate stats
      const grouped = groupDocumentsByStatus(docs);
      const newStats: Record<KanbanStatus, number> = {
        [KanbanStatus.PENDING]: grouped[KanbanStatus.PENDING].length,
        [KanbanStatus.PROCESSING]: grouped[KanbanStatus.PROCESSING].length,
        [KanbanStatus.COMPLETED]: grouped[KanbanStatus.COMPLETED].length,
        [KanbanStatus.REVIEWING]: grouped[KanbanStatus.REVIEWING].length,
        [KanbanStatus.CONFIRMED]: grouped[KanbanStatus.CONFIRMED].length,
        [KanbanStatus.FAILED]: grouped[KanbanStatus.FAILED].length,
      };
      setStats(newStats);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleStatClick = (status: KanbanStatus) => {
    navigate(`/board?status=${status}`);
  };

  const handleConfigClick = (configId: number) => {
    navigate(`/board?config=${configId}`);
  };

  const handleDocumentClick = (doc: UnifiedDocument) => {
    navigate(`/flows/${doc.id}`);
  };

  // Get recent documents (last 5)
  const recentDocuments = [...documents]
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .slice(0, 5);

  return (
    <Spin spinning={loading}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Stats Overview */}
        <Card title="文档状态概览">
          <StatsOverview stats={stats} onStatClick={handleStatClick} />
        </Card>

        <Row gutter={24}>
          {/* Document Types */}
          <Col xs={24} lg={12}>
            <Card
              title="文档类型"
              extra={
                <Button
                  type="link"
                  icon={<PlusOutlined />}
                  onClick={() => navigate('/configs/create')}
                >
                  新建
                </Button>
              }
            >
              {configs.length > 0 ? (
                <List
                  grid={{ gutter: 16, xs: 1, sm: 2, md: 2 }}
                  dataSource={configs.slice(0, 6)}
                  renderItem={(config) => (
                    <List.Item>
                      <Card
                        hoverable
                        size="small"
                        onClick={() => handleConfigClick(config.id)}
                        style={{ cursor: 'pointer' }}
                      >
                        <Space>
                          <FolderOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                          <div>
                            <Text strong>{config.name}</Text>
                            <br />
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {config.description || config.domain || '-'}
                            </Text>
                          </div>
                        </Space>
                      </Card>
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="暂无文档类型" />
              )}
              {configs.length > 6 && (
                <Button
                  type="link"
                  block
                  onClick={() => navigate('/configs')}
                  icon={<ArrowRightOutlined />}
                >
                  查看全部 ({configs.length})
                </Button>
              )}
            </Card>
          </Col>

          {/* Recent Documents */}
          <Col xs={24} lg={12}>
            <Card
              title="最近文档"
              extra={
                <Button type="link" onClick={() => navigate('/board')}>
                  查看全部 <ArrowRightOutlined />
                </Button>
              }
            >
              {recentDocuments.length > 0 ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {recentDocuments.map((doc) => (
                    <DocumentCard
                      key={doc.id}
                      document={doc}
                      onClick={handleDocumentClick}
                    />
                  ))}
                </Space>
              ) : (
                <Empty
                  image={<FileTextOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
                  description="暂无文档"
                >
                  <Button type="primary" onClick={() => navigate('/flows/create')}>
                    创建文档
                  </Button>
                </Empty>
              )}
            </Card>
          </Col>
        </Row>

        {/* Quick Actions */}
        <Card title="快捷操作">
          <Row gutter={16}>
            <Col xs={12} sm={6}>
              <Button
                type="primary"
                block
                size="large"
                icon={<PlusOutlined />}
                onClick={() => navigate('/flows/create')}
              >
                新建文档
              </Button>
            </Col>
            <Col xs={12} sm={6}>
              <Button
                block
                size="large"
                icon={<FolderOutlined />}
                onClick={() => navigate('/board')}
              >
                看板视图
              </Button>
            </Col>
            <Col xs={12} sm={6}>
              <Button
                block
                size="large"
                onClick={() => navigate('/configs')}
              >
                管理类型
              </Button>
            </Col>
            <Col xs={12} sm={6}>
              <Button
                block
                size="large"
                onClick={() => navigate('/schemas')}
              >
                管理模板
              </Button>
            </Col>
          </Row>
        </Card>
      </Space>
    </Spin>
  );
};

export default DashboardPage;
