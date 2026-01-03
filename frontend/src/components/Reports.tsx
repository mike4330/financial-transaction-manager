import React, { useState, useEffect } from 'react';
import styles from './Reports.module.css';

interface CategoryTotal {
  category: string;
  subcategory: string | null;
  amount: number;
  transaction_count: number;
  percentage: number;
}

interface YearlyCategoryData {
  year: number;
  categories: CategoryTotal[];
  total_spending: number;
  available_years: number[];
}

const Reports: React.FC = () => {
  const [data, setData] = useState<YearlyCategoryData | null>(null);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchYearlyData(selectedYear);
  }, [selectedYear]);

  const fetchYearlyData = async (year: number | null) => {
    try {
      setLoading(true);
      setError(null);

      const url = year
        ? `/api/reports/yearly-category-totals?year=${year}`
        : '/api/reports/yearly-category-totals';

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Failed to fetch yearly report data');
      }

      const result = await response.json();
      setData(result);

      // Set selected year if not already set
      if (!selectedYear) {
        setSelectedYear(result.year);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleYearChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedYear(parseInt(event.target.value));
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading report data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>Error: {error}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>No data available</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>Yearly Expense Report</h1>

        <div className={styles.controls}>
          <label htmlFor="year-select" className={styles.label}>
            Year:
          </label>
          <select
            id="year-select"
            value={selectedYear || data.year}
            onChange={handleYearChange}
            className={styles.select}
          >
            {data.available_years.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className={styles.summary}>
        <div className={styles.summaryCard}>
          <div className={styles.summaryLabel}>Total Expenses</div>
          <div className={styles.summaryValue}>{formatCurrency(data.total_spending)}</div>
        </div>
        <div className={styles.summaryCard}>
          <div className={styles.summaryLabel}>Categories</div>
          <div className={styles.summaryValue}>
            {new Set(data.categories.map(c => c.category)).size}
          </div>
        </div>
        <div className={styles.summaryCard}>
          <div className={styles.summaryLabel}>Transactions</div>
          <div className={styles.summaryValue}>
            {data.categories.reduce((sum, c) => sum + c.transaction_count, 0).toLocaleString()}
          </div>
        </div>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>Category</th>
              <th className={styles.th}>Subcategory</th>
              <th className={styles.thRight}>Amount</th>
              <th className={styles.thRight}>% of Total</th>
              <th className={styles.thRight}>Transactions</th>
            </tr>
          </thead>
          <tbody>
            {data.categories.map((item, index) => (
              <tr key={index} className={styles.row}>
                <td className={styles.td}>{item.category}</td>
                <td className={styles.td}>
                  {item.subcategory || <span className={styles.noSubcategory}>—</span>}
                </td>
                <td className={styles.tdRight}>{formatCurrency(item.amount)}</td>
                <td className={styles.tdRight}>{item.percentage.toFixed(1)}%</td>
                <td className={styles.tdRight}>{item.transaction_count.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className={styles.totalRow}>
              <td className={styles.tdBold} colSpan={2}>Total</td>
              <td className={styles.tdRightBold}>{formatCurrency(data.total_spending)}</td>
              <td className={styles.tdRightBold}>100.0%</td>
              <td className={styles.tdRightBold}>
                {data.categories.reduce((sum, c) => sum + c.transaction_count, 0).toLocaleString()}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
};

export default Reports;
