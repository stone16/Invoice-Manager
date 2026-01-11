import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  message,
  Typography,
  Select,
  DatePicker,
} from 'antd';
import {
  PlusOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { listFlows, listConfigs, getLangSmithTraceUrl } from '../services/api';
import type { DigiFlowWithResult, DigiFlowConfig } from '../types/digitization';
import {
  MainStatus,
  MainStatusLabels,
  FileContentTypeLabels,
} from '../types/digitization';
import dayjs from 'dayjs';

const { Title } = Typography;
const { RangePicker } = DatePicker;

const statusColors: Record<MainStatus, string> = {
  [MainStatus.PENDING]: 'default',
  [MainStatus.IN_PROGRESS]: 'processing',
  [MainStatus.COMPLETED]: 'success',
  [MainStatus.FAILED]: 'error',
};

function FlowListPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [flows, setFlows] = useState<DigiFlowWithResult[]>([]);
  const [configs, setConfigs] = useState<DigiFlowConfig[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [filterConfigId, setFilterConfigId] = useState<number | undefined>();
  const [filterStatus, setFilterStatus] = useState<number | undefined>();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

  const fetchConfigs = async () => {
    try {
      const response = await listConfigs();
      setConfigs(response.items);
    } catch (error) {
      console.error('获取Config列表失败', error);
    }
  };

  const fetchFlows = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        limit: pageSize,
        offset: (page - 1) * pageSize,
      };
      if (filterConfigId) {
        params.config_id = filterConfigId;
      }
      if (filterStatus !== undefined) {
        params.status = filterStatus;
      }
      if (dateRange) {
        params.start_date = dateRange[0].format('YYYY-MM-DD');
        params.end_date = dateRange[1].format('YYYY-MM-DD');
      }
      const response = await listFlows(params);
      setFlows(response.items);
      setTotal(response.total);
    } catch (error) {
      message.error('获取Flow列表失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfigs();
  }, []);

  useEffect(() => {
    fetchFlows();
  }, [page, pageSize]);

  const handleSearch = () => {
    setPage(1);
    fetchFlows();
  };

  const getConfigName = (configId: number) => {
    const config = configs.find(c => c.id === configId);
    return config?.name || `Config #${configId}`;
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'Config',
      dataIndex: 'config_id',
      key: 'config_id',
      render: (configId: number, record: DigiFlowWithResult) => (
        <Space direction="vertical" size={0}>
          <Tag color="purple">{getConfigName(configId)}</Tag>
          <Tag>v{record.config_version}</Tag>
        </Space>
      ),
    },
    {
      title: '文件类型',
      dataIndex: 'content_type',
      key: 'content_type',
      width: 100,
      render: (type: number) => (
        <Tag>{FileContentTypeLabels[type as keyof typeof FileContentTypeLabels] || type}</Tag>
      ),
    },
    {
      title: '文件名',
      key: 'file_name',
      render: (_: unknown, record: DigiFlowWithResult) => (
        record.content_context?.file_name || '-'
      ),
    },
    {
      title: '状态',
      dataIndex: 'main_status',
      key: 'main_status',
      width: 100,
      render: (status: MainStatus) => (
        <Tag color={statusColors[status]}>
          {MainStatusLabels[status]}
        </Tag>
      ),
    },
    {
      title: '结果版本',
      key: 'result_version',
      width: 100,
      render: (_: unknown, record: DigiFlowWithResult) => (
        record.result ? (
          <Tag color="green">v{record.result.version}</Tag>
        ) : (
          <Tag color="default">-</Tag>
        )
      ),
    },
    {
      title: 'LangSmith',
      dataIndex: 'langsmith_trace_id',
      key: 'langsmith_trace_id',
      width: 120,
      render: (traceId: string | null) => (
        traceId ? (
          <Button
            type="link"
            size="small"
            icon={<LinkOutlined />}
            href={getLangSmithTraceUrl(traceId)}
            target="_blank"
          >
            查看Trace
          </Button>
        ) : '-'
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: DigiFlowWithResult) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/flows/${record.id}`)}
        >
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Title level={4} style={{ margin: 0 }}>
            <ThunderboltOutlined style={{ marginRight: 8 }} />
            数字化流程
          </Title>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/flows/new')}
          >
            新建Flow
          </Button>
        </div>

        <div style={{ marginBottom: 16 }}>
          <Space wrap>
            <Select
              placeholder="选择Config"
              allowClear
              style={{ width: 200 }}
              value={filterConfigId}
              onChange={setFilterConfigId}
              options={configs.map(c => ({ value: c.id, label: c.name }))}
            />
            <Select
              placeholder="状态"
              allowClear
              style={{ width: 120 }}
              value={filterStatus}
              onChange={setFilterStatus}
              options={[
                { value: MainStatus.PENDING, label: MainStatusLabels[MainStatus.PENDING] },
                { value: MainStatus.IN_PROGRESS, label: MainStatusLabels[MainStatus.IN_PROGRESS] },
                { value: MainStatus.COMPLETED, label: MainStatusLabels[MainStatus.COMPLETED] },
                { value: MainStatus.FAILED, label: MainStatusLabels[MainStatus.FAILED] },
              ]}
            />
            <RangePicker
              value={dateRange}
              onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
            />
            <Button onClick={handleSearch}>搜索</Button>
          </Space>
        </div>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={flows}
          loading={loading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
        />
      </Card>
    </div>
  );
}

export default FlowListPage;
