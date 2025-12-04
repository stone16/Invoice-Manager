import { useState, useEffect, useCallback } from 'react';
import type { ColumnConfig } from '../components/ColumnSelector';

const STORAGE_KEY = 'invoice_list_column_settings';

interface ColumnSettings {
  visibility: Record<string, boolean>;
  widths: Record<string, number>;
}

const defaultColumnConfigs: ColumnConfig[] = [
  { key: 'invoice_number', title: '发票号码', visible: true },
  { key: 'issue_date', title: '开票日期', visible: true },
  { key: 'buyer_name', title: '购买方', visible: true },
  { key: 'buyer_tax_id', title: '购买方税号', visible: false },
  { key: 'seller_name', title: '销售方', visible: true },
  { key: 'seller_tax_id', title: '销售方税号', visible: false },
  { key: 'item_name', title: '项目名称', visible: true },
  { key: 'specification', title: '规格型号', visible: false },
  { key: 'unit', title: '单位', visible: false },
  { key: 'quantity', title: '数量', visible: false },
  { key: 'unit_price', title: '单价', visible: false },
  { key: 'amount', title: '金额(不含税)', visible: false },
  { key: 'tax_rate', title: '税率', visible: false },
  { key: 'tax_amount', title: '税额', visible: false },
  { key: 'total_with_tax', title: '价税合计', visible: true },
  { key: 'status', title: '状态', visible: true },
  { key: 'owner', title: '归属人', visible: true },
  { key: 'file_name', title: '文件名', visible: false },
  { key: 'created_at', title: '创建时间', visible: false },
  { key: 'updated_at', title: '更新时间', visible: false },
  { key: 'action', title: '操作', visible: true, fixed: true },
];

const defaultColumnWidths: Record<string, number> = {
  invoice_number: 150,
  issue_date: 120,
  buyer_name: 180,
  buyer_tax_id: 180,
  seller_name: 180,
  seller_tax_id: 180,
  item_name: 200,
  specification: 120,
  unit: 80,
  quantity: 100,
  unit_price: 100,
  amount: 120,
  tax_rate: 80,
  tax_amount: 120,
  total_with_tax: 120,
  status: 100,
  owner: 100,
  file_name: 150,
  created_at: 160,
  updated_at: 160,
  action: 120,
};

function loadSettings(): ColumnSettings | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (e) {
    console.error('Failed to load column settings:', e);
  }
  return null;
}

function saveSettings(settings: ColumnSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch (e) {
    console.error('Failed to save column settings:', e);
  }
}

export function useColumnSettings() {
  const [columnConfigs, setColumnConfigs] = useState<ColumnConfig[]>(() => {
    const stored = loadSettings();
    if (stored?.visibility) {
      return defaultColumnConfigs.map((col) => ({
        ...col,
        visible: stored.visibility[col.key] ?? col.visible,
      }));
    }
    return defaultColumnConfigs;
  });

  const [columnWidths, setColumnWidths] = useState<Record<string, number>>(() => {
    const stored = loadSettings();
    return { ...defaultColumnWidths, ...(stored?.widths || {}) };
  });

  // Save settings when they change
  useEffect(() => {
    const visibility: Record<string, boolean> = {};
    columnConfigs.forEach((col) => {
      visibility[col.key] = col.visible;
    });
    saveSettings({ visibility, widths: columnWidths });
  }, [columnConfigs, columnWidths]);

  const handleColumnResize = useCallback(
    (key: string) =>
      (_: React.SyntheticEvent, { size }: { size: { width: number } }) => {
        setColumnWidths((prev) => ({
          ...prev,
          [key]: size.width,
        }));
      },
    []
  );

  const visibleColumns = columnConfigs.filter((col) => col.visible);

  return {
    columnConfigs,
    setColumnConfigs,
    columnWidths,
    handleColumnResize,
    visibleColumns,
  };
}

export default useColumnSettings;
