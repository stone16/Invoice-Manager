import React from 'react';
import { Input, Select, DatePicker } from 'antd';
import type { RangePickerProps } from 'antd/es/date-picker';
import styles from './ControlBar.module.css';

const { RangePicker } = DatePicker;

interface ControlBarProps {
  searchPlaceholder?: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  statusFilter?: string;
  onStatusChange?: (value: string | undefined) => void;
  statusOptions?: Array<{ label: string; value: string }>;
  dateRange?: [any, any] | null;
  onDateRangeChange?: RangePickerProps['onChange'];
  totalText?: string;
}

const ControlBar: React.FC<ControlBarProps> = ({
  searchPlaceholder = '搜索...',
  searchValue,
  onSearchChange,
  statusFilter,
  onStatusChange,
  statusOptions = [],
  dateRange,
  onDateRangeChange,
  totalText = '',
}) => {
  return (
    <div className={styles.controlBar}>
      <div className={styles.leftSection}>
        <Input
          placeholder={searchPlaceholder}
          value={searchValue}
          onChange={(e) => onSearchChange?.(e.target.value)}
          className={styles.searchInput}
          allowClear
        />
        <Select
          placeholder="全部状态"
          value={statusFilter}
          onChange={onStatusChange}
          options={statusOptions}
          allowClear
          className={styles.statusFilter}
        />
        <RangePicker
          value={dateRange}
          onChange={onDateRangeChange}
          className={styles.dateRange}
        />
      </div>
      <div className={styles.rightSection}>
        {totalText && <span className={styles.totalText}>{totalText}</span>}
      </div>
    </div>
  );
};

export default ControlBar;
