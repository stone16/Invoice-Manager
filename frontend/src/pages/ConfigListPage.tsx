import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  message,
  Input,
  Typography,
  Select,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  SearchOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { listConfigs, listSchemas } from '../services/api';
import type { DigiFlowConfig, DigiFlowSchema } from '../types/digitization';
import { ConfigStatus, ConfigStatusLabels, SourceContentTypeLabels } from '../types/digitization';

const { Title } = Typography;

function ConfigListPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [configs, setConfigs] = useState<DigiFlowConfig[]>([]);
  const [schemas, setSchemas] = useState<DigiFlowSchema[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [filterSchemaId, setFilterSchemaId] = useState<number | undefined>();
  const [filterDomain, setFilterDomain] = useState('');

  const fetchSchemas = async () => {
    try {
      const response = await listSchemas({ page_size: 100 });
      setSchemas(response.items);
    } catch (error) {
      console.error('获取Schema列表失败', error);
    }
  };

  const fetchConfigs = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
      };
      if (filterSchemaId) {
        params.schema_id = filterSchemaId;
      }
      if (filterDomain) {
        params.domain = filterDomain;
      }
      const response = await listConfigs(params);
      setConfigs(response.items);
      setTotal(response.total);
    } catch (error) {
      message.error('获取Config列表失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchemas();
  }, []);

  useEffect(() => {
    fetchConfigs();
  }, [page, pageSize]);

  const handleSearch = () => {
    setPage(1);
    fetchConfigs();
  };

  const getSchemaName = (schemaId: number) => {
    const schema = schemas.find(s => s.id === schemaId);
    return schema?.name || `Schema #${schemaId}`;
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'Slug',
      dataIndex: 'slug',
      key: 'slug',
      render: (slug: string) => (
        <Tag color="purple">{slug}</Tag>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '关联Schema',
      dataIndex: 'schema_id',
      key: 'schema_id',
      render: (schemaId: number, record: DigiFlowConfig) => (
        <Space>
          <Tag color="blue">{getSchemaName(schemaId)}</Tag>
          <Tag>v{record.schema_version}</Tag>
        </Space>
      ),
    },
    {
      title: '输入类型',
      dataIndex: 'source_content_type',
      key: 'source_content_type',
      width: 100,
      render: (type: number) => (
        <Tag>{SourceContentTypeLabels[type as keyof typeof SourceContentTypeLabels] || type}</Tag>
      ),
    },
    {
      title: '领域',
      dataIndex: 'domain',
      key: 'domain',
      width: 100,
      render: (domain: string | null) => domain || '-',
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 80,
      render: (version: number) => (
        <Tag>v{version}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: ConfigStatus) => (
        <Tag color={status === ConfigStatus.ACTIVE ? 'success' : 'default'}>
          {ConfigStatusLabels[status]}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: DigiFlowConfig) => (
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => navigate(`/configs/${record.id}`)}
        >
          编辑
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Title level={4} style={{ margin: 0 }}>
            <SettingOutlined style={{ marginRight: 8 }} />
            Config管理
          </Title>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/configs/new')}
          >
            新建Config
          </Button>
        </div>

        <div style={{ marginBottom: 16 }}>
          <Space>
            <Select
              placeholder="选择Schema"
              allowClear
              style={{ width: 200 }}
              value={filterSchemaId}
              onChange={setFilterSchemaId}
              options={schemas.map(s => ({ value: s.id, label: s.name }))}
            />
            <Input
              placeholder="领域"
              value={filterDomain}
              onChange={(e) => setFilterDomain(e.target.value)}
              onPressEnter={handleSearch}
              style={{ width: 150 }}
              prefix={<SearchOutlined />}
            />
            <Button onClick={handleSearch}>搜索</Button>
          </Space>
        </div>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={configs}
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

export default ConfigListPage;
