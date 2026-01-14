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
  Table,
  Form,
  Input,
  Select,
  Modal,
  Alert,
  Tooltip,
} from 'antd';
import { ArrowLeftOutlined, EditOutlined, SaveOutlined, CheckOutlined, SyncOutlined, WarningOutlined } from '@ant-design/icons';
import { getInvoice, getInvoiceFileUrl, updateInvoice, resolveDiff, confirmInvoice, reprocessInvoice } from '../services/api';
import type { InvoiceDetail, ParsingDiff } from '../types/invoice';
import { InvoiceStatus } from '../types/invoice';

const statusColors: Record<string, string> = {
  '待处理': 'default',
  '待审核': 'processing',
  '已确认': 'success',
  '已报销': 'green',
  '未报销': 'warning',
};

const fieldLabels: Record<string, string> = {
  invoice_number: '发票号码',
  issue_date: '开票日期',
  buyer_name: '购买方名称',
  buyer_tax_id: '购买方纳税人识别号',
  seller_name: '销售方名称',
  seller_tax_id: '销售方纳税人识别号',
  item_name: '项目名称',
  total_with_tax: '价税合计',
  specification: '规格型号',
  unit: '单位',
  quantity: '数量',
  unit_price: '单价',
  amount: '金额',
  tax_rate: '税率',
  tax_amount: '税额',
};

function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [form] = Form.useForm();
  const [resolvingDiff, setResolvingDiff] = useState<number | null>(null);
  const [customValueModal, setCustomValueModal] = useState<{ visible: boolean; diffId: number | null; fieldName: string }>({
    visible: false,
    diffId: null,
    fieldName: '',
  });
  const [customValue, setCustomValue] = useState('');

  const fetchInvoice = async () => {
    if (!id) return;

    setLoading(true);
    try {
      const data = await getInvoice(parseInt(id));
      setInvoice(data);
      form.setFieldsValue(data);
    } catch (error) {
      message.error('获取发票详情失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoice();
  }, [id]);

  const handleSave = async () => {
    if (!id || !invoice) return;

    try {
      const values = await form.validateFields();
      await updateInvoice(parseInt(id), values);
      message.success('保存成功');
      setEditMode(false);
      fetchInvoice();
    } catch (error) {
      message.error('保存失败');
    }
  };

  const handleResolveDiff = async (diffId: number, source: 'ocr' | 'llm' | 'custom', customVal?: string) => {
    if (!id) return;
    setResolvingDiff(diffId);
    try {
      const result = await resolveDiff(parseInt(id), diffId, source, customVal);
      message.success(`${fieldLabels[result.field_name] || result.field_name} 已解决`);
      if (result.all_resolved) {
        message.success('所有差异已解决，发票已确认');
      }
      fetchInvoice();
    } catch (error) {
      message.error('解决差异失败');
    } finally {
      setResolvingDiff(null);
    }
  };

  const handleConfirmAll = async () => {
    if (!id) return;

    if (invoice) {
      const requiredFields: Array<keyof InvoiceDetail> = [
        'invoice_number',
        'issue_date',
        'total_with_tax',
        'buyer_name',
        'buyer_tax_id',
        'seller_name',
        'seller_tax_id',
        'item_name',
      ];
      const missing = requiredFields.filter((field) => {
        const value = invoice[field];
        if (value === null || value === undefined) {
          return true;
        }
        if (typeof value === 'string') {
          return value.trim().length === 0;
        }
        return false;
      });

      if (missing.length > 0) {
        message.error('请先补全必填字段，再进行确认。');
        return;
      }
    }

    try {
      await confirmInvoice(parseInt(id));
      message.success(invoice?.llm_result ? '发票已确认' : '发票已确认（OCR-only）');
      fetchInvoice();
    } catch (error: unknown) {
      // Handle specific error from backend
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { data?: { detail?: string } } };
        if (axiosError.response?.data?.detail) {
          message.error(axiosError.response.data.detail);
          return;
        }
      }
      message.error('确认失败');
    }
  };

  const handleReprocess = async () => {
    if (!id) return;
    setLoading(true);
    try {
      await reprocessInvoice(parseInt(id));
      message.success('重新解析完成');
      fetchInvoice();
    } catch (error) {
      message.error('重新解析失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCustomValueSubmit = async () => {
    if (customValueModal.diffId) {
      await handleResolveDiff(customValueModal.diffId, 'custom', customValue);
      setCustomValueModal({ visible: false, diffId: null, fieldName: '' });
      setCustomValue('');
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!invoice) {
    return <div>发票不存在</div>;
  }

  const hasLlm = Boolean(invoice.llm_result);
  const hasDiffs = Boolean(invoice.parsing_diffs && invoice.parsing_diffs.length > 0);
  const hasUnresolvedDiffs = Boolean(invoice.parsing_diffs && invoice.parsing_diffs.some(d => !d.resolved));

  const diffColumns = [
    {
      title: '字段',
      dataIndex: 'field_name',
      key: 'field_name',
      width: 120,
      render: (val: string) => fieldLabels[val] || val,
    },
    {
      title: 'OCR结果',
      dataIndex: 'ocr_value',
      key: 'ocr_value',
      render: (val: string | null, record: ParsingDiff) => (
        <Space>
          <span style={{ color: record.source === 'ocr' ? '#52c41a' : undefined }}>
            {val || '-'}
          </span>
          {!record.resolved && val && (
            <Button
              type="link"
              size="small"
              loading={resolvingDiff === record.id}
              onClick={() => handleResolveDiff(record.id, 'ocr')}
            >
              选择
            </Button>
          )}
        </Space>
      ),
    },
    {
      title: 'LLM结果',
      dataIndex: 'llm_value',
      key: 'llm_value',
      render: (val: string | null, record: ParsingDiff) => (
        <Space>
          <span style={{ color: record.source === 'llm' ? '#52c41a' : undefined }}>
            {val || '-'}
          </span>
          {!record.resolved && val && (
            <Button
              type="link"
              size="small"
              loading={resolvingDiff === record.id}
              onClick={() => handleResolveDiff(record.id, 'llm')}
            >
              选择
            </Button>
          )}
        </Space>
      ),
    },
    {
      title: '最终值',
      dataIndex: 'final_value',
      key: 'final_value',
      render: (val: string | null) => (
        <span style={{ fontWeight: 'bold', color: val ? '#1890ff' : undefined }}>
          {val || '-'}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'resolved',
      key: 'resolved',
      width: 100,
      render: (val: number) => (
        <Tag color={val ? 'success' : 'warning'}>{val ? '已解决' : '待确认'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: ParsingDiff) => (
        !record.resolved && (
          <Button
            type="link"
            size="small"
            onClick={() => {
              setCustomValueModal({ visible: true, diffId: record.id, fieldName: record.field_name });
              setCustomValue(record.ocr_value || record.llm_value || '');
            }}
          >
            自定义
          </Button>
        )
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
          返回列表
        </Button>
      </div>

      <Row gutter={16}>
        {/* Left: Invoice Info */}
        <Col span={14}>
          <Card
            title="发票信息"
            extra={
              <Space>
                {editMode ? (
                  <>
                    <Button onClick={() => setEditMode(false)}>取消</Button>
                    <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
                      保存
                    </Button>
                  </>
                ) : (
                  <Button icon={<EditOutlined />} onClick={() => setEditMode(true)}>
                    编辑
                  </Button>
                )}
              </Space>
            }
          >
            {editMode ? (
              <Form form={form} layout="vertical">
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="invoice_number" label="发票号码">
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="issue_date" label="开票日期">
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="buyer_name" label="购买方名称">
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="buyer_tax_id" label="购买方纳税人识别号">
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="seller_name" label="销售方名称">
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="seller_tax_id" label="销售方纳税人识别号">
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col span={24}>
                    <Form.Item name="item_name" label="项目名称">
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="total_with_tax" label="价税合计">
                      <Input type="number" />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="amount" label="金额">
                      <Input type="number" />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="tax_amount" label="税额">
                      <Input type="number" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="status" label="状态">
                      <Select
                        options={Object.values(InvoiceStatus).map((s) => ({
                          label: s,
                          value: s,
                        }))}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="owner" label="归属人">
                      <Input />
                    </Form.Item>
                  </Col>
                </Row>
              </Form>
            ) : (
              <Descriptions column={2} bordered size="small">
                <Descriptions.Item label="发票号码">
                  {invoice.invoice_number || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="开票日期">
                  {invoice.issue_date || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="购买方名称">
                  {invoice.buyer_name || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="购买方纳税人识别号">
                  {invoice.buyer_tax_id || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="销售方名称">
                  {invoice.seller_name || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="销售方纳税人识别号">
                  {invoice.seller_tax_id || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="项目名称" span={2}>
                  {invoice.item_name || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="规格型号">
                  {invoice.specification || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="单位">
                  {invoice.unit || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="数量">
                  {invoice.quantity != null ? invoice.quantity : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="单价">
                  {invoice.unit_price != null ? invoice.unit_price : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="金额">
                  {invoice.amount != null ? `¥${Number(invoice.amount).toFixed(2)}` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="税率">
                  {invoice.tax_rate || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="税额">
                  {invoice.tax_amount != null ? `¥${Number(invoice.tax_amount).toFixed(2)}` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="价税合计">
                  {invoice.total_with_tax != null ? `¥${Number(invoice.total_with_tax).toFixed(2)}` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={statusColors[invoice.status] || 'default'}>
                    {invoice.status}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="归属人">
                  {invoice.owner || '-'}
                </Descriptions.Item>
              </Descriptions>
            )}
          </Card>

          {/* Comparison & Review Section */}
          <Card
            title={
              <Space>
                <span>解析结果与审核</span>
                {!hasLlm && (
                  <Tag color="processing" icon={<WarningOutlined />}>
                    OCR-only
                  </Tag>
                )}
                {hasLlm && hasUnresolvedDiffs && (
                  <Tag color="warning">
                    {invoice.parsing_diffs?.filter(d => !d.resolved).length} 项待确认
                  </Tag>
                )}
                {hasLlm && hasDiffs && !hasUnresolvedDiffs && (
                  <Tag color="success">
                    已完成比对
                  </Tag>
                )}
              </Space>
            }
            extra={
              <Space>
                <Button
                  icon={<SyncOutlined />}
                  onClick={handleReprocess}
                  loading={loading}
                >
                  重新解析
                </Button>
                {hasLlm && hasUnresolvedDiffs && (
                  <Button
                    type="primary"
                    icon={<CheckOutlined />}
                    onClick={handleConfirmAll}
                  >
                    全部确认
                  </Button>
                )}
                {!hasLlm && (
                  <Tooltip title="OCR-only 结果可手动确认">
                    <Button
                      type="primary"
                      icon={<CheckOutlined />}
                      onClick={handleConfirmAll}
                    >
                      确认（仅OCR）
                    </Button>
                  </Tooltip>
                )}
              </Space>
            }
            style={{ marginTop: 16 }}
          >
            {!hasLlm && (
              <Alert
                message="OCR预处理完成（可手动确认）"
                description={
                  <span>
                    发票已通过OCR识别预处理，可直接编辑后确认。配置LLM服务可获得更精准的智能比对功能，点击"重新解析"启用双重校验。
                  </span>
                }
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}
            {hasDiffs ? (
              <Table
                rowKey="id"
                columns={diffColumns}
                dataSource={invoice.parsing_diffs}
                pagination={false}
                size="small"
              />
            ) : (
              <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                {hasLlm ? '无比对差异' : 'OCR-only 模式暂无比对数据'}
              </div>
            )}
          </Card>

          {/* Custom Value Modal */}
          <Modal
            title={`自定义值 - ${fieldLabels[customValueModal.fieldName] || customValueModal.fieldName}`}
            open={customValueModal.visible}
            onOk={handleCustomValueSubmit}
            onCancel={() => {
              setCustomValueModal({ visible: false, diffId: null, fieldName: '' });
              setCustomValue('');
            }}
            okText="确定"
            cancelText="取消"
          >
            <Input
              value={customValue}
              onChange={(e) => setCustomValue(e.target.value)}
              placeholder="请输入自定义值"
            />
          </Modal>
        </Col>

        {/* Right: File Preview */}
        <Col span={10}>
          <Card title="原始文件">
            {invoice.file_type === 'pdf' ? (
              <iframe
                src={getInvoiceFileUrl(invoice.id)}
                style={{ width: '100%', height: 600, border: 'none' }}
                title="PDF Preview"
              />
            ) : (
              <img
                src={getInvoiceFileUrl(invoice.id)}
                alt="Invoice"
                style={{ width: '100%', maxHeight: 600, objectFit: 'contain' }}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default InvoiceDetailPage;
