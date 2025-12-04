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
} from 'antd';
import {
  SettingOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { getLLMStatus, configureLLM, testLLMConnection } from '../services/api';
import type { LLMStatusResponse, LLMProviderInfo } from '../types/invoice';

interface LLMConfigModalProps {
  open: boolean;
  onClose: () => void;
  onConfigured?: () => void;
}

// Default models for each provider
const DEFAULT_MODELS: Record<string, string[]> = {
  openai: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  anthropic: ['claude-3-haiku-20240307', 'claude-3-sonnet-20240229', 'claude-3-opus-20240229', 'claude-3-5-sonnet-20241022'],
  google: ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro'],
  qwen: ['qwen-turbo', 'qwen-plus', 'qwen-max'],
  deepseek: ['deepseek-chat', 'deepseek-coder'],
  zhipu: ['glm-4-flash', 'glm-4', 'glm-4-plus'],
};

// Providers that support custom base URL
const SUPPORTS_BASE_URL = ['openai', 'qwen', 'deepseek'];

function LLMConfigModal({ open, onClose, onConfigured }: LLMConfigModalProps) {
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [configuring, setConfiguring] = useState(false);
  const [status, setStatus] = useState<LLMStatusResponse | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [form] = Form.useForm();

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const data = await getLLMStatus();
      setStatus(data);
      if (data.active_provider) {
        setSelectedProvider(data.active_provider);
      }
    } catch (error) {
      console.error('Failed to fetch LLM status:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchStatus();
      form.resetFields();
    }
  }, [open]);

  const handleProviderChange = (provider: string) => {
    setSelectedProvider(provider);
    form.setFieldsValue({
      provider,
      model: DEFAULT_MODELS[provider]?.[0] || '',
      api_key: '',
      base_url: '',
    });
  };

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
              description="发票确认功能需要配置LLM服务来进行OCR结果比对。请选择一个LLM提供商并配置API密钥。"
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
              model: DEFAULT_MODELS[selectedProvider || 'openai']?.[0] || '',
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
              label="模型"
            >
              <Select
                placeholder="选择模型"
                allowClear
                options={DEFAULT_MODELS[selectedProvider || 'openai']?.map((m) => ({
                  label: m,
                  value: m,
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
