import { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Select,
  Input,
  Button,
  Space,
  message,
  Alert,
  Spin,
  Tag,
  Divider,
  Tooltip,
} from 'antd';
import {
  SettingOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ApiOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { getLLMStatus, configureLLM, testLLMConnection, getAvailableModels } from '../services/api';
import type { LLMStatusResponse, LLMProviderInfo, ModelInfo } from '../types/invoice';

interface LLMConfigModalProps {
  open: boolean;
  onClose: () => void;
  onConfigured?: () => void;
}

// Fallback models for each provider (used when API fails)
const FALLBACK_MODELS: Record<string, ModelInfo[]> = {
  openai: [
    { id: 'gpt-4o', name: 'GPT-4o', vision: true },
    { id: 'gpt-4o-mini', name: 'GPT-4o Mini', vision: true },
    { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', vision: true },
  ],
  anthropic: [
    { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4', vision: true },
    { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', vision: true },
    { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', vision: true },
  ],
  google: [
    { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', vision: true },
    { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', vision: true },
    { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash', vision: true },
  ],
  qwen: [
    { id: 'qwen2.5-vl-72b-instruct', name: 'Qwen 2.5 VL 72B', vision: true },
    { id: 'qwen-turbo', name: 'Qwen Turbo', vision: false },
  ],
  deepseek: [
    { id: 'deepseek-chat', name: 'DeepSeek Chat', vision: false },
  ],
  zhipu: [
    { id: 'glm-4v', name: 'GLM-4V', vision: true },
    { id: 'glm-4-flash', name: 'GLM-4 Flash', vision: false },
  ],
};

// Providers that support custom base URL
const SUPPORTS_BASE_URL = ['openai', 'qwen', 'deepseek'];

function LLMConfigModal({ open, onClose, onConfigured }: LLMConfigModalProps) {
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [configuring, setConfiguring] = useState(false);
  const [status, setStatus] = useState<LLMStatusResponse | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsSource, setModelsSource] = useState<'openrouter' | 'fallback'>('fallback');
  const [form] = Form.useForm();

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const data = await getLLMStatus();
      setStatus(data);
      if (data.active_provider) {
        setSelectedProvider(data.active_provider);
        // Fetch models for the active provider
        await fetchModels(data.active_provider);
      }
    } catch (error) {
      console.error('Failed to fetch LLM status:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchModels = async (provider: string) => {
    setModelsLoading(true);
    try {
      const response = await getAvailableModels(provider, false);
      if (response.models && response.models.length > 0) {
        setModels(response.models);
        setModelsSource(response.source);
      } else {
        // Fall back to hardcoded models
        setModels(FALLBACK_MODELS[provider] || []);
        setModelsSource('fallback');
      }
    } catch (error) {
      console.error('Failed to fetch models:', error);
      // Fall back to hardcoded models
      setModels(FALLBACK_MODELS[provider] || []);
      setModelsSource('fallback');
    } finally {
      setModelsLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchStatus();
      form.resetFields();
    }
  }, [open]);

  const handleProviderChange = async (provider: string) => {
    setSelectedProvider(provider);
    // Fetch models for the new provider
    await fetchModels(provider);
    // Set default model from fetched list
    const providerModels = FALLBACK_MODELS[provider] || [];
    form.setFieldsValue({
      provider,
      model: providerModels[0]?.id || '',
      api_key: '',
      base_url: '',
    });
  };

  // Update form model when models are fetched
  useEffect(() => {
    if (models.length > 0 && selectedProvider) {
      const currentModel = form.getFieldValue('model');
      // If current model not in list, set to first available
      if (!currentModel || !models.find(m => m.id === currentModel)) {
        form.setFieldsValue({ model: models[0].id });
      }
    }
  }, [models, selectedProvider]);

  const handleConfigure = async () => {
    try {
      const values = await form.validateFields();
      setConfiguring(true);

      const config = {
        provider: values.provider,
        api_key: values.api_key,
        model: values.model || undefined,
        base_url: values.base_url || undefined,
      };

      const result = await configureLLM(config);
      if (result.success) {
        message.success(result.message);
        await fetchStatus();
        onConfigured?.();
      }
    } catch (error: unknown) {
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { data?: { detail?: string } } };
        if (axiosError.response?.data?.detail) {
          message.error(axiosError.response.data.detail);
          return;
        }
      }
      if (error && typeof error === 'object' && 'errorFields' in error) {
        // Form validation error, ignore
        return;
      }
      message.error('配置失败');
    } finally {
      setConfiguring(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      const result = await testLLMConnection();
      if (result.success) {
        message.success(`${result.provider_display} 连接测试成功`);
      }
    } catch (error: unknown) {
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { data?: { detail?: string } } };
        if (axiosError.response?.data?.detail) {
          message.error(axiosError.response.data.detail);
          return;
        }
      }
      message.error('连接测试失败');
    } finally {
      setTesting(false);
    }
  };

  const renderProviderStatus = (provider: LLMProviderInfo) => {
    const isActive = status?.active_provider === provider.name;
    return (
      <div key={provider.name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span>{provider.display_name}</span>
        {provider.is_configured && (
          <Tag color="success" icon={<CheckCircleOutlined />}>
            已配置
          </Tag>
        )}
        {isActive && (
          <Tag color="blue">当前使用</Tag>
        )}
        {provider.model && provider.is_configured && (
          <Tag>{provider.model}</Tag>
        )}
      </div>
    );
  };

  return (
    <Modal
      title={
        <Space>
          <SettingOutlined />
          <span>LLM 服务配置</span>
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={600}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
        </div>
      ) : (
        <>
          {/* Current Status */}
          {status?.is_configured ? (
            <Alert
              message={
                <Space>
                  <CheckCircleOutlined />
                  <span>当前使用: {status.active_provider_display}</span>
                </Space>
              }
              type="success"
              showIcon={false}
              style={{ marginBottom: 16 }}
              action={
                <Button size="small" onClick={handleTest} loading={testing}>
                  测试连接
                </Button>
              }
            />
          ) : (
            <Alert
              message="未配置LLM服务"
              description="LLM 为可选增强功能，可提升发票识别准确率与比对能力。不配置也可使用 OCR-only 流程。"
              type="warning"
              showIcon
              icon={<ExclamationCircleOutlined />}
              style={{ marginBottom: 16 }}
            />
          )}

          {/* Provider List */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 500, marginBottom: 8 }}>可用的LLM提供商:</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {status?.available_providers.map(renderProviderStatus)}
            </div>
          </div>

          <Divider />

          {/* Configuration Form */}
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              provider: selectedProvider || 'openai',
              model: FALLBACK_MODELS[selectedProvider || 'openai']?.[0]?.id || '',
            }}
          >
            <Form.Item
              name="provider"
              label="选择LLM提供商"
              rules={[{ required: true, message: '请选择LLM提供商' }]}
            >
              <Select
                placeholder="选择LLM提供商"
                onChange={handleProviderChange}
                options={status?.available_providers.map((p) => ({
                  label: p.display_name,
                  value: p.name,
                }))}
              />
            </Form.Item>

            <Form.Item
              name="api_key"
              label="API 密钥"
              rules={[{ required: true, message: '请输入API密钥' }]}
            >
              <Input.Password
                placeholder="输入API密钥"
                prefix={<ApiOutlined />}
              />
            </Form.Item>

            <Form.Item
              name="model"
              label={
                <Space>
                  <span>模型</span>
                  {modelsSource === 'openrouter' && (
                    <Tag color="blue" style={{ fontSize: 10 }}>来自 OpenRouter</Tag>
                  )}
                </Space>
              }
            >
              <Select
                placeholder="选择模型"
                allowClear
                loading={modelsLoading}
                options={models.map((m) => ({
                  label: (
                    <Space>
                      <span>{m.name || m.id}</span>
                      {m.vision && (
                        <Tooltip title="支持图像识别">
                          <EyeOutlined style={{ color: '#1890ff' }} />
                        </Tooltip>
                      )}
                    </Space>
                  ),
                  value: m.id,
                }))}
              />
            </Form.Item>

            {SUPPORTS_BASE_URL.includes(selectedProvider) && (
              <Form.Item
                name="base_url"
                label="自定义 API 地址 (可选)"
                tooltip="用于兼容OpenAI接口的其他服务"
              >
                <Input placeholder="例如: https://api.example.com/v1" />
              </Form.Item>
            )}

            <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
              <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                <Button onClick={onClose}>取消</Button>
                <Button
                  type="primary"
                  onClick={handleConfigure}
                  loading={configuring}
                >
                  保存配置
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </>
      )}
    </Modal>
  );
}

export default LLMConfigModal;
