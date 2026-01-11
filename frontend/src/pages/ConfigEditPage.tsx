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
  Select,
  Switch,
  InputNumber,
  Divider,
  Tag,
  Collapse,
} from 'antd';
import {
  ArrowLeftOutlined,
  SaveOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import { getConfig, createConfig, updateConfig, listSchemas } from '../services/api';
import type {
  DigiFlowConfig,
  DigiFlowConfigCreate,
  DigiFlowConfigUpdate,
  DigiFlowSchema,
  WorkflowConfig,
  PromptConfig,
} from '../types/digitization';
import { SourceContentType, SourceContentTypeLabels } from '../types/digitization';

const { Title, Text } = Typography;
const { TextArea } = Input;

function ConfigEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isNew = id === 'new';

  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState<DigiFlowConfig | null>(null);
  const [schemas, setSchemas] = useState<DigiFlowSchema[]>([]);
  const [form] = Form.useForm();

  // Workflow config state
  const [workflowConfig, setWorkflowConfig] = useState<WorkflowConfig>({
    rag_enabled: true,
    rag_top_k: 3,
    rag_threshold: 0.3,
    model: 'gpt-4o',
    temperature: 0,
    max_tokens: 4096,
  });

  // Prompt config state
  const [promptConfig, setPromptConfig] = useState<PromptConfig>({
    task_description: '',
    custom_instructions: '',
  });

  useEffect(() => {
    fetchSchemas();
    if (!isNew && id) {
      fetchConfig(parseInt(id));
    }
  }, [id, isNew]);

  const fetchSchemas = async () => {
    try {
      const response = await listSchemas();
      setSchemas(response.items);
    } catch (error) {
      console.error('获取Schema列表失败', error);
    }
  };

  const fetchConfig = async (configId: number) => {
    setLoading(true);
    try {
      const data = await getConfig(configId);
      setConfig(data);
      form.setFieldsValue({
        slug: data.slug,
        name: data.name,
        description: data.description,
        domain: data.domain,
        schema_id: data.schema_id,
        source_content_type: data.source_content_type,
      });
      if (data.workflow_config) {
        setWorkflowConfig(data.workflow_config);
      }
      if (data.prompt_config) {
        setPromptConfig(data.prompt_config);
      }
    } catch (error) {
      message.error('获取Config失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      const selectedSchema = schemas.find(s => s.id === values.schema_id);
      if (!selectedSchema && isNew) {
        message.error('请选择关联的Schema');
        return;
      }

      if (isNew) {
        const createData: DigiFlowConfigCreate = {
          slug: values.slug,
          name: values.name,
          description: values.description,
          domain: values.domain,
          schema_id: values.schema_id,
          schema_version: selectedSchema!.version,
          source_content_type: values.source_content_type,
          workflow_config: workflowConfig,
          prompt_config: promptConfig,
        };
        await createConfig(createData);
        message.success('Config创建成功');
      } else if (id) {
        const updateData: DigiFlowConfigUpdate = {
          name: values.name,
          description: values.description,
          domain: values.domain,
          workflow_config: workflowConfig,
          prompt_config: promptConfig,
        };
        await updateConfig(parseInt(id), updateData);
        message.success('Config更新成功');
      }

      navigate('/configs');
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
      key: 'workflow',
      label: (
        <span>
          <ThunderboltOutlined />
          工作流配置
        </span>
      ),
      children: (
        <div>
          <Collapse
            defaultActiveKey={['rag', 'model']}
            items={[
              {
                key: 'rag',
                label: 'RAG配置',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                      <Text>启用RAG:</Text>
                      <Switch
                        checked={workflowConfig.rag_enabled}
                        onChange={(checked) => setWorkflowConfig({ ...workflowConfig, rag_enabled: checked })}
                      />
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                      <Text>Top-K:</Text>
                      <InputNumber
                        min={1}
                        max={10}
                        value={workflowConfig.rag_top_k}
                        onChange={(value) => setWorkflowConfig({ ...workflowConfig, rag_top_k: value || 3 })}
                      />
                      <Text type="secondary">检索最相似的K个示例</Text>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                      <Text>相似度阈值:</Text>
                      <InputNumber
                        min={0}
                        max={1}
                        step={0.1}
                        value={workflowConfig.rag_threshold}
                        onChange={(value) => setWorkflowConfig({ ...workflowConfig, rag_threshold: value || 0.3 })}
                      />
                      <Text type="secondary">最小相似度分数</Text>
                    </div>
                  </Space>
                ),
              },
              {
                key: 'model',
                label: '模型配置',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                      <Text>模型:</Text>
                      <Select
                        style={{ width: 200 }}
                        value={workflowConfig.model}
                        onChange={(value) => setWorkflowConfig({ ...workflowConfig, model: value })}
                        options={[
                          { value: 'gpt-4o', label: 'GPT-4o' },
                          { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
                          { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
                          { value: 'claude-3-5-sonnet-latest', label: 'Claude 3.5 Sonnet' },
                        ]}
                      />
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                      <Text>Temperature:</Text>
                      <InputNumber
                        min={0}
                        max={2}
                        step={0.1}
                        value={workflowConfig.temperature}
                        onChange={(value) => setWorkflowConfig({ ...workflowConfig, temperature: value || 0 })}
                      />
                      <Text type="secondary">较低值产生更确定的输出</Text>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                      <Text>最大Token数:</Text>
                      <InputNumber
                        min={256}
                        max={128000}
                        step={256}
                        value={workflowConfig.max_tokens}
                        onChange={(value) => setWorkflowConfig({ ...workflowConfig, max_tokens: value || 4096 })}
                      />
                    </div>
                  </Space>
                ),
              },
            ]}
          />
        </div>
      ),
    },
    {
      key: 'prompt',
      label: (
        <span>
          <MessageOutlined />
          提示词配置
        </span>
      ),
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Text strong>任务描述</Text>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
              描述此配置的主要目的和提取任务
            </Text>
            <TextArea
              value={promptConfig.task_description}
              onChange={(e) => setPromptConfig({ ...promptConfig, task_description: e.target.value })}
              placeholder="例如：从发票中提取关键信息，包括发票号码、日期、金额等字段"
              autoSize={{ minRows: 3, maxRows: 6 }}
            />
          </div>
          <div>
            <Text strong>自定义指令</Text>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
              添加特定领域的指令和约束
            </Text>
            <TextArea
              value={promptConfig.custom_instructions}
              onChange={(e) => setPromptConfig({ ...promptConfig, custom_instructions: e.target.value })}
              placeholder={`例如：
- 金额必须保留两位小数
- 日期格式统一为 YYYY-MM-DD
- 如果无法识别某字段，请返回 null 而不是猜测`}
              autoSize={{ minRows: 6, maxRows: 12 }}
            />
          </div>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/configs')}
          >
            返回列表
          </Button>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <Title level={4} style={{ margin: 0 }}>
            <SettingOutlined style={{ marginRight: 8 }} />
            {isNew ? '新建Config' : `编辑Config: ${config?.name}`}
            {config && (
              <Tag color="purple" style={{ marginLeft: 8 }}>v{config.version}</Tag>
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
          <div style={{ display: 'flex', gap: 24 }}>
            <Form.Item
              name="slug"
              label="Slug (标识符)"
              rules={[
                { required: true, message: '请输入Slug' },
                { pattern: /^[a-z0-9_-]+$/, message: 'Slug只能包含小写字母、数字、下划线和连字符' },
              ]}
              style={{ width: 200 }}
            >
              <Input placeholder="invoice_standard" disabled={!isNew} />
            </Form.Item>
            <Form.Item
              name="name"
              label="名称"
              rules={[{ required: true, message: '请输入名称' }]}
              style={{ width: 250 }}
            >
              <Input placeholder="标准发票提取配置" />
            </Form.Item>
            <Form.Item
              name="domain"
              label="领域"
              style={{ width: 150 }}
            >
              <Input placeholder="finance" />
            </Form.Item>
          </div>

          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea placeholder="配置描述..." autoSize={{ minRows: 2, maxRows: 4 }} />
          </Form.Item>

          <div style={{ display: 'flex', gap: 24 }}>
            <Form.Item
              name="schema_id"
              label="关联Schema"
              rules={[{ required: true, message: '请选择Schema' }]}
              style={{ width: 300 }}
            >
              <Select
                placeholder="选择Schema"
                disabled={!isNew}
                options={schemas.map(s => ({
                  value: s.id,
                  label: `${s.name} (v${s.version})`,
                }))}
              />
            </Form.Item>
            <Form.Item
              name="source_content_type"
              label="输入内容类型"
              rules={[{ required: true, message: '请选择输入类型' }]}
              style={{ width: 150 }}
            >
              <Select
                placeholder="选择类型"
                disabled={!isNew}
                options={[
                  { value: SourceContentType.FILE, label: SourceContentTypeLabels[SourceContentType.FILE] },
                  { value: SourceContentType.TEXT, label: SourceContentTypeLabels[SourceContentType.TEXT] },
                ]}
              />
            </Form.Item>
          </div>
        </Form>

        <Divider />

        <Tabs items={tabItems} />
      </Card>
    </div>
  );
}

export default ConfigEditPage;
