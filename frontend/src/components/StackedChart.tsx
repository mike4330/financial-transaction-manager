import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useTimeRange } from '../contexts/TimeRangeContext';
import { usePreferences } from '../contexts/PreferencesContext';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { cachedFetch } from '../utils/apiCache';
import styles from './StackedChart.module.css';

interface StackedChartProps {
  category: string;
  title: string;
  color?: string;
  currency?: boolean;
}

interface TransactionData {
  id: number;
  date: string;
  account: string;
  amount: number;
  payee: string;
  description: string;
  action: string;
  transaction_type: string;
  category: string;
  subcategory: string;
  category_id: number | null;
  subcategory_id: number | null;
}

interface ChartData {
  period: string;
  [key: string]: any; // Dynamic subcategory keys
}

// Generate colors for subcategories
const generateSubcategoryColors = (subcategories: string[], baseColor: string = '#ec4899') => {
  const colors: { [key: string]: string } = {};
  
  // Convert color (hex or rgba) to HSL for color variations
  const colorToHsl = (color: string) => {
    let r, g, b;
    
    if (color.startsWith('rgba')) {
      // Parse rgba(r, g, b, a) format
      const match = color.match(/rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)/);
      if (match) {
        r = parseInt(match[1]) / 255;
        g = parseInt(match[2]) / 255;
        b = parseInt(match[3]) / 255;
      } else {
        // Fallback to default pink color
        r = 236 / 255; g = 72 / 255; b = 153 / 255;
      }
    } else {
      // Parse hex format
      r = parseInt(color.slice(1, 3), 16) / 255;
      g = parseInt(color.slice(3, 5), 16) / 255;
      b = parseInt(color.slice(5, 7), 16) / 255;
    }
    
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    let h, s, l = (max + min) / 2;
    
    if (max === min) {
      h = s = 0;
    } else {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = (g - b) / d + (g < b ? 6 : 0); break;
        case g: h = (b - r) / d + 2; break;
        case b: h = (r - g) / d + 4; break;
        default: h = 0;
      }
      h /= 6;
    }
    
    return [h * 360, s * 100, l * 100];
  };
  
  const [baseH, baseS, baseL] = colorToHsl(baseColor);
  
  subcategories.forEach((sub, index) => {
    // Vary lightness and slightly adjust hue for each subcategory
    const lightness = Math.max(30, Math.min(70, baseL - 10 + (index * 15)));
    const hue = (baseH + (index * 30)) % 360;
    colors[sub] = `hsl(${hue}, ${baseS}%, ${lightness}%)`;
  });
  
  return colors;
};

const StackedChart: React.FC<StackedChartProps> = ({ 
  category, 
  title, 
  color = '#ec4899',
  currency = true 
}) => {
  const { timeRange, getDateFilter } = useTimeRange();
  const { homePreferences } = usePreferences();
  const [data, setData] = useState<ChartData[]>([]);
  const [subcategories, setSubcategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartType, setChartType] = useState<'bar' | 'line'>('bar');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const dateFilter = getDateFilter();
      const params = new URLSearchParams({
        category: category,
        limit: '10000' // Get all transactions for aggregation
      });

      // Add date filters if they exist
      if (dateFilter.startDate) {
        params.append('start_date', dateFilter.startDate);
      }
      if (dateFilter.endDate) {
        params.append('end_date', dateFilter.endDate);
      }

      const url = `/api/transactions?${params}`;

      const result = await cachedFetch(url);
      const transactions: TransactionData[] = result.transactions || [];

      // Filter by selected accounts if specified
      const filteredTransactions = homePreferences.selectedAccounts.length > 0
        ? transactions.filter(t => homePreferences.selectedAccounts.includes(t.account))
        : transactions;

      // Group by time period and subcategory
      const groupedData = groupByPeriodAndSubcategory(filteredTransactions);
      const uniqueSubcategories = Array.from(new Set(filteredTransactions.map(t => t.subcategory || 'Uncategorized')));
      
      setData(groupedData);
      setSubcategories(uniqueSubcategories);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [timeRange, category, homePreferences.selectedAccounts, getDateFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const groupByPeriodAndSubcategory = useCallback((transactions: TransactionData[]): ChartData[] => {
    const groups: { [key: string]: { [subcategory: string]: number } } = {};

    transactions.forEach(transaction => {
      const date = new Date(transaction.date);
      const subcategory = transaction.subcategory || 'Uncategorized';
      
      // Determine grouping period based on time range
      const dateFilter = getDateFilter();
      let daysDiff = 180; // Default to 6 months
      if (dateFilter.startDate) {
        const startDate = new Date(dateFilter.startDate);
        const endDate = dateFilter.endDate ? new Date(dateFilter.endDate) : new Date();
        daysDiff = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
      }
      let period: string;
      
      if (daysDiff <= 90) {
        // Weekly grouping for 3 months or less
        const startOfWeek = new Date(date);
        startOfWeek.setDate(date.getDate() - date.getDay());
        period = startOfWeek.toISOString().split('T')[0];
      } else {
        // Monthly grouping for longer periods
        period = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      }

      if (!groups[period]) {
        groups[period] = {};
      }

      if (!groups[period][subcategory]) {
        groups[period][subcategory] = 0;
      }

      groups[period][subcategory] += Math.abs(transaction.amount); // Use absolute values for spending
    });

    // Convert to chart format
    return Object.entries(groups)
      .map(([period, subcategoryAmounts]) => {
        const item: ChartData = { period };
        Object.entries(subcategoryAmounts).forEach(([subcategory, amount]) => {
          item[subcategory] = amount;
        });
        return item;
      })
      .sort((a, b) => a.period.localeCompare(b.period));
  }, [getDateFilter]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatPeriod = (period: string) => {
    if (period.includes('-') && period.length === 10) {
      // Weekly format (YYYY-MM-DD)
      return new Date(period).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } else {
      // Monthly format (YYYY-MM)
      const [year, month] = period.split('-');
      return new Date(parseInt(year), parseInt(month) - 1).toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short' 
      });
    }
  };

  const subcategoryColors = useMemo(() => 
    generateSubcategoryColors(subcategories, color), 
    [subcategories, color]
  );

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.loadingText}>Loading {title}...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorContainer}>
        <div className={styles.errorText}>Error: {error}</div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className={styles.noDataContainer}>
        <div className={styles.noDataText}>No data available for {title}</div>
      </div>
    );
  }

  const renderChart = () => {
    if (chartType === 'bar') {
      return (
        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis 
            dataKey="period" 
            tickFormatter={formatPeriod}
            stroke="#666"
          />
          <YAxis 
            tickFormatter={currency ? formatCurrency : undefined}
            stroke="#666"
          />
          <Tooltip 
            formatter={(value: number, name: string) => [
              currency ? formatCurrency(value) : value, 
              name
            ]}
            labelFormatter={(label: string) => `Period: ${formatPeriod(label)}`}
          />
          <Legend />
          
          {subcategories.map((subcategory) => (
            <Bar
              key={subcategory}
              dataKey={subcategory}
              stackId="subcategories"
              fill={subcategoryColors[subcategory]}
            />
          ))}
        </BarChart>
      );
    } else {
      return (
        <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis 
            dataKey="period" 
            tickFormatter={formatPeriod}
            stroke="#666"
          />
          <YAxis 
            tickFormatter={currency ? formatCurrency : undefined}
            stroke="#666"
          />
          <Tooltip 
            formatter={(value: number, name: string) => [
              currency ? formatCurrency(value) : value, 
              name
            ]}
            labelFormatter={(label: string) => `Period: ${formatPeriod(label)}`}
          />
          <Legend />
          
          {subcategories.map((subcategory) => (
            <Line
              key={subcategory}
              type="monotone"
              dataKey={subcategory}
              stroke={subcategoryColors[subcategory]}
              strokeWidth={2}
              dot={{ r: 4 }}
              connectNulls={false}
            />
          ))}
        </LineChart>
      );
    }
  };

  return (
    <div className={styles.chartContainer}>
      <div className={styles.chartHeader}>
        <h3 className={styles.chartTitle}>{title}</h3>
        <div className={styles.toggleContainer}>
          <button
            onClick={() => setChartType('bar')}
            className={`${styles.toggleButton} ${
              chartType === 'bar' ? styles.toggleButtonActive : ''
            }`}
          >
            📊 Stacked
          </button>
          <button
            onClick={() => setChartType('line')}
            className={`${styles.toggleButton} ${
              chartType === 'line' ? styles.toggleButtonActive : ''
            }`}
          >
            📈 Lines
          </button>
        </div>
      </div>
      
      <ResponsiveContainer width="100%" height={300}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
};

export default React.memo(StackedChart);