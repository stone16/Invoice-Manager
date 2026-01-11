import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Input,
  Button,
  Space,
  message,
  Spin,
  Typography,
  Table,
  Tag,
  Select,
  Popconfirm,
  Alert,
  Divider,
} from 'antd';
import {
  ArrowLeftOutlined,
  SaveOutlined,
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { getFlow, submitFeedback } from '../services/api';
import type { DigiFlowWithResult, FeedbackSubmission, FieldWithSource } from '../types/digitization';
import {
  AuditReasonCode,
  AuditReasonCodeLabels,
  FeedbackSource,
} from '../types/digitization';

const { Text } = Typography;

interface CorrectionItem {
  key: string;
  field_path: string;
  old_value: string;
  new_value: string;
  reason_code: AuditReasonCode;
  reason_text: string;
}

function FlowFeedbackPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [flow, setFlow] = useState<DigiFlowWithResult | null>(null);
  const [corrections, setCorrections] = useState<CorrectionItem[]>([]);
  const [editingKey, setEditingKey] = useState<string | null>(null);

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

  const addCorrection = () => {
    const newKey = `new_${Date.now()}`;
    const newCorrection: CorrectionItem = {
      key: newKey,
      field_path: '',
      old_value: '',
      new_value: '',
      reason_code: AuditReasonCode.INCORRECT,
      reason_text: '',
    };
    setCorrections([...corrections, newCorrection]);
    setEditingKey(newKey);
  };

  const removeCorrection = (key: string) => {
    setCorrections(corrections.filter(c => c.key !== key));
    if (editingKey === key) {
      setEditingKey(null);
    }
  };

  const updateCorrection = (key: string, field: keyof CorrectionItem, value: unknown) => {
    setCorrections(corrections.map(c =>
      c.key === key ? { ...c, [field]: value } : c
    ));
  };

  const selectFieldFromResult = (fieldPath: string) => {
    if (!flow?.result?.data) return;

    const fieldData = flow.result.data[fieldPath] as FieldWithSource | undefined;
    const currentValue = fieldData?.value !== undefined ? String(fieldData.value) : '';

    const newKey = `field_${Date.now()}`;
    const newCorrection: CorrectionItem = {
      key: newKey,
      field_path: fieldPath,
      old_value: currentValue,
      new_value: currentValue,
      reason_code: AuditReasonCode.INCORRECT,
      reason_text: '',
    };
    setCorrections([...corrections, newCorrection]);
    setEditingKey(newKey);
  };

  const handleSubmit = async () => {
    if (corrections.length === 0) {
      message.warning('请至少添加一项修正');
      return;
    }

    // Validate corrections
    const invalidCorrections = corrections.filter(c => !c.field_path || c.new_value === c.old_value);
    if (invalidCorrections.length > 0) {
      message.error('请确保所有修正项都有字段路径且新值与旧值不同');
      return;
    }

    setSubmitting(true);
    try {
      const feedback: FeedbackSubmission = {
        corrections: corrections.map(c => ({
          field_path: c.field_path,
          new_value: c.new_value,
          reason_code: c.reason_code,
          reason_text: c.reason_text || undefined,
        })),
        source: FeedbackSource.UI,
      };

      const response = await submitFeedback(parseInt(id!), feedback);

      if (response.success) {
        message.success(`修正提交成功！创建了 ${response.audits_created} 条审计记录，结果版本更新为 v${response.result_version}`);
        navigate(`/flows/${id}`);
      } else {
        message.error(response.message || '提交失败');
      }
    } catch (error) {
      message.error('提交修正失败');
      console.error(error);
    } finally {
      setSubmitting(false);
    }
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

  // Get available fields from result
  const availableFields = flow.result?.data
    ? Object.keys(flow.result.data).filter(
        key => !corrections.some(c => c.field_path === key)
      )
    : [];

  const columns = [
    {
      title: '字段路径',
      dataIndex: 'field_path',
      key: 'field_path',
      width: 150,
      render: (value: string, record: CorrectionItem) => (
        editingKey === record.key ? (
          <Select
            style={{ width: '100%' }}
            value={value}
            onChange={(v) => {
              updateCorrection(record.key, 'field_path', v);
              // Auto-fill old value
              const fieldData = flow.result?.data?.[v] as FieldWithSource | undefined;
              if (fieldData?.value !== undefined) {
                updateCorrection(record.key, 'old_value', String(fieldData.value));
                updateCorrection(record.key, 'new_value', String(fieldData.value));
              }
            }}
            options={[
              { value: value, label: value },
              ...availableFields.map(f => ({ value: f, label: f })),
            ].filter(o => o.value)}
          />
        ) : (
          <Tag color="blue">{value || '-'}</Tag>
        )
      ),
    },
    {
      title: '原始值',
      dataIndex: 'old_value',
      key: 'old_value',
      width: 150,
      render: (value: string) => (
        <Text type="secondary">{value || '-'}</Text>
      ),
    },
    {
      title: '新值',
      dataIndex: 'new_value',
      key: 'new_value',
      width: 200,
      render: (value: string, record: CorrectionItem) => (
        editingKey === record.key ? (
          <Input
            value={value}
            onChange={(e) => updateCorrection(record.key, 'new_value', e.target.value)}
            placeholder="输入修正后的值"
          />
        ) : (
          <Text strong style={{ color: value !== record.old_value ? '#52c41a' : undefined }}>
            {value || '-'}
          </Text>
        )
      ),
    },
    {
      title: '原因',
      dataIndex: 'reason_code',
      key: 'reason_code',
      width: 150,
      render: (value: AuditReasonCode, record: CorrectionItem) => (
        editingKey === record.key ? (
          <Select
            style={{ width: '100%' }}
            value={value}
            onChange={(v) => updateCorrection(record.key, 'reason_code', v)}
            options={Object.entries(AuditReasonCodeLabels).map(([code, label]) => ({
              value: parseInt(code),
              label: label,
            }))}
          />
        ) : (
          <Tag>{AuditReasonCodeLabels[value]}</Tag>
        )
      ),
    },
    {
      title: '原因说明',
      dataIndex: 'reason_text',
      key: 'reason_text',
      render: (value: string, record: CorrectionItem) => (
        editingKey === record.key ? (
          <Input
            value={value}
            onChange={(e) => updateCorrection(record.key, 'reason_text', e.target.value)}
            placeholder="可选：详细说明"
          />
        ) : (
          <Text type="secondary">{value || '-'}</Text>
        )
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: CorrectionItem) => (
        <Space>
          {editingKey === record.key ? (
            <Button
              type="link"
              size="small"
              onClick={() => setEditingKey(null)}
            >
              完成
            </Button>
          ) : (
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => setEditingKey(record.key)}
            >
              编辑
            </Button>
          )}
          <Popconfirm
            title="确定删除此修正项？"
            onConfirm={() => removeCorrection(record.key)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/flows/${id}`)}>
          返回Flow详情
        </Button>
      </div>

      <Card
        title={
          <Space>
            <EditOutlined />
            <span>提交修正 - Flow #{flow.id}</span>
            {flow.result && <Tag color="green">当前版本: v{flow.result.version}</Tag>}
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSubmit}
            loading={submitting}
            disabled={corrections.length === 0}
          >
            提交修正
          </Button>
        }
      >
        <Alert
          message="字段修正说明"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li>选择需要修正的字段，输入正确的值</li>
              <li>选择修正原因以便后续分析和改进</li>
              <li>提交后将创建审计记录，并更新结果版本</li>
              <li>修正后的数据将用于RAG训练，改进未来的提取质量</li>
            </ul>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        {/* Quick add from existing fields */}
        {availableFields.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Text strong>快速添加字段修正：</Text>
            <div style={{ marginTop: 8 }}>
              <Space wrap>
                {availableFields.slice(0, 10).map(field => (
                  <Button
                    key={field}
                    size="small"
                    onClick={() => selectFieldFromResult(field)}
                  >
                    {field}
                  </Button>
                ))}
                {availableFields.length > 10 && (
                  <Text type="secondary">+{availableFields.length - 10} 更多字段</Text>
                )}
              </Space>
            </div>
          </div>
        )}

        <Divider />

        <div style={{ marginBottom: 16 }}>
          <Button
            type="dashed"
            icon={<PlusOutlined />}
            onClick={addCorrection}
            style={{ width: '100%' }}
          >
            添加修正项
          </Button>
        </div>

        <Table
          rowKey="key"
          columns={columns}
          dataSource={corrections}
          pagination={false}
          locale={{ emptyText: '暂无修正项，点击上方按钮添加' }}
        />

        {corrections.length > 0 && (
          <div style={{ marginTop: 16, textAlign: 'right' }}>
            <Space>
              <Text type="secondary">共 {corrections.length} 项修正</Text>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSubmit}
                loading={submitting}
              >
                提交修正
              </Button>
            </Space>
          </div>
        )}
      </Card>
    </div>
  );
}

export default FlowFeedbackPage;
