import { ReactNode } from 'react';
import { Alert, Button } from 'antd';
import { RocketOutlined } from '@ant-design/icons';
import Sidebar from './Sidebar';
import styles from './MainLayout.module.css';

interface MainLayoutProps {
  children: ReactNode;
  llmConfigured: boolean | null;
  showLlmPromo: boolean;
  onOpenLLMConfig: () => void;
  onCloseLLMPromo: () => void;
}

export default function MainLayout({
  children,
  llmConfigured,
  showLlmPromo,
  onOpenLLMConfig,
  onCloseLLMPromo,
}: MainLayoutProps) {
  return (
    <div className={styles.layoutContainer}>
      <Sidebar llmConfigured={llmConfigured} onOpenLLMConfig={onOpenLLMConfig} />

      <main className={styles.mainContent}>
        <div className={styles.contentWrapper}>
          {/* LLM Configuration Promo Banner */}
          {showLlmPromo && !llmConfigured && (
            <Alert
              className={styles.llmPromoAlert}
              message="提升发票识别准确率"
              description={
                <span>
                  当前使用免费OCR预处理服务。配置LLM服务后可获得更精准的发票信息提取和智能比对功能。
                  <Button
                    type="link"
                    icon={<RocketOutlined />}
                    onClick={onOpenLLMConfig}
                    style={{ padding: '0 4px' }}
                  >
                    立即配置
                  </Button>
                </span>
              }
              type="info"
              showIcon
              closable
              onClose={onCloseLLMPromo}
            />
          )}

          {children}
        </div>

        <footer className={styles.footer}>
          发票管理系统 ©2025 by Stometaverse.
        </footer>
      </main>
    </div>
  );
}
