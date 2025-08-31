import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { useTimeRange } from '../contexts/TimeRangeContext';
import { useTheme } from '../contexts/ThemeContext';
import { getGridProps, getAxisProps, getTooltipProps } from '../styles/chartTheme';
import type { DashboardCard } from '../types/dashboard';
import { TransactionModal } from './TransactionModal';

interface Transaction {
  id: number;
  date: string;
  amount: number;
  description: string;
  payee: string;
}

interface ChartData {
  month: string;
  percentage: number;
  numerator: number;
  denominator: number;
  count: number;
}

interface PercentageChartProps {
  card: DashboardCard;
}

export const PercentageChart: React.FC<PercentageChartProps> = ({ card }) => {
  const [data, setData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartType, setChartType] = useState<'line' | 'bar'>(card.config?.chartType || 'bar');
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState<{
    startDate: string;
    endDate: string;
    title: string;
    category: string;
    subcategory?: string;
  } | null>(null);
  const { timeRange, getDateFilter, startFromZero } = useTimeRange();
  const { isDarkMode } = useTheme();

  // Get theme-aware chart props
  const gridProps = getGridProps(isDarkMode);
  const axisProps = getAxisProps(isDarkMode);
  const tooltipProps = getTooltipProps(isDarkMode);

  // Helper function to calculate Y-axis domain with padding for non-zero mode
  const getYAxisDomain = (data: any[]) => {
    if (startFromZero) {
      return [0, 'dataMax'];
    }
    
    if (data.length === 0) {
      return ['dataMin', 'dataMax'];
    }
    
    const values = data.map(d => d.percentage).filter(v => v != null);
    if (values.length === 0) {
      return ['dataMin', 'dataMax'];
    }
    
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min;
    
    // Add 10% padding to both ends, but ensure minimum doesn't go below 0% for percentage charts
    const padding = range * 0.1;
    const paddedMin = Math.max(0, min - padding); // Floor at 0% for percentage charts
    return [paddedMin, max + padding];
  };

  // Helper function to calculate date range from clicked data point
  const getDateRangeFromDataPoint = (monthLabel: string) => {
    console.log('Percentage chart month label received:', monthLabel); // Debug log
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
        return {
          startDate: new Date().toISOString().split('T')[0],
          endDate: new Date().toISOString().split('T')[0],
          title: `${card.title} - ${monthLabel}`,
          category: card.data.numeratorCategory,
          subcategory: card.data.numeratorSubcategory
        };
      }
      
      // Calculate start of week (Sunday)
      const startOfWeek = new Date(parsedDate);
      startOfWeek.setDate(parsedDate.getDate() - parsedDate.getDay());
      
      // Calculate end of week (Saturday)
      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 6);
      
      return {
        startDate: startOfWeek.toISOString().split('T')[0],
        endDate: endOfWeek.toISOString().split('T')[0],
        title: `${card.title} - Week of ${monthLabel}`,
        category: card.data.numeratorCategory,
        subcategory: card.data.numeratorSubcategory
      };
    } else {
      // For monthly binning, monthLabel is like "Jun 2025"
      console.log('Using monthly binning for:', monthLabel);
      const parts = monthLabel.split(' ');
      console.log('Split parts:', parts);
      
      if (parts.length !== 2) {
        console.error('Unexpected month label format:', monthLabel);
        return {
          startDate: new Date().toISOString().split('T')[0],
          endDate: new Date().toISOString().split('T')[0],
          title: `${card.title} - ${monthLabel}`,
          category: card.data.numeratorCategory,
          subcategory: card.data.numeratorSubcategory
        };
      }
      
      const monthName = parts[0];
      const year = parseInt(parts[1]);
      
      const monthIndex = new Date(`${monthName} 1, 2000`).getMonth();
      console.log('Month index for', monthName, ':', monthIndex);
      
      if (isNaN(year) || monthIndex === -1) {
        console.error('Invalid year or month:', year, monthName);
        return {
          startDate: new Date().toISOString().split('T')[0],
          endDate: new Date().toISOString().split('T')[0],
          title: `${card.title} - ${monthLabel}`,
          category: card.data.numeratorCategory,
          subcategory: card.data.numeratorSubcategory
        };
      }
      
      const startDate = new Date(year, monthIndex, 1);
      const endDate = new Date(year, monthIndex + 1, 0); // Last day of month
      
      console.log('Calculated date range:', startDate, endDate);
      
      return {
        startDate: startDate.toISOString().split('T')[0],
        endDate: endDate.toISOString().split('T')[0],
        title: `${card.title} - ${monthName} ${year}`,
        category: card.data.numeratorCategory,
        subcategory: card.data.numeratorSubcategory
      };
    }
  };

  const handleDataPointClick = (data: any, index: number) => {
    console.log('Percentage chart clicked:', data, index); // Debug log
    if (data && data.month) {
      const period = getDateRangeFromDataPoint(data.month);
      setSelectedPeriod(period);
      setModalOpen(true);
    }
  };

  const handleLineClick = (data: any, index: number, event: any) => {
    console.log('Percentage line clicked:', data, index); // Debug log
    handleDataPointClick(data, index);
  };

  const handleBarClick = (data: any, index: number, event: any) => {
    console.log('Percentage bar clicked:', data, index); // Debug log  
    handleDataPointClick(data, index);
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Get date filter from time range context
        const dateFilter = getDateFilter();
        const baseParams = new URLSearchParams({
          limit: '1000'
        });
        
        if (dateFilter.startDate) {
          baseParams.append('start_date', dateFilter.startDate);
        }
        // No end date needed - we want everything from start_date to now
        
        // Fetch numerator data (Food & Dining)
        const numeratorParams = new URLSearchParams(baseParams);
        numeratorParams.append('category', card.data.numeratorCategory || 'Food & Dining');
        if (card.data.numeratorSubcategory) {
          numeratorParams.append('subcategory', card.data.numeratorSubcategory);
        }
        
        // Fetch denominator data (Income)
        const denominatorParams = new URLSearchParams(baseParams);
        denominatorParams.append('category', card.data.denominatorCategory || 'Income');
        if (card.data.denominatorSubcategory) {
          denominatorParams.append('subcategory', card.data.denominatorSubcategory);
        }

        const [numeratorResponse, denominatorResponse] = await Promise.all([
          fetch(`/api/transactions?${numeratorParams.toString()}`),
          fetch(`/api/transactions?${denominatorParams.toString()}`)
        ]);
        
        if (!numeratorResponse.ok || !denominatorResponse.ok) {
          throw new Error('Failed to fetch transaction data');
        }

        const numeratorResult = await numeratorResponse.json();
        const denominatorResult = await denominatorResponse.json();
        
        const numeratorTransactions: Transaction[] = numeratorResult.transactions || [];
        const denominatorTransactions: Transaction[] = denominatorResult.transactions || [];
        
        // Determine binning strategy based on time range
        const useWeeklyBinning = timeRange === '1M' || timeRange === '3M';
        
        // Group numerator data (food spending)
        const numeratorGrouped = numeratorTransactions.reduce((acc, transaction) => {
          // Parse date string more explicitly to avoid timezone issues
          const dateParts = transaction.date.split('-');
          const year = parseInt(dateParts[0]);
          const month = parseInt(dateParts[1]) - 1; // month is 0-based in Date constructor
          const day = parseInt(dateParts[2]);
          const date = new Date(year, month, day);
          
          let key: string;
          let label: string;
          
          if (useWeeklyBinning) {
            const startOfWeek = new Date(date);
            startOfWeek.setDate(date.getDate() - date.getDay());
            key = `${startOfWeek.getFullYear()}-${String(startOfWeek.getMonth() + 1).padStart(2, '0')}-${String(startOfWeek.getDate()).padStart(2, '0')}`;
            label = startOfWeek.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
          } else {
            key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
            label = date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
          }
          
          if (!acc[key]) {
            acc[key] = { amount: 0, count: 0, label, sortKey: key };
          }
          
          acc[key].amount += Math.abs(transaction.amount);
          acc[key].count += 1;
          
          return acc;
        }, {} as Record<string, { amount: number; count: number; label: string; sortKey: string }>);

        // Group denominator data (income)
        const denominatorGrouped = denominatorTransactions.reduce((acc, transaction) => {
          // Parse date string more explicitly to avoid timezone issues
          const dateParts = transaction.date.split('-');
          const year = parseInt(dateParts[0]);
          const month = parseInt(dateParts[1]) - 1; // month is 0-based in Date constructor
          const day = parseInt(dateParts[2]);
          const date = new Date(year, month, day);
          
          let key: string;
          let label: string;
          
          if (useWeeklyBinning) {
            const startOfWeek = new Date(date);
            startOfWeek.setDate(date.getDate() - date.getDay());
            key = `${startOfWeek.getFullYear()}-${String(startOfWeek.getMonth() + 1).padStart(2, '0')}-${String(startOfWeek.getDate()).padStart(2, '0')}`;
            label = startOfWeek.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
          } else {
            key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
            label = date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
          }
          
          if (!acc[key]) {
            acc[key] = { amount: 0, count: 0, label, sortKey: key };
          }
          
          acc[key].amount += Math.abs(transaction.amount);
          acc[key].count += 1;
          
          return acc;
        }, {} as Record<string, { amount: number; count: number; label: string; sortKey: string }>);

        // Simple approach: just use the periods where we have data
        const allKeys = new Set([...Object.keys(numeratorGrouped), ...Object.keys(denominatorGrouped)]);
        
        if (allKeys.size === 0) {
          setData([]);
          return;
        }

        // Create chart data for periods with data
        const chartData: ChartData[] = Array.from(allKeys)
          .sort() // Sort chronologically
          .map(key => {
            const numerator = numeratorGrouped[key]?.amount || 0;
            const denominator = denominatorGrouped[key]?.amount || 0;
            const percentage = denominator > 0 ? (numerator / denominator) * 100 : 0;
            
            // Generate consistent label for this key
            let label: string;
            if (useWeeklyBinning) {
              const keyDate = new Date(key);
              label = keyDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            } else {
              // For monthly keys like "2025-07", parse explicitly
              const keyParts = key.split('-');
              const year = parseInt(keyParts[0]);
              const month = parseInt(keyParts[1]) - 1; // 0-based for Date constructor
              const keyDate = new Date(year, month, 1);
              label = keyDate.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
            }
            
            return {
              month: label,
              percentage: percentage,
              numerator: numerator,
              denominator: denominator,
              count: numeratorGrouped[key]?.count || 0
            };
          });

        // Filter out periods with no meaningful data
        const filteredData = chartData.filter(item => item.numerator > 0 || item.denominator > 0);

        setData(filteredData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load percentage data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [timeRange, card]); // Re-fetch when time range or card config changes

  const formatPercentage = (value: number) => `${value.toFixed(1)}%`;
  const formatTooltip = (value: number, name: string, props: any) => {
    if (name === 'percentage') {
      const { numerator, denominator } = props.payload;
      const numeratorLabel = card.data.numeratorSubcategory 
        ? `${card.data.numeratorCategory}/${card.data.numeratorSubcategory}`
        : card.data.numeratorCategory;
      const denominatorLabel = card.data.denominatorSubcategory
        ? `${card.data.denominatorCategory}/${card.data.denominatorSubcategory}`
        : card.data.denominatorCategory;
      return [
        `${value.toFixed(1)}%`,
        `${numeratorLabel}: $${numerator.toFixed(2)} / ${denominatorLabel}: $${denominator.toFixed(2)}`
      ];
    }
    return [value, name];
  };

  if (loading) {
    return (
      <div className="card">
        <h3 className="text-xl mb-4">{card.title}</h3>
        <div style={{ textAlign: 'center', padding: '1rem' }}>
          <p>Loading percentage data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h3 className="text-xl mb-4">{card.title}</h3>
        <div style={{ textAlign: 'center', padding: '1rem', color: '#dc2626' }}>
          <p>Error: {error}</p>
        </div>
      </div>
    );
  }

  const avgPercentage = data.reduce((sum, item) => sum + item.percentage, 0) / (data.length || 1);
  const totalNumerator = data.reduce((sum, item) => sum + item.numerator, 0);
  const totalDenominator = data.reduce((sum, item) => sum + item.denominator, 0);
  const overallPercentage = totalDenominator > 0 ? (totalNumerator / totalDenominator) * 100 : 0;
  const useWeeklyBinning = timeRange === '1M' || timeRange === '3M';

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <h3 className="text-xl">{card.title}</h3>
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
                backgroundColor: chartType === 'line' ? card.config?.color : 'white',
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
                backgroundColor: chartType === 'bar' ? card.config?.color : 'white',
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
        <p><strong>Overall:</strong> {overallPercentage.toFixed(1)}%</p>
        <p><strong>Average {useWeeklyBinning ? 'Weekly' : 'Monthly'}:</strong> {avgPercentage.toFixed(1)}%</p>
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
              />
              <YAxis 
                tickFormatter={formatPercentage}
                domain={getYAxisDomain(data)}
              />
              <Tooltip formatter={formatTooltip} />
              <Line 
                type="monotone" 
                dataKey="percentage" 
                stroke={card.config?.color || '#8884d8'} 
                strokeWidth={2}
                dot={{ fill: card.config?.color || '#8884d8', strokeWidth: 2, r: 4, cursor: 'pointer' }}
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
              />
              <YAxis 
                tickFormatter={formatPercentage}
                domain={getYAxisDomain(data)}
              />
              <Tooltip formatter={formatTooltip} />
              <Bar dataKey="percentage" fill={card.config?.color || '#8884d8'} style={{ cursor: 'pointer' }} onClick={handleBarClick} animationDuration={200} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
      
      {/* Transaction Modal */}
      <TransactionModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        category={selectedPeriod?.category}
        subcategory={selectedPeriod?.subcategory}
        startDate={selectedPeriod?.startDate}
        endDate={selectedPeriod?.endDate}
        title={selectedPeriod?.title}
      />
    </div>
  );
};