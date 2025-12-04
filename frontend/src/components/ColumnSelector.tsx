import { useState } from 'react';
import { Button, Checkbox, Popover, Space, Divider } from 'antd';
import { SettingOutlined } from '@ant-design/icons';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';

export interface ColumnConfig {
  key: string;
  title: string;
  visible: boolean;
  fixed?: boolean; // If true, cannot be hidden
}

interface ColumnSelectorProps {
  columns: ColumnConfig[];
  onChange: (columns: ColumnConfig[]) => void;
}

function ColumnSelector({ columns, onChange }: ColumnSelectorProps) {
  const [open, setOpen] = useState(false);

  const handleChange = (key: string, e: CheckboxChangeEvent) => {
    const newColumns = columns.map((col) =>
      col.key === key ? { ...col, visible: e.target.checked } : col
    );
    onChange(newColumns);
  };

  const handleSelectAll = () => {
    const newColumns = columns.map((col) => ({ ...col, visible: true }));
    onChange(newColumns);
  };

  const handleReset = () => {
    // Reset to default visible columns (those that are fixed or in the default set)
    const defaultVisible = [
      'invoice_number',
      'issue_date',
      'buyer_name',
      'seller_name',
      'item_name',
      'total_with_tax',
      'status',
      'owner',
      'action',
    ];
    const newColumns = columns.map((col) => ({
      ...col,
      visible: col.fixed || defaultVisible.includes(col.key),
    }));
    onChange(newColumns);
  };

  const content = (
    <div style={{ width: 200 }}>
      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
        <Button size="small" type="link" onClick={handleSelectAll}>
          全选
        </Button>
        <Button size="small" type="link" onClick={handleReset}>
          重置
        </Button>
      </div>
      <Divider style={{ margin: '8px 0' }} />
      <Space direction="vertical" style={{ width: '100%' }}>
        {columns
          .filter((col) => col.key !== 'action')
          .map((col) => (
            <Checkbox
              key={col.key}
              checked={col.visible}
              disabled={col.fixed}
              onChange={(e) => handleChange(col.key, e)}
            >
              {col.title}
            </Checkbox>
          ))}
      </Space>
    </div>
  );

  return (
    <Popover
      content={content}
      title="选择显示列"
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      placement="bottomRight"
    >
      <Button icon={<SettingOutlined />}>列设置</Button>
    </Popover>
  );
}

export default ColumnSelector;
