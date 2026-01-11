import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  message,
  Spin,
  Row,
  Col,
  Typography,
  Table,
  Tooltip,
  Collapse,
  Alert,
} from 'antd';
import {
  ArrowLeftOutlined,
  LinkOutlined,
  EditOutlined,
  FileTextOutlined,
  AimOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { getFlow, getLangSmithTraceUrl } from '../services/api';
import type { DigiFlowWithResult, TextBlock, FieldWithSource } from '../types/digitization';
import {
  MainStatus,
  MainStatusLabels,
  DataOrigin,
  FileContentTypeLabels,
} from '../types/digitization';

const { Text, Paragraph } = Typography;

const statusColors: Record<MainStatus, string> = {
  [MainStatus.PENDING]: 'default',
  [MainStatus.IN_PROGRESS]: 'processing',
  [MainStatus.COMPLETED]: 'success',
  [MainStatus.FAILED]: 'error',
};

// Component to display a field value with its Block ID source
interface FieldWithSourceDisplayProps {
  fieldName: string;
  fieldData: FieldWithSource | unknown;
  onBlockClick?: (blockId: string) => void;
}

function FieldWithSourceDisplay({ fieldName, fieldData, onBlockClick }: FieldWithSourceDisplayProps) {
  // Check if this is a FieldWithSource object
  const hasDataSource = fieldData && typeof fieldData === 'object' && 'data_source' in (fieldData as object);

  if (!hasDataSource) {
    // Plain value without source tracking
    const displayValue = typeof fieldData === 'object' ? JSON.stringify(fieldData) : String(fieldData ?? '-');
    return (
      <Descriptions.Item label={fieldName}>
        {displayValue}
      </Descriptions.Item>
    );
  }

  const typedData = fieldData as FieldWithSource;
  const blockId = typedData.data_source?.block_id;
  const confidence = typedData.data_source?.confidence;

  return (
    <Descriptions.Item
      label={
        <Space>
          <span>{fieldName}</span>
          {blockId && (
            <Tooltip title={`来源: Block ${blockId}${confidence ? ` (置信度: ${(confidence * 100).toFixed(0)}%)` : ''}`}>
              <Tag
                color="blue"
                style={{ cursor: 'pointer', fontSize: '11px' }}
                onClick={() => onBlockClick?.(blockId)}
              >
                <AimOutlined /> {blockId}
              </Tag>
            </Tooltip>
          )}
        </Space>
      }
    >
      <Space>
        <span style={{ fontWeight: 500 }}>{String(typedData.value ?? '-')}</span>
        {confidence && confidence >= 0.9 && (
          <CheckCircleOutlined style={{ color: '#52c41a' }} />
        )}
      </Space>
    </Descriptions.Item>
  );
}

function FlowDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [flow, setFlow] = useState<DigiFlowWithResult | null>(null);
  const [highlightedBlockId, setHighlightedBlockId] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      fetchFlow(parseInt(id));
    }
  }, [id]);

  const fetchFlow = async (flowId: number) => {
    setLoading(true);
    try {
      const data = await getFlow(flowId);
      setFlow(data);
    } catch (error) {
      message.error('获取Flow详情失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleBlockClick = (blockId: string) => {
    setHighlightedBlockId(blockId);
    // Scroll to text blocks section
    document.getElementById('text-blocks-section')?.scrollIntoView({ behavior: 'smooth' });
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!flow) {
    return <div>Flow不存在</div>;
  }

  // Text blocks table columns
  const textBlockColumns = [
    {
      title: 'Block ID',
      dataIndex: 'block_id',
      key: 'block_id',
      width: 120,
      render: (blockId: string) => (
        <Tag color={blockId === highlightedBlockId ? 'gold' : 'blue'}>
          {blockId}
        </Tag>
      ),
    },
    {
      title: '页码',
      dataIndex: 'page',
      key: 'page',
      width: 60,
    },
    {
      title: '行',
      dataIndex: 'row',
      key: 'row',
      width: 60,
    },
    {
      title: '列',
      dataIndex: 'col',
      key: 'col',
      width: 60,
    },
    {
      title: '文本内容',
      dataIndex: 'text',
      key: 'text',
      render: (text: string, record: TextBlock) => (
        <span
          style={{
            backgroundColor: record.block_id === highlightedBlockId ? '#fff7e6' : undefined,
            padding: record.block_id === highlightedBlockId ? '2px 4px' : undefined,
          }}
        >
          {text}
        </span>
      ),
    },
    {
      title: '边界框',
      dataIndex: 'bbox',
      key: 'bbox',
      width: 200,
      render: (bbox: TextBlock['bbox']) => (
        bbox ? (
          <Text type="secondary" style={{ fontSize: 11 }}>
            ({bbox.x0.toFixed(0)}, {bbox.y0.toFixed(0)}) - ({bbox.x1.toFixed(0)}, {bbox.y1.toFixed(0)})
          </Text>
        ) : '-'
      ),
    },
  ];

  // Render extracted data fields with Block ID sources
  const renderExtractedData = () => {
    if (!flow.result?.data) {
      return <Text type="secondary">暂无提取结果</Text>;
    }

    const data = flow.result.data;
    const fields = Object.entries(data);

    return (
      <Descriptions bordered column={2} size="small">
        {fields.map(([key, value]) => (
          <FieldWithSourceDisplay
            key={key}
            fieldName={key}
            fieldData={value}
            onBlockClick={handleBlockClick}
          />
        ))}
      </Descriptions>
    );
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/flows')}>
          返回列表
        </Button>
      </div>

      <Row gutter={16}>
        {/* Left: Flow Info and Results */}
        <Col span={14}>
          <Card
            title={
              <Space>
                <FileTextOutlined />
                <span>Flow #{flow.id}</span>
                <Tag color={statusColors[flow.main_status as MainStatus]}>
                  {MainStatusLabels[flow.main_status as MainStatus]}
                </Tag>
              </Space>
            }
            extra={
              <Space>
                {flow.langsmith_trace_id && (
                  <Button
                    type="link"
                    icon={<LinkOutlined />}
                    href={getLangSmithTraceUrl(flow.langsmith_trace_id)}
                    target="_blank"
                  >
                    LangSmith Trace
                  </Button>
                )}
                <Button
                  icon={<EditOutlined />}
                  onClick={() => navigate(`/flows/${flow.id}/feedback`)}
                >
                  提交修正
                </Button>
              </Space>
            }
          >
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="Config ID">{flow.config_id}</Descriptions.Item>
              <Descriptions.Item label="Config版本">v{flow.config_version}</Descriptions.Item>
              <Descriptions.Item label="Schema ID">{flow.schema_id}</Descriptions.Item>
              <Descriptions.Item label="Schema版本">v{flow.schema_version}</Descriptions.Item>
              <Descriptions.Item label="文件类型">
                <Tag>{FileContentTypeLabels[flow.content_type as keyof typeof FileContentTypeLabels]}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="文件名">
                {flow.content_context?.file_name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间" span={2}>
                {new Date(flow.created_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* Extracted Results with Block ID visualization */}
          <Card
            title={
              <Space>
                <AimOutlined />
                <span>提取结果</span>
                {flow.result && (
                  <Tag color={flow.result.data_origin === DataOrigin.USER ? 'orange' : 'green'}>
                    {flow.result.data_origin === DataOrigin.USER ? '用户修正' : '系统提取'}
                  </Tag>
                )}
                {flow.result && <Tag>v{flow.result.version}</Tag>}
              </Space>
            }
            style={{ marginTop: 16 }}
          >
            {flow.main_status === MainStatus.COMPLETED ? (
              <>
                <Alert
                  message="Block ID 追踪"
                  description="每个提取的字段值都带有Block ID标签，点击可跳转到对应的源文本块。"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                {renderExtractedData()}
              </>
            ) : flow.main_status === MainStatus.FAILED ? (
              <Alert
                message="提取失败"
                description="请检查文件格式或重新处理。"
                type="error"
                showIcon
              />
            ) : (
              <Alert
                message="处理中"
                description="正在提取数据..."
                type="info"
                showIcon
              />
            )}
          </Card>

          {/* Text Blocks Section */}
          <Card
            id="text-blocks-section"
            title={
              <Space>
                <FileTextOutlined />
                <span>源文本块</span>
                {flow.result?.text_blocks && (
                  <Tag>{flow.result.text_blocks.length} 个文本块</Tag>
                )}
              </Space>
            }
            style={{ marginTop: 16 }}
          >
            {flow.result?.text_blocks && flow.result.text_blocks.length > 0 ? (
              <Table
                rowKey="block_id"
                columns={textBlockColumns}
                dataSource={flow.result.text_blocks}
                pagination={{ pageSize: 20 }}
                size="small"
                rowClassName={(record) =>
                  record.block_id === highlightedBlockId ? 'highlighted-row' : ''
                }
              />
            ) : (
              <Text type="secondary">暂无文本块数据</Text>
            )}
          </Card>
        </Col>

        {/* Right: File Preview / Metadata */}
        <Col span={10}>
          <Card title="文件信息">
            <Collapse
              defaultActiveKey={['content', 'metadata']}
              items={[
                {
                  key: 'content',
                  label: '内容上下文',
                  children: (
                    <Descriptions column={1} size="small">
                      <Descriptions.Item label="文件路径">
                        {flow.content_context?.file_path || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="文件名">
                        {flow.content_context?.file_name || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="文件类型">
                        {flow.content_context?.file_type || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="页数">
                        {flow.content_context?.pages || '-'}
                      </Descriptions.Item>
                    </Descriptions>
                  ),
                },
                {
                  key: 'metadata',
                  label: '元数据',
                  children: (
                    <Paragraph>
                      <pre style={{ fontSize: 11, maxHeight: 300, overflow: 'auto' }}>
                        {JSON.stringify(flow.content_metadata || {}, null, 2)}
                      </pre>
                    </Paragraph>
                  ),
                },
                {
                  key: 'langsmith',
                  label: 'LangSmith信息',
                  children: flow.langsmith_trace_id ? (
                    <Space direction="vertical">
                      <Text>Trace ID: {flow.langsmith_trace_id}</Text>
                      <Button
                        type="primary"
                        icon={<LinkOutlined />}
                        href={getLangSmithTraceUrl(flow.langsmith_trace_id)}
                        target="_blank"
                      >
                        在LangSmith中查看
                      </Button>
                      {flow.langsmith_metadata && (
                        <pre style={{ fontSize: 11, maxHeight: 200, overflow: 'auto' }}>
                          {JSON.stringify(flow.langsmith_metadata, null, 2)}
                        </pre>
                      )}
                    </Space>
                  ) : (
                    <Text type="secondary">未启用LangSmith追踪</Text>
                  ),
                },
                {
                  key: 'validation',
                  label: 'Schema验证',
                  children: (
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Tag color={flow.schema_validation_status === 1 ? 'success' : 'warning'}>
                        {flow.schema_validation_status === 1 ? '验证通过' : '待验证'}
                      </Tag>
                      {flow.schema_validation_result && (
                        <pre style={{ fontSize: 11, maxHeight: 200, overflow: 'auto' }}>
                          {JSON.stringify(flow.schema_validation_result, null, 2)}
                        </pre>
                      )}
                    </Space>
                  ),
                },
              ]}
            />
          </Card>

          {/* Plain Data (without data_source) */}
          {flow.result?.plain_data && (
            <Card title="纯数据 (无来源追踪)" style={{ marginTop: 16 }}>
              <pre style={{ fontSize: 12, maxHeight: 400, overflow: 'auto' }}>
                {JSON.stringify(flow.result.plain_data, null, 2)}
              </pre>
            </Card>
          )}
        </Col>
      </Row>

      <style>{`
        .highlighted-row {
          background-color: #fff7e6 !important;
        }
        .highlighted-row:hover {
          background-color: #ffe7ba !important;
        }
      `}</style>
    </div>
  );
}

export default FlowDetailPage;
