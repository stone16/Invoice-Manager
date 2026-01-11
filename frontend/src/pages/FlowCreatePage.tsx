import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  Space,
  message,
  Typography,
  Select,
  Upload,
  Alert,
  Steps,
  Result,
} from 'antd';
import {
  ArrowLeftOutlined,
  InboxOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { listConfigs, uploadFlow } from '../services/api';
import type { DigiFlowConfig, DigiFlowWithResult } from '../types/digitization';

const { Text } = Typography;
const { Dragger } = Upload;

function FlowCreatePage() {
  const navigate = useNavigate();
  const [configs, setConfigs] = useState<DigiFlowConfig[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<number | null>(null);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [createdFlows, setCreatedFlows] = useState<DigiFlowWithResult[]>([]);

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      const response = await listConfigs({ page_size: 100, status: 1 }); // Active only
      setConfigs(response.items);
    } catch (error) {
      message.error('获取Config列表失败');
      console.error(error);
    }
  };

  const handleUpload = async () => {
    if (!selectedConfigId) {
      message.warning('请选择一个Config');
      return;
    }

    if (fileList.length === 0) {
      message.warning('请上传至少一个文件');
      return;
    }

    setUploading(true);
    try {
      const files = fileList.map(f => f.originFileObj as File);
      const flows = await uploadFlow(selectedConfigId, files);
      setCreatedFlows(flows);
      setCurrentStep(2);
      message.success(`成功创建 ${flows.length} 个Flow`);
    } catch (error) {
      message.error('上传失败');
      console.error(error);
    } finally {
      setUploading(false);
    }
  };

  const uploadProps = {
    multiple: true,
    fileList,
    beforeUpload: (file: File) => {
      setFileList(prev => [...prev, {
        uid: `${Date.now()}-${file.name}`,
        name: file.name,
        status: 'done',
        originFileObj: file,
      } as UploadFile]);
      return false; // Prevent auto upload
    },
    onRemove: (file: UploadFile) => {
      setFileList(prev => prev.filter(f => f.uid !== file.uid));
    },
  };

  const steps = [
    {
      title: '选择配置',
      description: '选择要使用的提取配置',
    },
    {
      title: '上传文件',
      description: '上传待处理的文档',
    },
    {
      title: '完成',
      description: '查看处理结果',
    },
  ];

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div style={{ maxWidth: 600, margin: '0 auto' }}>
            <Text strong>选择提取配置 (Config)</Text>
            <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              Config定义了如何提取和处理文档内容
            </Text>
            <Select
              style={{ width: '100%' }}
              size="large"
              placeholder="选择一个Config"
              value={selectedConfigId}
              onChange={setSelectedConfigId}
              options={configs.map(c => ({
                value: c.id,
                label: (
                  <Space>
                    <span>{c.name}</span>
                    <Text type="secondary">({c.slug})</Text>
                  </Space>
                ),
              }))}
            />
            {selectedConfigId && (
              <Alert
                message={`已选择: ${configs.find(c => c.id === selectedConfigId)?.name}`}
                type="success"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}
            <div style={{ marginTop: 24, textAlign: 'right' }}>
              <Button
                type="primary"
                disabled={!selectedConfigId}
                onClick={() => setCurrentStep(1)}
              >
                下一步
              </Button>
            </div>
          </div>
        );

      case 1:
        return (
          <div style={{ maxWidth: 600, margin: '0 auto' }}>
            <Text strong>上传文档</Text>
            <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              支持 PDF、图片、Excel 等格式
            </Text>
            <Dragger {...uploadProps}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持单个或批量上传，文件将使用选定的Config进行处理
              </p>
            </Dragger>
            <div style={{ marginTop: 24, display: 'flex', justifyContent: 'space-between' }}>
              <Button onClick={() => setCurrentStep(0)}>
                上一步
              </Button>
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                disabled={fileList.length === 0}
                loading={uploading}
                onClick={handleUpload}
              >
                开始处理 ({fileList.length} 个文件)
              </Button>
            </div>
          </div>
        );

      case 2:
        return (
          <Result
            status="success"
            icon={<CheckCircleOutlined />}
            title="处理完成！"
            subTitle={`成功创建 ${createdFlows.length} 个数字化流程`}
            extra={[
              <Button
                type="primary"
                key="list"
                onClick={() => navigate('/flows')}
              >
                查看列表
              </Button>,
              <Button
                key="detail"
                onClick={() => {
                  if (createdFlows.length > 0) {
                    navigate(`/flows/${createdFlows[0].id}`);
                  }
                }}
              >
                查看第一个Flow详情
              </Button>,
              <Button
                key="new"
                onClick={() => {
                  setCurrentStep(0);
                  setFileList([]);
                  setCreatedFlows([]);
                }}
              >
                继续上传
              </Button>,
            ]}
          >
            {createdFlows.length > 0 && (
              <div style={{ textAlign: 'left', marginTop: 16 }}>
                <Text strong>已创建的Flow：</Text>
                <ul>
                  {createdFlows.map(flow => (
                    <li key={flow.id}>
                      <a onClick={() => navigate(`/flows/${flow.id}`)}>
                        Flow #{flow.id} - {flow.content_context?.file_name}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Result>
        );

      default:
        return null;
    }
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/flows')}>
          返回列表
        </Button>
      </div>

      <Card
        title={
          <Space>
            <ThunderboltOutlined />
            <span>新建数字化流程</span>
          </Space>
        }
      >
        <Steps
          current={currentStep}
          items={steps}
          style={{ marginBottom: 32 }}
        />
        {renderStepContent()}
      </Card>
    </div>
  );
}

export default FlowCreatePage;
