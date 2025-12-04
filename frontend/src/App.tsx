import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  FileAddOutlined,
  UnorderedListOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import UploadPage from './pages/UploadPage';
import InvoiceListPage from './pages/InvoiceListPage';
import InvoiceDetailPage from './pages/InvoiceDetailPage';

const { Header, Content, Footer } = Layout;

function AppContent() {
  const location = useLocation();

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
      </Header>
      <Content style={{ padding: '24px', background: '#f0f2f5' }}>
        <Routes>
          <Route path="/" element={<InvoiceListPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
        </Routes>
      </Content>
      <Footer style={{ textAlign: 'center' }}>
        发票管理系统 ©2024
      </Footer>
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
