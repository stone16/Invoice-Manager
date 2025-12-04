import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Tooltip, Badge } from 'antd';
import {
  FileAddOutlined,
  UnorderedListOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import UploadPage from './pages/UploadPage';
import InvoiceListPage from './pages/InvoiceListPage';
import InvoiceDetailPage from './pages/InvoiceDetailPage';
import LLMConfigModal from './components/LLMConfigModal';
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

  const menuItems = [
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
          selectedKeys={[location.pathname]}
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
          <Route path="/" element={<InvoiceListPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
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
