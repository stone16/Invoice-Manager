import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  Button,
  Space,
  message,
  Spin,
  Typography,
  Tabs,
  Alert,
  Divider,
  Tag,
} from 'antd';
import {
  ArrowLeftOutlined,
  SaveOutlined,
  FileTextOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { load as loadYaml } from 'js-yaml';
import { getSchema, createSchema, updateSchema } from '../services/api';
import type { DigiFlowSchema, DigiFlowSchemaCreate, DigiFlowSchemaUpdate } from '../types/digitization';

const { Title, Text } = Typography;
const { TextArea } = Input;

function SchemaEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isNew = id === 'new';

  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [schema, setSchema] = useState<DigiFlowSchema | null>(null);
  const [form] = Form.useForm();
  const [yamlContent, setYamlContent] = useState('');
  const [jsonContent, setJsonContent] = useState('{}');
  const [parseError, setParseError] = useState<string | null>(null);

  useEffect(() => {
    if (!isNew && id) {
      fetchSchema(parseInt(id));
    }
  }, [id, isNew]);

  const fetchSchema = async (schemaId: number) => {
    setLoading(true);
    try {
      const data = await getSchema(schemaId);
      setSchema(data);
      form.setFieldsValue({
        slug: data.slug,
        name: data.name,
      });
      setYamlContent(data.yaml_schema || '');
      setJsonContent(JSON.stringify(data.schema, null, 2));
    } catch (error) {
      message.error('获取Schema失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const parseYamlToJson = (yaml: string): Record<string, unknown> | null => {
    try {
      if (yaml.trim().startsWith('{')) {
        return JSON.parse(yaml);
      }

      const parsed = loadYaml(yaml);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
      return null;
    } catch {
      return null;
    }
  };

  const handleYamlChange = (value: string) => {
    setYamlContent(value);
    setParseError(null);

    if (!value.trim()) {
      setJsonContent('{}');
      return;
    }

    const parsed = parseYamlToJson(value);
    if (parsed) {
      setJsonContent(JSON.stringify(parsed, null, 2));
    } else {
      setJsonContent('{}');
      setParseError('YAML解析失败，请检查格式');
    }
  };

  const handleJsonChange = (value: string) => {
    setJsonContent(value);
    setParseError(null);

    try {
      JSON.parse(value);
    } catch {
      setParseError('JSON格式无效');
    }
  };

  const handleSave = async () => {
    try {
      if (parseError) {
        message.error(parseError);
        return;
      }

      const values = await form.validateFields();

      let schemaObj: Record<string, unknown> | undefined;
      try {
        const parsed = JSON.parse(jsonContent);
        // Only use the parsed JSON if it has actual content (not empty object)
        // Otherwise, let the backend parse the YAML
        if (Object.keys(parsed).length > 0) {
          schemaObj = parsed;
        }
      } catch {
        // JSON parsing failed - if we have YAML, let backend parse it
        if (!yamlContent?.trim()) {
          message.error('Schema JSON格式无效');
          return;
        }
      }

      // Must have either valid YAML or valid JSON schema
      if (!yamlContent?.trim() && !schemaObj) {
        message.error('请提供YAML或JSON格式的Schema定义');
        return;
      }

      setSaving(true);

      if (isNew) {
        const createData: DigiFlowSchemaCreate = {
          slug: values.slug,
          name: values.name,
          yaml_schema: yamlContent || undefined,
          schema: schemaObj,
        };
        await createSchema(createData);
        message.success('Schema创建成功');
      } else if (id) {
        const updateData: DigiFlowSchemaUpdate = {
          name: values.name,
          yaml_schema: yamlContent || undefined,
          schema: schemaObj,
        };
        await updateSchema(parseInt(id), updateData);
        message.success('Schema更新成功');
      }

      navigate('/schemas');
    } catch (error) {
      message.error('保存失败');
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  const tabItems = [
    {
      key: 'yaml',
      label: (
        <span>
          <FileTextOutlined />
          YAML编辑
        </span>
      ),
      children: (
        <div>
          <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
            使用YAML格式定义Schema结构（推荐）
          </Text>
          <TextArea
            value={yamlContent}
            onChange={(e) => handleYamlChange(e.target.value)}
            placeholder={`# 示例Schema定义
type: object
properties:
  invoice_number:
    type: string
    description: 发票号码
  issue_date:
    type: string
    description: 开票日期
  total_amount:
    type: number
    description: 金额
required:
  - invoice_number`}
            style={{ fontFamily: 'monospace', minHeight: 400 }}
            autoSize={{ minRows: 15, maxRows: 30 }}
          />
        </div>
      ),
    },
    {
      key: 'json',
      label: (
        <span>
          <CodeOutlined />
          JSON预览
        </span>
      ),
      children: (
        <div>
          <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
            JSON Schema格式（用于验证）
          </Text>
          <TextArea
            value={jsonContent}
            onChange={(e) => handleJsonChange(e.target.value)}
            placeholder="{}"
            style={{ fontFamily: 'monospace', minHeight: 400 }}
            autoSize={{ minRows: 15, maxRows: 30 }}
          />
        </div>
      ),
    },
  ];

  return (
    <div>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/schemas')}
          >
            返回列表
          </Button>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <Title level={4} style={{ margin: 0 }}>
            <FileTextOutlined style={{ marginRight: 8 }} />
            {isNew ? '新建Schema' : `编辑Schema: ${schema?.name}`}
            {schema && (
              <Tag color="blue" style={{ marginLeft: 8 }}>v{schema.version}</Tag>
            )}
          </Title>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
          >
            保存
          </Button>
        </div>

        <Form form={form} layout="vertical">
          <Space style={{ width: '100%' }} size="large">
            <Form.Item
              name="slug"
              label="Slug (标识符)"
              rules={[
                { required: true, message: '请输入Slug' },
                { pattern: /^[a-z0-9_-]+$/, message: 'Slug只能包含小写字母、数字、下划线和连字符' },
              ]}
              style={{ width: 300 }}
            >
              <Input placeholder="invoice_standard" disabled={!isNew} />
            </Form.Item>
            <Form.Item
              name="name"
              label="名称"
              rules={[{ required: true, message: '请输入名称' }]}
              style={{ width: 300 }}
            >
              <Input placeholder="标准发票Schema" />
            </Form.Item>
          </Space>
        </Form>

        <Divider />

        {parseError && (
          <Alert
            message={parseError}
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Tabs items={tabItems} />
      </Card>
    </div>
  );
}

export default SchemaEditPage;
