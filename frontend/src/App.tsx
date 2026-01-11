import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Tooltip, Badge } from 'antd';
import type { MenuProps } from 'antd';
import {
  FileAddOutlined,
  UnorderedListOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import UploadPage from './pages/UploadPage';
import InvoiceListPage from './pages/InvoiceListPage';
import InvoiceDetailPage from './pages/InvoiceDetailPage';
import LLMConfigModal from './components/LLMConfigModal';
import SchemaListPage from './pages/SchemaListPage';
import SchemaEditPage from './pages/SchemaEditPage';
import ConfigListPage from './pages/ConfigListPage';
import ConfigEditPage from './pages/ConfigEditPage';
import FlowListPage from './pages/FlowListPage';
import FlowDetailPage from './pages/FlowDetailPage';
import FlowCreatePage from './pages/FlowCreatePage';
import FlowFeedbackPage from './pages/FlowFeedbackPage';
import { getLLMStatus } from './services/api';

const { Header, Content, Footer } = Layout;

function AppContent() {
  const location = useLocation();
  const [llmConfigOpen, setLlmConfigOpen] = useState(false);
  const [llmConfigured, setLlmConfigured] = useState<boolean | null>(null);

  // Check LLM status on app load
  useEffect(() => {
    const checkLLMStatus = async () => {
      try {
        const status = await getLLMStatus();
        setLlmConfigured(status.is_configured);
        // Auto-open modal if LLM is not configured
        if (!status.is_configured) {
          setLlmConfigOpen(true);
        }
      } catch (error) {
        console.error('Failed to check LLM status:', error);
        // If check fails, assume not configured and show modal
        setLlmConfigured(false);
        setLlmConfigOpen(true);
      }
    };
    checkLLMStatus();
  }, []);

  const handleLLMConfigured = () => {
    setLlmConfigured(true);
  };

  // Determine which menu key is selected based on current path
  const getSelectedKey = () => {
    const path = location.pathname;
    if (path.startsWith('/schemas')) return '/schemas';
    if (path.startsWith('/configs')) return '/configs';
    if (path.startsWith('/flows')) return '/flows';
    if (path.startsWith('/upload')) return '/upload';
    if (path.startsWith('/invoices')) return '/';
    return path;
  };

  const menuItems: MenuProps['items'] = [
    {
      key: '/',
      icon: <UnorderedListOutlined />,
      label: <Link to="/">发票列表</Link>,
    },
    {
      key: '/upload',
      icon: <FileAddOutlined />,
      label: <Link to="/upload">上传发票</Link>,
    },
    {
      type: 'divider',
    },
    {
      key: 'digitization',
      icon: <AppstoreOutlined />,
      label: '数字化平台',
      children: [
        {
          key: '/schemas',
          icon: <DatabaseOutlined />,
          label: <Link to="/schemas">Schema管理</Link>,
        },
        {
          key: '/configs',
          icon: <SettingOutlined />,
          label: <Link to="/configs">Config管理</Link>,
        },
        {
          key: '/flows',
          icon: <ThunderboltOutlined />,
          label: <Link to="/flows">数字化流程</Link>,
        },
      ],
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{ color: 'white', fontSize: '18px', fontWeight: 'bold', marginRight: '40px' }}>
          发票管理系统
        </div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[getSelectedKey()]}
          items={menuItems}
          style={{ flex: 1 }}
        />
        <Tooltip title={llmConfigured ? 'LLM服务已配置' : 'LLM服务未配置，点击配置'}>
          <Button
            type="text"
            icon={
              <Badge dot={!llmConfigured} status={llmConfigured ? 'success' : 'warning'}>
                {llmConfigured ? (
                  <CheckCircleOutlined style={{ color: '#52c41a', fontSize: '18px' }} />
                ) : (
                  <ExclamationCircleOutlined style={{ color: '#faad14', fontSize: '18px' }} />
                )}
              </Badge>
            }
            onClick={() => setLlmConfigOpen(true)}
            style={{ marginLeft: 8 }}
          />
        </Tooltip>
        <Tooltip title="LLM设置">
          <Button
            type="text"
            icon={<SettingOutlined style={{ color: 'rgba(255, 255, 255, 0.85)', fontSize: '18px' }} />}
            onClick={() => setLlmConfigOpen(true)}
          />
        </Tooltip>
      </Header>
      <Content style={{ padding: '24px', background: '#f0f2f5' }}>
        <Routes>
          {/* Invoice routes */}
          <Route path="/" element={<InvoiceListPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/invoices/:id" element={<InvoiceDetailPage />} />

          {/* Schema routes */}
          <Route path="/schemas" element={<SchemaListPage />} />
          <Route path="/schemas/:id" element={<SchemaEditPage />} />

          {/* Config routes */}
          <Route path="/configs" element={<ConfigListPage />} />
          <Route path="/configs/:id" element={<ConfigEditPage />} />

          {/* Flow routes */}
          <Route path="/flows" element={<FlowListPage />} />
          <Route path="/flows/new" element={<FlowCreatePage />} />
          <Route path="/flows/:id" element={<FlowDetailPage />} />
          <Route path="/flows/:id/feedback" element={<FlowFeedbackPage />} />
        </Routes>
      </Content>
      <Footer style={{ textAlign: 'center' }}>
        发票管理系统 ©2025 by Stometaverse.
      </Footer>

      <LLMConfigModal
        open={llmConfigOpen}
        onClose={() => setLlmConfigOpen(false)}
        onConfigured={handleLLMConfigured}
      />
    </Layout>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;
