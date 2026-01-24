import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Select,
  Input,
  message,
  Popconfirm,
  Modal,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  EyeOutlined,
  DeleteOutlined,
  UploadOutlined,
  ReloadOutlined,
  DownloadOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { listInvoices, deleteInvoice, batchUpdateInvoices, batchDeleteInvoices, batchReprocessInvoices, getStatistics } from '../services/api';
import type { Invoice, Statistics } from '../types/invoice';
import { InvoiceStatus } from '../types/invoice';
import ResizableTitle from '../components/ResizableTitle';
import ColumnSelector from '../components/ColumnSelector';
import { useColumnSettings } from '../hooks/useColumnSettings';
import { useInvoiceStatistics } from '../hooks/useInvoiceStatistics';
import MetricCard from '../components/dashboard/MetricCard';
import ControlBar from '../components/dashboard/ControlBar';
import styles from './InvoiceListPage.module.css';
import 'react-resizable/css/styles.css';

const statusColors: Record<string, string> = {
  '已上传': 'default',
  '解析中': 'processing',
  '待处理': 'blue',
  '待审核': 'warning',
  '已确认': 'success',
  '已报销': 'green',
  '未报销': 'orange',
};

function InvoiceListPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [selectedRowKeys, setSelectedRowKeys] = useState<number[]>([]);
  const [statistics, setStatistics] = useState<Statistics | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [ownerFilter, setOwnerFilter] = useState<string>('');
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);
  const [searchValue, setSearchValue] = useState<string>('');

  // Column settings
  const {
    columnConfigs,
    setColumnConfigs,
    columnWidths,
    handleColumnResize,
    visibleColumns,
  } = useColumnSettings();

  const fetchInvoices = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (statusFilter) params.status = statusFilter;
      if (ownerFilter) params.owner = ownerFilter;
      if (dateRange?.[0]) params.start_date = dateRange[0].format('YYYY-MM-DD');
      if (dateRange?.[1]) params.end_date = dateRange[1].format('YYYY-MM-DD');
      if (searchValue) params.invoice_number = searchValue;

      const response = await listInvoices(params);
      setInvoices(response.items);
      setTotal(response.total);
    } catch (error) {
      message.error('获取发票列表失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStatistics = async () => {
    if (selectedRowKeys.length === 0) {
      setStatistics(null);
      return;
    }

    try {
      const stats = await getStatistics(selectedRowKeys);
      setStatistics(stats);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, [page, pageSize, statusFilter, ownerFilter, dateRange, searchValue]);

  useEffect(() => {
    fetchStatistics();
  }, [selectedRowKeys]);

  const handleStatusChange = (value: string | undefined) => {
    setStatusFilter(value);
    setPage(1);
  };

  const handleSearchChange = (value: string) => {
    setSearchValue(value);
    setPage(1);
  };

  const handleDateRangeChange = (range: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null) => {
    setDateRange(range);
    setPage(1);
  };

  const handleOwnerChange = (value: string) => {
    setOwnerFilter(value);
    setPage(1);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteInvoice(id);
      message.success('删除成功');
      fetchInvoices();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleBatchUpdate = async (status: string) => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择发票');
      return;
    }

    try {
      await batchUpdateInvoices(selectedRowKeys, status);
      message.success('批量更新成功');
      setSelectedRowKeys([]);
      fetchInvoices();
    } catch (error) {
      message.error('批量更新失败');
    }
  };

  const handleBatchDelete = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择发票');
      return;
    }

    Modal.confirm({
      title: '确认批量删除',
      content: `确定要删除选中的 ${selectedRowKeys.length} 张发票吗？此操作不可恢复。`,
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const result = await batchDeleteInvoices(selectedRowKeys);
          message.success(result.message);
          setSelectedRowKeys([]);
          fetchInvoices();
        } catch (error) {
          message.error('批量删除失败');
        }
      },
    });
  };

  const handleBatchReprocess = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择发票');
      return;
    }

    Modal.confirm({
      title: '确认重新解析',
      content: `确定要重新解析选中的 ${selectedRowKeys.length} 张发票吗？旧的解析结果将被清除。`,
      okText: '确认重新解析',
      cancelText: '取消',
      onOk: async () => {
        try {
          const result = await batchReprocessInvoices(selectedRowKeys);
          message.success(result.message);
          setSelectedRowKeys([]);
          fetchInvoices();
        } catch (error) {
          message.error('批量重新解析失败');
        }
      },
    });
  };

  const handleExport = (format: 'csv' | 'excel') => {
    const params = new URLSearchParams();

    if (selectedRowKeys.length > 0) {
      params.append('invoice_ids', selectedRowKeys.join(','));
    }
    if (statusFilter) {
      params.append('status', statusFilter);
    }
    if (ownerFilter) {
      params.append('owner', ownerFilter);
    }
    if (dateRange?.[0]) {
      params.append('start_date', dateRange[0].format('YYYY-MM-DD'));
    }
    if (dateRange?.[1]) {
      params.append('end_date', dateRange[1].format('YYYY-MM-DD'));
    }

    const url = `/api/invoices/export/${format}?${params.toString()}`;
    window.open(url, '_blank');
  };

  // All column definitions
  const allColumnDefinitions: Record<string, ColumnsType<Invoice>[number]> = useMemo(
    () => ({
      invoice_number: {
        title: '发票号码',
        dataIndex: 'invoice_number',
        key: 'invoice_number',
        width: columnWidths.invoice_number,
        ellipsis: true,
        render: (val) => val || '-',
        onHeaderCell: () => ({
          width: columnWidths.invoice_number,
          onResize: handleColumnResize('invoice_number'),
        }),
      },
      issue_date: {
        title: '开票日期',
        dataIndex: 'issue_date',
        key: 'issue_date',
        width: columnWidths.issue_date,
        render: (val) => val || '-',
        onHeaderCell: () => ({
          width: columnWidths.issue_date,
          onResize: handleColumnResize('issue_date'),
        }),
      },
      buyer_name: {
        title: '购买方',
        dataIndex: 'buyer_name',
        key: 'buyer_name',
        width: columnWidths.buyer_name,
        ellipsis: true,
        render: (val) => val || '-',
        onHeaderCell: () => ({
          width: columnWidths.buyer_name,
          onResize: handleColumnResize('buyer_name'),
        }),
      },
      buyer_tax_id: {
        title: '购买方税号',
        dataIndex: 'buyer_tax_id',
        key: 'buyer_tax_id',
        width: columnWidths.buyer_tax_id,
        ellipsis: true,
        render: (val) => val || '-',
        onHeaderCell: () => ({
          width: columnWidths.buyer_tax_id,
          onResize: handleColumnResize('buyer_tax_id'),
        }),
      },
      seller_name: {
        title: '销售方',
        dataIndex: 'seller_name',
        key: 'seller_name',
        width: columnWidths.seller_name,
        ellipsis: true,
        render: (val) => val || '-',
        onHeaderCell: () => ({
          width: columnWidths.seller_name,
          onResize: handleColumnResize('seller_name'),
        }),
      },
      seller_tax_id: {
        title: '销售方税号',
        dataIndex: 'seller_tax_id',
        key: 'seller_tax_id',
        width: columnWidths.seller_tax_id,
        ellipsis: true,
        render: (val) => val || '-',
        onHeaderCell: () => ({
          width: columnWidths.seller_tax_id,
          onResize: handleColumnResize('seller_tax_id'),
        }),
      },
      item_name: {
        title: '项目名称',
        dataIndex: 'item_name',
        key: 'item_name',
        width: columnWidths.item_name,
        ellipsis: true,
        render: (val) => val || '-',
        onHeaderCell: () => ({
          width: columnWidths.item_name,
          onResize: handleColumnResize('item_name'),
        }),
      },
      specification: {
        title: '规格型号',
        dataIndex: 'specification',
        key: 'specification',
        width: columnWidths.specification,
        ellipsis: true,
        render: (val) => val || '-',
        onHeaderCell: () => ({
          width: columnWidths.specification,
          onResize: handleColumnResize('specification'),
        }),
      },
      unit: {
        title: '单位',
        dataIndex: 'unit',
        key: 'unit',
        width: columnWidths.unit,
        render: (val) => val || '-',
        onHeaderCell: () => ({
          width: columnWidths.unit,
          onResize: handleColumnResize('unit'),
        }),
      },
      quantity: {
        title: '数量',
        dataIndex: 'quantity',
        key: 'quantity',
        width: columnWidths.quantity,
        align: 'right',
        render: (val) => (val != null ? Number(val) : '-'),
        onHeaderCell: () => ({
          width: columnWidths.quantity,
          onResize: handleColumnResize('quantity'),
        }),
      },
      unit_price: {
        title: '单价',
        dataIndex: 'unit_price',
        key: 'unit_price',
        width: columnWidths.unit_price,
        align: 'right',
        render: (val) => (val != null ? `¥${Number(val).toFixed(4)}` : '-'),
        onHeaderCell: () => ({
          width: columnWidths.unit_price,
          onResize: handleColumnResize('unit_price'),
        }),
      },
      amount: {
        title: '金额(不含税)',
        dataIndex: 'amount',
        key: 'amount',
        width: columnWidths.amount,
        align: 'right',
        render: (val) => (val != null ? `¥${Number(val).toFixed(2)}` : '-'),
        onHeaderCell: () => ({
          width: columnWidths.amount,
          onResize: handleColumnResize('amount'),
        }),
      },
      tax_rate: {
        title: '税率',
        dataIndex: 'tax_rate',
        key: 'tax_rate',
        width: columnWidths.tax_rate,
        render: (val) => val || '-',
        onHeaderCell: () => ({
          width: columnWidths.tax_rate,
          onResize: handleColumnResize('tax_rate'),
        }),
      },
      tax_amount: {
        title: '税额',
        dataIndex: 'tax_amount',
        key: 'tax_amount',
        width: columnWidths.tax_amount,
        align: 'right',
        render: (val) => (val != null ? `¥${Number(val).toFixed(2)}` : '-'),
        onHeaderCell: () => ({
          width: columnWidths.tax_amount,
          onResize: handleColumnResize('tax_amount'),
        }),
      },
      total_with_tax: {
        title: '价税合计',
        dataIndex: 'total_with_tax',
        key: 'total_with_tax',
        width: columnWidths.total_with_tax,
        align: 'right',
        render: (val) => (val != null ? `¥${Number(val).toFixed(2)}` : '-'),
        onHeaderCell: () => ({
          width: columnWidths.total_with_tax,
          onResize: handleColumnResize('total_with_tax'),
        }),
      },
      status: {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        width: columnWidths.status,
        render: (status: string) => (
          <Tag color={statusColors[status] || 'default'}>{status}</Tag>
        ),
        onHeaderCell: () => ({
          width: columnWidths.status,
          onResize: handleColumnResize('status'),
        }),
      },
      owner: {
        title: '归属人',
        dataIndex: 'owner',
        key: 'owner',
        width: columnWidths.owner,
        render: (val) => val || '-',
        onHeaderCell: () => ({
          width: columnWidths.owner,
          onResize: handleColumnResize('owner'),
        }),
      },
      file_name: {
        title: '文件名',
        dataIndex: 'file_name',
        key: 'file_name',
        width: columnWidths.file_name,
        ellipsis: true,
        render: (val) => val || '-',
        onHeaderCell: () => ({
          width: columnWidths.file_name,
          onResize: handleColumnResize('file_name'),
        }),
      },
      created_at: {
        title: '创建时间',
        dataIndex: 'created_at',
        key: 'created_at',
        width: columnWidths.created_at,
        render: (val) => (val ? dayjs(val).format('YYYY-MM-DD HH:mm') : '-'),
        onHeaderCell: () => ({
          width: columnWidths.created_at,
          onResize: handleColumnResize('created_at'),
        }),
      },
      updated_at: {
        title: '更新时间',
        dataIndex: 'updated_at',
        key: 'updated_at',
        width: columnWidths.updated_at,
        render: (val) => (val ? dayjs(val).format('YYYY-MM-DD HH:mm') : '-'),
        onHeaderCell: () => ({
          width: columnWidths.updated_at,
          onResize: handleColumnResize('updated_at'),
        }),
      },
      action: {
        title: '操作',
        key: 'action',
        width: columnWidths.action,
        fixed: 'right' as const,
        render: (_, record) => (
          <Space>
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/invoices/${record.id}`)}
            >
              详情
            </Button>
            <Popconfirm
              title="确定删除？"
              onConfirm={() => handleDelete(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        ),
      },
    }),
    [columnWidths, handleColumnResize, navigate]
  );

  // Build columns based on visible column configs
  const columns: ColumnsType<Invoice> = useMemo(() => {
    return visibleColumns
      .map((config) => allColumnDefinitions[config.key])
      .filter(Boolean);
  }, [visibleColumns, allColumnDefinitions]);

  // Calculate total scroll width
  const scrollX = useMemo(() => {
    return visibleColumns.reduce(
      (sum, col) => sum + (columnWidths[col.key] || 100),
      0
    );
  }, [visibleColumns, columnWidths]);

  // Calculate statistics from current page invoices
  const pageStatistics = useInvoiceStatistics(invoices);

  // Generate total text for control bar
  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total, pageSize]);
  const displayStart = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const displayEnd = total === 0 ? 0 : Math.min(page * pageSize, total);

  const totalText = useMemo(() => {
    return `显示 ${displayStart}-${displayEnd} 条，共 ${total} 条`;
  }, [displayStart, displayEnd, total]);

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  // Table components with resizable header
  const tableComponents = {
    header: {
      cell: ResizableTitle,
    },
  };

  return (
    <div className={styles.pageContainer}>
      {/* Page Header */}
      <div className={styles.pageHeader}>
        <div className={styles.headerContent}>
          <h1 className={styles.pageTitle}>发票列表</h1>
          <p className={styles.pageSubtitle}>管理和查看所有发票记录</p>
        </div>
        <div className={styles.headerActions}>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => handleExport('excel')}
            className={styles.secondaryButton}
          >
            导出
          </Button>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={() => navigate('/upload')}
            className={styles.primaryButton}
          >
            上传发票
          </Button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className={styles.metricsSection}>
        <MetricCard
          label="发票数量"
          value={pageStatistics.count}
        />
        <MetricCard
          label="金额合计"
          value={pageStatistics.totalAmount.toFixed(2)}
          prefix="¥"
        />
        <MetricCard
          label="税额合计"
          value={pageStatistics.totalTax.toFixed(2)}
          prefix="¥"
        />
        <MetricCard
          label="价税合计"
          value={pageStatistics.totalWithTax.toFixed(2)}
          prefix="¥"
        />
      </div>

      {/* Selected Statistics Card */}
      {statistics && (
        <Card style={{ marginBottom: 32 }}>
          <Row gutter={24}>
            <Col span={6}>
              <Statistic title="选中数量" value={statistics.count} suffix="张" />
            </Col>
            <Col span={6}>
              <Statistic
                title="金额合计"
                value={statistics.total_amount}
                precision={2}
                prefix="¥"
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="税额合计"
                value={statistics.total_tax}
                precision={2}
                prefix="¥"
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="价税合计"
                value={statistics.total_with_tax}
                precision={2}
                prefix="¥"
              />
            </Col>
          </Row>
        </Card>
      )}

      {/* Control Bar */}
      <ControlBar
        searchPlaceholder="搜索发票号码..."
        searchValue={searchValue}
        onSearchChange={handleSearchChange}
        statusFilter={statusFilter}
        onStatusChange={handleStatusChange}
        statusOptions={Object.values(InvoiceStatus).map((s) => ({ label: s, value: s }))}
        dateRange={dateRange}
        onDateRangeChange={handleDateRangeChange}
        totalText={totalText}
      />

      {/* Additional Controls */}
      <div className={styles.additionalControls}>
        <Input
          placeholder="归属人"
          style={{ width: 120 }}
          value={ownerFilter}
          onChange={(e) => handleOwnerChange(e.target.value)}
          onPressEnter={fetchInvoices}
        />

        <Button icon={<ReloadOutlined />} onClick={fetchInvoices}>
          刷新
        </Button>

        <Button icon={<DownloadOutlined />} onClick={() => handleExport('csv')}>
          导出CSV
        </Button>

        <ColumnSelector columns={columnConfigs} onChange={setColumnConfigs} />

        {selectedRowKeys.length > 0 && (
          <>
            <Select
              placeholder="批量修改状态"
              style={{ width: 140 }}
              onChange={handleBatchUpdate}
              options={Object.values(InvoiceStatus).map((s) => ({ label: s, value: s }))}
            />
            <Button
              icon={<SyncOutlined />}
              onClick={handleBatchReprocess}
            >
              重新解析
            </Button>
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleBatchDelete}
            >
              批量删除
            </Button>
            <span style={{ lineHeight: '32px' }}>
              已选择 {selectedRowKeys.length} 项
            </span>
          </>
        )}
      </div>

      {/* Table */}
      <div className={styles.tableContainer}>
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={invoices}
          components={tableComponents}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys as number[]),
          }}
          pagination={false}
          scroll={{ x: scrollX }}
          className={styles.invoiceTable}
        />
      </div>

      {/* Custom Pagination */}
      <div className={styles.paginationRow}>
        <div className={styles.paginationLeft}>
          <span className={styles.paginationText}>
            显示 {displayStart}-{displayEnd} 共 {total} 条
          </span>
        </div>
        <div className={styles.paginationRight}>
          <Button
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
          >
            上一页
          </Button>
          <span className={styles.pageNumbers}>
            {page} / {totalPages}
          </span>
          <Button
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            下一页
          </Button>
          <Select
            value={pageSize}
            onChange={(val) => {
              setPageSize(val);
              setPage(1);
            }}
            options={[
              { label: '10 条/页', value: 10 },
              { label: '20 条/页', value: 20 },
              { label: '50 条/页', value: 50 },
              { label: '100 条/页', value: 100 },
            ]}
            style={{ width: 120, marginLeft: 12 }}
          />
        </div>
      </div>
    </div>
  );
}

export default InvoiceListPage;
