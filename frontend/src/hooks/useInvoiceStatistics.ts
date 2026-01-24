import { useMemo } from 'react';
import type { Invoice } from '../types/invoice';

interface InvoiceStatistics {
  count: number;
  totalAmount: number;
  totalTax: number;
  totalWithTax: number;
}

export const useInvoiceStatistics = (invoices: Invoice[]): InvoiceStatistics => {
  return useMemo(() => {
    if (!invoices || invoices.length === 0) {
      return {
        count: 0,
        totalAmount: 0,
        totalTax: 0,
        totalWithTax: 0,
      };
    }

    const stats = invoices.reduce(
      (acc, invoice) => {
        const amount = invoice.amount ? Number(invoice.amount) : 0;
        const tax = invoice.tax_amount ? Number(invoice.tax_amount) : 0;
        const total = invoice.total_with_tax ? Number(invoice.total_with_tax) : 0;

        return {
          count: acc.count + 1,
          totalAmount: acc.totalAmount + amount,
          totalTax: acc.totalTax + tax,
          totalWithTax: acc.totalWithTax + total,
        };
      },
      {
        count: 0,
        totalAmount: 0,
        totalTax: 0,
        totalWithTax: 0,
      }
    );

    return stats;
  }, [invoices]);
};
