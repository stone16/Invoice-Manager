import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Upload, Button, message, List, Tag, Typography } from 'antd';
import { InboxOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { uploadInvoices } from '../services/api';
import type { UploadResponse } from '../types/invoice';

const { Dragger } = Upload;
const { Title } = Typography;

function UploadPage() {
  const navigate = useNavigate();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState<UploadResponse[]>([]);

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请先选择文件');
      return;
    }

    setUploading(true);
    try {
      const files = fileList.map((f) => f.originFileObj as File);
      const response = await uploadInvoices(files);
      setResults(response);

      const successCount = response.filter((r) => r.status === 'success').length;
      if (successCount > 0) {
        message.success(`成功上传 ${successCount} 个文件`);
        setFileList([]);
      }

      const failCount = response.filter((r) => r.status === 'error').length;
      if (failCount > 0) {
        message.error(`${failCount} 个文件上传失败`);
      }
    } catch (error) {
      message.error('上传失败，请重试');
      console.error(error);
    } finally {
      setUploading(false);
    }
  };

  const uploadProps = {
    multiple: true,
    accept: '.pdf,.jpg,.jpeg,.png',
    fileList,
    beforeUpload: (file: File) => {
      const isValid = ['application/pdf', 'image/jpeg', 'image/png'].includes(file.type);
      if (!isValid) {
        message.error('只支持 PDF、JPG、PNG 格式');
        return Upload.LIST_IGNORE;
      }

      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        message.error('文件大小不能超过 10MB');
        return Upload.LIST_IGNORE;
      }

      return false; // Prevent auto upload
    },
    onChange: ({ fileList: newFileList }: { fileList: UploadFile[] }) => {
      setFileList(newFileList);
    },
    onRemove: (file: UploadFile) => {
      setFileList(fileList.filter((f) => f.uid !== file.uid));
    },
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Card>
        <Title level={4}>上传发票</Title>

        <Dragger {...uploadProps} style={{ marginBottom: 24 }}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">
            支持 PDF、JPG、PNG 格式，单个文件最大 10MB，支持批量上传
          </p>
        </Dragger>

        <div style={{ display: 'flex', gap: 16 }}>
          <Button
            type="primary"
            onClick={handleUpload}
            loading={uploading}
            disabled={fileList.length === 0}
          >
            {uploading ? '上传中...' : '开始上传'}
          </Button>
          <Button onClick={() => navigate('/')}>
            返回列表
          </Button>
        </div>
      </Card>

      {results.length > 0 && (
        <Card title="上传结果" style={{ marginTop: 24 }}>
          <List
            dataSource={results}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  avatar={
                    item.status === 'success' ? (
                      <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />
                    ) : (
                      <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />
                    )
                  }
                  title={item.file_name}
                  description={item.message}
                />
                {item.status === 'success' && (
                  <Tag color="success">ID: {item.id}</Tag>
                )}
              </List.Item>
            )}
          />
          <Button
            type="primary"
            onClick={() => navigate('/')}
            style={{ marginTop: 16 }}
          >
            查看发票列表
          </Button>
        </Card>
      )}
    </div>
  );
}

export default UploadPage;
