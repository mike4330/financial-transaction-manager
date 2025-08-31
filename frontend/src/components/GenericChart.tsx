import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { useTimeRange } from '../contexts/TimeRangeContext';
import { usePreferences } from '../contexts/PreferencesContext';
import { useTheme } from '../contexts/ThemeContext';
import type { ChartConfig } from '../config/chartConfig';
import { TransactionModal } from './TransactionModal';
import { getChartTheme, getGridProps, getAxisProps, getTooltipProps } from '../styles/chartTheme';

interface Transaction {
  id: number;
  date: string;
  amount: number;
  description: string;
  payee: string;
  account: string;
}

interface ChartData {
  month: string;
  amount: number;
  count: number;
}

interface GenericChartProps {
  config: ChartConfig;
}

// Utility function to format dates without timezone conversion issues
const formatDateSafe = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

export const GenericChart: React.FC<GenericChartProps> = ({ config }) => {
  const [data, setData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartType, setChartType] = useState<'line' | 'bar'>('bar');
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState<{
    startDate: string;
    endDate: string;
    title: string;
  } | null>(null);
  const { timeRange, getDateFilter, startFromZero } = useTimeRange();
  const { homePreferences } = usePreferences();
  const { isDarkMode } = useTheme();

  // Get consistent chart theme from centralized theme system
  const chartTheme = useMemo(() => getChartTheme(isDarkMode), [isDarkMode]);
  const gridProps = useMemo(() => getGridProps(isDarkMode), [isDarkMode]);
  const axisProps = useMemo(() => getAxisProps(isDarkMode), [isDarkMode]);
  const tooltipProps = useMemo(() => getTooltipProps(isDarkMode), [isDarkMode]);

  // Helper function to calculate Y-axis domain with padding for non-zero mode
  const getYAxisDomain = (data: any[]) => {
    if (startFromZero) {
      return [0, 'dataMax'];
    }
    
    if (data.length === 0) {
      return ['dataMin', 'dataMax'];
    }
    
    const values = data.map(d => d.amount).filter(v => v != null);
    if (values.length === 0) {
      return ['dataMin', 'dataMax'];
    }
    
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min;
    
    // Add 10% padding to both ends, but ensure minimum doesn't go below zero
    const padding = range * 0.1;
    const paddedMin = Math.max(0, min - padding); // Floor at zero
    return [paddedMin, max + padding];
  };

  // Helper function to calculate date range from clicked data point
  const getDateRangeFromDataPoint = (monthLabel: string) => {
    console.log('Month label received:', monthLabel); // Debug log
    const useWeeklyBinning = timeRange === '1M' || timeRange === '3M';
    
    if (useWeeklyBinning) {
      // For weekly binning, monthLabel is like "Dec 8" 
      console.log('Using weekly binning for:', monthLabel);
      const currentYear = new Date().getFullYear();
      const parsedDate = new Date(`${monthLabel} ${currentYear}`);
      console.log('Parsed date:', parsedDate);
      
      if (isNaN(parsedDate.getTime())) {
        console.error('Invalid date created from:', monthLabel);
        // Fallback: try parsing differently
        const today = new Date();
        return {
          startDate: formatDateSafe(today),
          endDate: formatDateSafe(today),
          title: `${config.title} - ${monthLabel}`
        };
      }
      
      // Calculate start of week (Sunday)
      const startOfWeek = new Date(parsedDate);
      startOfWeek.setDate(parsedDate.getDate() - parsedDate.getDay());
      
      // Calculate end of week (Saturday)
      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 6);
      
      
      return {
        startDate: formatDateSafe(startOfWeek),
        endDate: formatDateSafe(endOfWeek),
        title: `${config.title} - Week of ${monthLabel}`
      };
    } else {
      // For monthly binning, monthLabel is like "Jun 2025"
      console.log('Using monthly binning for:', monthLabel);
      const parts = monthLabel.split(' ');
      console.log('Split parts:', parts);
      
      if (parts.length !== 2) {
        console.error('Unexpected month label format:', monthLabel);
        const today = new Date();
        return {
          startDate: formatDateSafe(today),
          endDate: formatDateSafe(today),
          title: `${config.title} - ${monthLabel}`
        };
      }
      
      const monthName = parts[0];
      const year = parseInt(parts[1]);
      
      const monthIndex = new Date(`${monthName} 1, 2000`).getMonth();
      console.log('Month index for', monthName, ':', monthIndex);
      
      if (isNaN(year) || monthIndex === -1) {
        console.error('Invalid year or month:', year, monthName);
        const today = new Date();
        return {
          startDate: formatDateSafe(today),
          endDate: formatDateSafe(today),
          title: `${config.title} - ${monthLabel}`
        };
      }
      
      const startDate = new Date(year, monthIndex, 1);
      const endDate = new Date(year, monthIndex + 1, 0); // Last day of month
      
      console.log('Calculated date range:', startDate, endDate);
      
      
      return {
        startDate: formatDateSafe(startDate),
        endDate: formatDateSafe(endDate),
        title: `${config.title} - ${monthName} ${year}`
      };
    }
  };

  const handleDataPointClick = (data: any, index: number) => {
    console.log('Chart clicked:', data, index); // Debug log
    if (data && data.month) {
      const period = getDateRangeFromDataPoint(data.month);
      setSelectedPeriod(period);
      setModalOpen(true);
    }
  };

  const handleLineClick = (data: any, index: number, event: any) => {
    console.log('Line clicked:', data, index); // Debug log
    handleDataPointClick(data, index);
  };

  const handleBarClick = (data: any, index: number, event: any) => {
    console.log('Bar clicked:', data, index); // Debug log  
    handleDataPointClick(data, index);
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Get date filter from time range context
        const dateFilter = getDateFilter();
        
        let apiUrl: string;
        
        if (config.endpoint) {
          // Use custom endpoint with date filtering
          const endpointUrl = new URL(config.endpoint, window.location.origin);
          if (dateFilter.startDate) {
            endpointUrl.searchParams.append('start_date', dateFilter.startDate);
          }
          endpointUrl.searchParams.append('limit', '1000');
          apiUrl = endpointUrl.toString();
        } else {
          // Use standard category/subcategory filtering
          const params = new URLSearchParams({
            category: config.category,
            subcategory: config.subcategory,
            limit: '1000'
          });
          
          if (dateFilter.startDate) {
            params.append('start_date', dateFilter.startDate);
          }
          apiUrl = `/api/transactions?${params.toString()}`;
        }
        
        // Fetch filtered transactions
        const response = await fetch(apiUrl);
        const result = await response.json();
        
        if (!response.ok) {
          throw new Error(`Failed to fetch ${config.subcategory} data`);
        }

        let transactions: Transaction[] = result.transactions || [];
        
        // Apply account filtering if any accounts are selected
        if (homePreferences.selectedAccounts.length > 0) {
          transactions = transactions.filter(transaction => 
            homePreferences.selectedAccounts.includes(transaction.account)
          );
        }
        
        // Determine binning strategy based on time range
        const useWeeklyBinning = timeRange === '1M' || timeRange === '3M';
        
        // Group by appropriate time period and calculate totals
        const groupedData = transactions.reduce((acc, transaction) => {
          // Parse date string more explicitly to avoid timezone issues
          const dateParts = transaction.date.split('-');
          const year = parseInt(dateParts[0]);
          const month = parseInt(dateParts[1]) - 1; // month is 0-based in Date constructor
          const day = parseInt(dateParts[2]);
          const date = new Date(year, month, day);
          
          let key: string;
          let label: string;
          
          if (useWeeklyBinning) {
            // Weekly binning - start of week (Sunday)
            const startOfWeek = new Date(date);
            startOfWeek.setDate(date.getDate() - date.getDay());
            key = `${startOfWeek.getFullYear()}-${String(startOfWeek.getMonth() + 1).padStart(2, '0')}-${String(startOfWeek.getDate()).padStart(2, '0')}`;
            label = startOfWeek.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
          } else {
            // Monthly binning
            key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
            label = date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
          }
          
          if (!acc[key]) {
            acc[key] = {
              month: label,
              amount: 0,
              count: 0,
              sortKey: key
            };
          }
          
          acc[key].amount += Math.abs(transaction.amount); // Use absolute value for spending
          acc[key].count += 1;
          
          return acc;
        }, {} as Record<string, ChartData & { sortKey: string }>);

        // Convert to array and sort by date
        const chartData = Object.values(groupedData)
          .sort((a, b) => a.sortKey.localeCompare(b.sortKey))
          .map(({ sortKey, ...data }) => data);

        setData(chartData);
      } catch (err) {
        setError(err instanceof Error ? err.message : `Failed to load ${config.subcategory} data`);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [timeRange, config, homePreferences.selectedAccounts]); // Re-fetch when time range, config, or account filters change

  const formatCurrency = (value: number) => `$${value.toFixed(0)}`;
  const formatTooltip = (value: number, name: string) => {
    if (name === 'amount') {
      return [`$${value.toFixed(2)}`, 'Spent'];
    }
    return [value, 'Transactions'];
  };

  if (loading) {
    return (
      <div className="card">
        <h3 className="text-xl mb-4">{config.emoji} {config.title}</h3>
        <div style={{ textAlign: 'center', padding: '1rem' }}>
          <p>Loading {config.subcategory.toLowerCase()} data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h3 className="text-xl mb-4">{config.emoji} {config.title}</h3>
        <div style={{ textAlign: 'center', padding: '1rem', color: '#dc2626' }}>
          <p>Error: {error}</p>
        </div>
      </div>
    );
  }

  const totalSpent = data.reduce((sum, item) => sum + item.amount, 0);
  const avgMonthly = totalSpent / (data.length || 1);
  const useWeeklyBinning = timeRange === '1M' || timeRange === '3M';

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <h3 className="text-xl">{config.emoji} {config.title}</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span style={{ fontSize: '0.875rem', color: '#666' }}>
            {timeRange === 'ALL' ? 'All Time' : timeRange}
          </span>
          <div>
            <button
            onClick={() => setChartType('line')}
            style={{
              padding: '0.5rem 1rem',
              marginRight: '0.5rem',
              border: '1px solid #ccc',
              borderRadius: '4px',
              backgroundColor: chartType === 'line' ? config.color : 'white',
              color: chartType === 'line' ? 'white' : 'black',
              cursor: 'pointer'
            }}
          >
            Line
          </button>
          <button
            onClick={() => setChartType('bar')}
            style={{
              padding: '0.5rem 1rem',
              border: '1px solid #ccc',
              borderRadius: '4px',
              backgroundColor: chartType === 'bar' ? config.color : 'white',
              color: chartType === 'bar' ? 'white' : 'black',
              cursor: 'pointer'
            }}
          >
            Bar
          </button>
          </div>
        </div>
      </div>

      <div style={{ 
        marginBottom: '0.75rem',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '0.5rem'
      }}>
        <p><strong>Total Spent:</strong> ${totalSpent.toFixed(2)}</p>
        <p><strong>Average {useWeeklyBinning ? 'Weekly' : 'Monthly'}:</strong> ${avgMonthly.toFixed(2)}</p>
      </div>

      <div style={{ width: '100%', height: '320px' }}>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'line' ? (
            <LineChart data={data} animationDuration={200}>
              <CartesianGrid {...gridProps} />
              <XAxis 
                dataKey="month" 
                angle={-45}
                textAnchor="end"
                height={80}
                fontSize={12}
                {...axisProps}
              />
              <YAxis 
                tickFormatter={formatCurrency}
                domain={getYAxisDomain(data)}
                {...axisProps}
              />
              <Tooltip 
                formatter={formatTooltip}
                {...tooltipProps}
              />
              <Line 
                type="monotone" 
                dataKey="amount" 
                stroke={config.color} 
                strokeWidth={2}
                dot={{ fill: config.color, strokeWidth: 2, r: 4, cursor: 'pointer' }}
                activeDot={{ r: 6, cursor: 'pointer' }}
                onClick={handleLineClick}
                animationDuration={200}
              />
            </LineChart>
          ) : (
            <BarChart data={data} animationDuration={200}>
              <CartesianGrid {...gridProps} />
              <XAxis 
                dataKey="month" 
                angle={-45}
                textAnchor="end"
                height={80}
                fontSize={12}
                {...axisProps}
              />
              <YAxis 
                tickFormatter={formatCurrency}
                domain={getYAxisDomain(data)}
                {...axisProps}
              />
              <Tooltip 
                formatter={formatTooltip}
                {...tooltipProps}
              />
              <Bar dataKey="amount" fill={config.color} style={{ cursor: 'pointer' }} onClick={handleBarClick} animationDuration={200} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
      
      {/* Transaction Modal */}
      <TransactionModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        category={config.category}
        subcategory={config.subcategory}
        startDate={selectedPeriod?.startDate}
        endDate={selectedPeriod?.endDate}
        title={selectedPeriod?.title}
      />
    </div>
  );
};

export const MemoizedGenericChart = React.memo(GenericChart);