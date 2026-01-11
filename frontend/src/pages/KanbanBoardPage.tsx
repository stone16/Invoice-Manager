import React, { useState, useEffect } from 'react';
import { Card, Select, Space, Button, Spin, message, Input, Upload } from 'antd';
import { ReloadOutlined, UploadOutlined } from '@ant-design/icons';
import { KanbanBoard } from '../components/kanban/KanbanBoard';
import {
  UnifiedDocument,
  flowToUnifiedDocument,
  KanbanStatus,
  mapKanbanToFlowStatus,
} from '../types/kanban';
import { DigiFlowConfig } from '../types/digitization';
import { listFlows, listConfigs, uploadFlow } from '../services/api';
import type { UploadFile } from 'antd/es/upload/interface';

const { Option } = Select;
const { Search } = Input;

/**
 * KanbanBoardPage - Main page for document kanban view
 * Features: filter by config, search, upload, refresh
 */
const KanbanBoardPage: React.FC = () => {
  const [documents, setDocuments] = useState<UnifiedDocument[]>([]);
  const [configs, setConfigs] = useState<DigiFlowConfig[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<number | undefined>();
  const [searchText, setSearchText] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Load configs on mount
  useEffect(() => {
    loadConfigs();
  }, []);

  // Load documents when config changes
  useEffect(() => {
    loadDocuments();
  }, [selectedConfigId]);

  const loadConfigs = async () => {
    try {
      const response = await listConfigs({ page_size: 100, status: 1 });
      setConfigs(response.items);
    } catch (error) {
      console.error('Failed to load configs:', error);
      message.error('加载文档类型失败');
    }
  };

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const response = await listFlows({
        limit: 100,
        offset: 0,
        config_id: selectedConfigId,
      });

      // Convert flows to unified documents
      const docs = response.items.map((flow) => {
        const config = configs.find((c) => c.id === flow.config_id);
        return flowToUnifiedDocument(flow, config);
      });

      setDocuments(docs);
    } catch (error) {
      console.error('Failed to load documents:', error);
      message.error('加载文档失败');
    } finally {
      setLoading(false);
    }
  };

  const handleConfigChange = (value: number | undefined) => {
    setSelectedConfigId(value);
  };

  const handleSearch = (value: string) => {
    setSearchText(value);
  };

  const handleRefresh = () => {
    loadDocuments();
  };

  const handleStatusChange = async (docId: number, newStatus: KanbanStatus) => {
    // Map kanban status to flow status
    const flowStatus = mapKanbanToFlowStatus(newStatus);

    if (flowStatus === null) {
      throw new Error('Invalid status transition');
    }

    // TODO: Implement actual status update API
    // For now, just update locally
    setDocuments((prev) =>
      prev.map((doc) =>
        doc.id === docId
          ? { ...doc, status: newStatus, originalStatus: flowStatus }
          : doc
      )
    );
  };

  const handleDocumentEdit = (doc: UnifiedDocument) => {
    // Navigate to flow detail page for editing
    window.location.href = `/flows/${doc.id}`;
  };

  const handleUpload = async (file: UploadFile) => {
    if (!selectedConfigId) {
      message.warning('请先选择文档类型');
      return false;
    }

    setUploading(true);
    try {
      await uploadFlow(selectedConfigId, [file as unknown as File]);
      message.success('上传成功');
      loadDocuments();
    } catch (error) {
      console.error('Upload failed:', error);
      message.error('上传失败');
    } finally {
      setUploading(false);
    }

    return false; // Prevent default upload behavior
  };

  // Filter documents by search text
  const filteredDocuments = documents.filter((doc) => {
    if (!searchText) return true;
    const lowerSearch = searchText.toLowerCase();
    return (
      doc.title.toLowerCase().includes(lowerSearch) ||
      doc.subtitle?.toLowerCase().includes(lowerSearch) ||
      doc.preview?.toLowerCase().includes(lowerSearch)
    );
  });

  return (
    <Card
      title="文档看板"
      extra={
        <Space>
          <Select
            placeholder="选择文档类型"
            style={{ width: 180 }}
            allowClear
            value={selectedConfigId}
            onChange={handleConfigChange}
          >
            {configs.map((config) => (
              <Option key={config.id} value={config.id}>
                {config.name}
              </Option>
            ))}
          </Select>

          <Search
            placeholder="搜索文档..."
            onSearch={handleSearch}
            style={{ width: 200 }}
            allowClear
          />

          <Upload
            accept=".pdf,.xlsx,.xls,.png,.jpg,.jpeg"
            showUploadList={false}
            beforeUpload={handleUpload}
            disabled={!selectedConfigId || uploading}
          >
            <Button
              icon={<UploadOutlined />}
              loading={uploading}
              disabled={!selectedConfigId}
            >
              上传
            </Button>
          </Upload>

          <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
            刷新
          </Button>
        </Space>
      }
      bodyStyle={{ padding: '0 16px 16px' }}
    >
      <Spin spinning={loading}>
        <KanbanBoard
          documents={filteredDocuments}
          onStatusChange={handleStatusChange}
          onDocumentEdit={handleDocumentEdit}
          isLoading={loading}
        />
      </Spin>
    </Card>
  );
};

export default KanbanBoardPage;
