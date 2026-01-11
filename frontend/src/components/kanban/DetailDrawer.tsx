import React, { useState, useEffect } from 'react';
import {
  Drawer,
  Descriptions,
  Typography,
  Space,
  Button,
  Tabs,
  Table,
  Tag,
  Spin,
  Empty,
  message,
} from 'antd';
import {
  EditOutlined,
  HistoryOutlined,
  FileTextOutlined,
  ExportOutlined,
} from '@ant-design/icons';
import { UnifiedDocument } from '../../types/kanban';
import { DigiFlowResultFieldAudit, MainStatusLabels, MainStatus } from '../../types/digitization';
import { StatusBadge } from './StatusBadge';
import { getFlowAuditHistory } from '../../services/api';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

interface DetailDrawerProps {
  document: UnifiedDocument | null;
  open: boolean;
  onClose: () => void;
  onEdit?: (doc: UnifiedDocument) => void;
}

/**
 * DetailDrawer - Side panel showing document details
 * Includes: basic info, extracted data, audit history
 */
export const DetailDrawer: React.FC<DetailDrawerProps> = ({
  document,
  open,
  onClose,
  onEdit,
}) => {
  const [activeTab, setActiveTab] = useState('info');
  const [auditHistory, setAuditHistory] = useState<DigiFlowResultFieldAudit[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Load audit history when document changes
  useEffect(() => {
    if (document && open) {
      loadAuditHistory(document.id);
    }
  }, [document?.id, open]);

  const loadAuditHistory = async (flowId: number) => {
    setLoadingHistory(true);
    try {
      const history = await getFlowAuditHistory(flowId);
      setAuditHistory(history.items);
    } catch (error) {
      console.error('Failed to load audit history:', error);
      message.error('加载审核历史失败');
    } finally {
      setLoadingHistory(false);
    }
  };

  if (!document) {
    return null;
  }

  const flow = document.raw;
  const result = flow.result;

  // Audit history columns
  const auditColumns = [
    {
      title: '字段',
      dataIndex: 'field_path',
      key: 'field_path',
      width: 120,
    },
    {
      title: '旧值',
      dataIndex: 'old_value',
      key: 'old_value',
      width: 100,
      render: (val: unknown) => (
        <Text type="secondary" delete>
          {String(val ?? '-')}
        </Text>
      ),
    },
    {
      title: '新值',
      dataIndex: 'new_value',
      key: 'new_value',
      width: 100,
      render: (val: unknown) => <Text strong>{String(val ?? '-')}</Text>,
    },
    {
      title: '时间',
      dataIndex: 'audited_at',
      key: 'audited_at',
      width: 150,
      render: (val: string) => dayjs(val).format('MM-DD HH:mm'),
    },
  ];

  // Extracted data columns
  const dataColumns = [
    {
      title: '字段',
      dataIndex: 'field',
      key: 'field',
      width: 120,
    },
    {
      title: '值',
      dataIndex: 'value',
      key: 'value',
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 80,
      render: (source: string) => (
        <Tag color={source === 'user' ? 'blue' : 'default'}>
          {source === 'user' ? '人工' : '系统'}
        </Tag>
      ),
    },
  ];

  // Convert result data to table format
  const extractedData = result?.data
    ? Object.entries(result.data).map(([key, fieldWithSource]) => ({
        key,
        field: key,
        value: String(fieldWithSource?.value ?? '-'),
        source: fieldWithSource?.data_source ? 'system' : 'user',
      }))
    : [];

  const tabItems = [
    {
      key: 'info',
      label: (
        <span>
          <FileTextOutlined />
          基本信息
        </span>
      ),
      children: (
        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label="文档ID">{document.id}</Descriptions.Item>
          <Descriptions.Item label="文件名">{document.title}</Descriptions.Item>
          <Descriptions.Item label="文档类型">{document.subtitle || '-'}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <StatusBadge status={document.status} />
          </Descriptions.Item>
          <Descriptions.Item label="原始状态">
            <Tag>{MainStatusLabels[document.originalStatus as MainStatus]}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="文件类型">{document.fileType || '-'}</Descriptions.Item>
          <Descriptions.Item label="页数">{document.pageCount ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="文本块数">{document.blockCount ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="结果版本">v{document.version ?? 1}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {dayjs(document.createdAt).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {document.updatedAt
              ? dayjs(document.updatedAt).format('YYYY-MM-DD HH:mm:ss')
              : '-'}
          </Descriptions.Item>
          {document.langsmithTraceId && (
            <Descriptions.Item label="Trace ID">
              <Text copyable={{ text: document.langsmithTraceId }}>
                {document.langsmithTraceId.slice(0, 8)}...
              </Text>
            </Descriptions.Item>
          )}
        </Descriptions>
      ),
    },
    {
      key: 'data',
      label: (
        <span>
          <EditOutlined />
          提取数据
        </span>
      ),
      children: (
        <>
          {extractedData.length > 0 ? (
            <Table
              dataSource={extractedData}
              columns={dataColumns}
              size="small"
              pagination={false}
              scroll={{ y: 400 }}
            />
          ) : (
            <Empty description="暂无提取数据" />
          )}
        </>
      ),
    },
    {
      key: 'history',
      label: (
        <span>
          <HistoryOutlined />
          修改历史
        </span>
      ),
      children: (
        <Spin spinning={loadingHistory}>
          {auditHistory.length > 0 ? (
            <Table
              dataSource={auditHistory}
              columns={auditColumns}
              size="small"
              pagination={{ pageSize: 10 }}
              rowKey="id"
            />
          ) : (
            <Empty description="暂无修改记录" />
          )}
        </Spin>
      ),
    },
  ];

  return (
    <Drawer
      title={
        <Space>
          <Title level={5} style={{ margin: 0 }}>
            {document.title}
          </Title>
          <StatusBadge status={document.status} size="small" />
        </Space>
      }
      placement="right"
      width={480}
      open={open}
      onClose={onClose}
      extra={
        <Space>
          {onEdit && (
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => onEdit(document)}
            >
              编辑
            </Button>
          )}
          <Button
            icon={<ExportOutlined />}
            onClick={() => window.open(`/flows/${document.id}`, '_blank')}
          >
            详情页
          </Button>
        </Space>
      }
    >
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="small"
      />
    </Drawer>
  );
};

export default DetailDrawer;
