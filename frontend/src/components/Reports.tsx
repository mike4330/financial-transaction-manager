import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, FileDown } from 'lucide-react';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import styles from './Reports.module.css';

interface Subcategory {
  subcategory: string;
  amount: number;
  transaction_count: number;
  percentage: number;
}

interface CategoryTotal {
  category: string;
  amount: number;
  transaction_count: number;
  percentage: number;
  subcategories: Subcategory[];
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
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

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

  const toggleCategory = (categoryName: string) => {
    setExpandedCategories((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(categoryName)) {
        newSet.delete(categoryName);
      } else {
        newSet.add(categoryName);
      }
      return newSet;
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const exportToPDF = () => {
    if (!data) return;

    const doc = new jsPDF();

    // Title
    doc.setFontSize(18);
    doc.text(`Yearly Expense Report - ${data.year}`, 14, 22);

    // Summary information
    doc.setFontSize(11);
    doc.text(`Total Expenses: ${formatCurrency(data.total_spending)}`, 14, 32);
    doc.text(`Categories: ${data.categories.length}`, 14, 38);
    doc.text(`Total Transactions: ${data.categories.reduce((sum, c) => sum + c.transaction_count, 0).toLocaleString()}`, 14, 44);

    // Prepare table data
    const tableData = data.categories.map(category => [
      category.category,
      formatCurrency(category.amount),
      `${category.percentage.toFixed(1)}%`,
      category.transaction_count.toLocaleString()
    ]);

    // Add table
    autoTable(doc, {
      head: [['Category', 'Amount', '% of Total', 'Transactions']],
      body: tableData,
      startY: 52,
      theme: 'grid',
      headStyles: {
        fillColor: [66, 66, 66],
        textColor: 255,
        fontStyle: 'bold'
      },
      columnStyles: {
        1: { halign: 'right' },
        2: { halign: 'right' },
        3: { halign: 'right' }
      }
    });

    // Add total row
    const finalY = (doc as any).lastAutoTable.finalY;
    autoTable(doc, {
      body: [[
        'Total',
        formatCurrency(data.total_spending),
        '100.0%',
        data.categories.reduce((sum, c) => sum + c.transaction_count, 0).toLocaleString()
      ]],
      startY: finalY,
      theme: 'plain',
      styles: {
        fontStyle: 'bold'
      },
      columnStyles: {
        1: { halign: 'right' },
        2: { halign: 'right' },
        3: { halign: 'right' }
      }
    });

    // Save the PDF
    doc.save(`expense-report-${data.year}.pdf`);
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

          <button onClick={exportToPDF} className={styles.exportButton}>
            <FileDown size={18} />
            Export PDF
          </button>
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
            {data.categories.length}
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
              <th className={styles.thRight}>Amount</th>
              <th className={styles.thRight}>% of Total</th>
              <th className={styles.thRight}>Transactions</th>
            </tr>
          </thead>
          <tbody>
            {data.categories.map((category, index) => (
              <React.Fragment key={index}>
                {/* Category Row */}
                <tr
                  className={`${styles.row} ${styles.categoryRow} ${category.subcategories.length > 0 ? styles.clickable : ''}`}
                  onClick={() => category.subcategories.length > 0 && toggleCategory(category.category)}
                >
                  <td className={styles.td}>
                    <div className={styles.categoryCell}>
                      {category.subcategories.length > 0 && (
                        <span className={styles.expandIcon}>
                          {expandedCategories.has(category.category) ? (
                            <ChevronDown size={18} />
                          ) : (
                            <ChevronRight size={18} />
                          )}
                        </span>
                      )}
                      <span className={styles.categoryName}>{category.category}</span>
                      {category.subcategories.length > 0 && (
                        <span className={styles.subcategoryCount}>
                          ({category.subcategories.length})
                        </span>
                      )}
                    </div>
                  </td>
                  <td className={styles.tdRight}>{formatCurrency(category.amount)}</td>
                  <td className={styles.tdRight}>{category.percentage.toFixed(1)}%</td>
                  <td className={styles.tdRight}>{category.transaction_count.toLocaleString()}</td>
                </tr>

                {/* Subcategory Rows */}
                {expandedCategories.has(category.category) && category.subcategories.map((subcat, subIndex) => (
                  <tr key={`${index}-${subIndex}`} className={`${styles.row} ${styles.subcategoryRow}`}>
                    <td className={styles.td}>
                      <div className={styles.subcategoryCell}>
                        {subcat.subcategory}
                      </div>
                    </td>
                    <td className={styles.tdRight}>{formatCurrency(subcat.amount)}</td>
                    <td className={styles.tdRight}>{subcat.percentage.toFixed(1)}%</td>
                    <td className={styles.tdRight}>{subcat.transaction_count.toLocaleString()}</td>
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
          <tfoot>
            <tr className={styles.totalRow}>
              <td className={styles.tdBold}>Total</td>
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
