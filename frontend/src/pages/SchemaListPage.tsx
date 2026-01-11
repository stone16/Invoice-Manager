import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  message,
  Popconfirm,
  Input,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { listSchemas, deleteSchema } from '../services/api';
import type { DigiFlowSchema } from '../types/digitization';
import { ConfigStatus, ConfigStatusLabels } from '../types/digitization';

const { Title } = Typography;

function SchemaListPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [schemas, setSchemas] = useState<DigiFlowSchema[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchSlug, setSearchSlug] = useState('');

  const fetchSchemas = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
      };
      if (searchSlug) {
        params.slug = searchSlug;
      }
      const response = await listSchemas(params);
      setSchemas(response.items);
      setTotal(response.total);
    } catch (error) {
      message.error('获取Schema列表失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchemas();
  }, [page, pageSize]);

  const handleDelete = async (id: number) => {
    try {
      await deleteSchema(id);
      message.success('删除成功');
      fetchSchemas();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSearch = () => {
    setPage(1);
    fetchSchemas();
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
        <Tag color="blue">{slug}</Tag>
      ),
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
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
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: DigiFlowSchema) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => navigate(`/schemas/${record.id}`)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除此Schema吗？"
            description="删除后将归档此Schema"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Title level={4} style={{ margin: 0 }}>
            <FileTextOutlined style={{ marginRight: 8 }} />
            Schema管理
          </Title>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/schemas/new')}
          >
            新建Schema
          </Button>
        </div>

        <div style={{ marginBottom: 16 }}>
          <Space>
            <Input
              placeholder="搜索Slug"
              value={searchSlug}
              onChange={(e) => setSearchSlug(e.target.value)}
              onPressEnter={handleSearch}
              style={{ width: 200 }}
              prefix={<SearchOutlined />}
            />
            <Button onClick={handleSearch}>搜索</Button>
          </Space>
        </div>

        <Table
          rowKey="id"
          columns={columns}
          dataSource={schemas}
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

export default SchemaListPage;
