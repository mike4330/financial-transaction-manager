import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { useTimeRange } from '../contexts/TimeRangeContext';

interface Transaction {
  id: number;
  date: string;
  amount: number;
  description: string;
  payee: string;
}

interface ChartData {
  month: string;
  amount: number;
  count: number;
}

export const FastFoodChart: React.FC = () => {
  const [data, setData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartType, setChartType] = useState<'line' | 'bar'>('line');
  const { timeRange, getDateFilter } = useTimeRange();

  useEffect(() => {
    const fetchFastFoodData = async () => {
      try {
        setLoading(true);
        
        // Get date filter from time range context
        const dateFilter = getDateFilter();
        const params = new URLSearchParams({
          category: 'Food & Dining',
          subcategory: 'Fast Food',
          limit: '1000'
        });
        
        if (dateFilter.startDate) {
          params.append('start_date', dateFilter.startDate);
        }
        if (dateFilter.endDate) {
          params.append('end_date', dateFilter.endDate);
        }
        
        // Fetch filtered fast food transactions
        const response = await fetch(`/api/transactions?${params.toString()}`);
        const result = await response.json();
        
        if (!response.ok) {
          throw new Error('Failed to fetch fast food data');
        }

        const transactions: Transaction[] = result.transactions || [];
        
        // Determine binning strategy based on time range
        const useWeeklyBinning = timeRange === '1M' || timeRange === '3M';
        
        // Group by appropriate time period and calculate totals
        const groupedData = transactions.reduce((acc, transaction) => {
          const date = new Date(transaction.date);
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
        setError(err instanceof Error ? err.message : 'Failed to load fast food data');
      } finally {
        setLoading(false);
      }
    };

    fetchFastFoodData();
  }, [timeRange]); // Re-fetch when time range changes

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
        <h3 className="text-xl mb-4">🍔 Fast Food Spending Over Time</h3>
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <p>Loading fast food data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <h3 className="text-xl mb-4">🍔 Fast Food Spending Over Time</h3>
        <div style={{ textAlign: 'center', padding: '2rem', color: '#dc2626' }}>
          <p>Error: {error}</p>
        </div>
      </div>
    );
  }

  const totalSpent = data.reduce((sum, item) => sum + item.amount, 0);
  const avgMonthly = totalSpent / data.length;

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 className="text-xl">🍔 Fast Food Spending Over Time</h3>
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
              backgroundColor: chartType === 'line' ? '#3b82f6' : 'white',
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
              backgroundColor: chartType === 'bar' ? '#3b82f6' : 'white',
              color: chartType === 'bar' ? 'white' : 'black',
              cursor: 'pointer'
            }}
          >
            Bar
          </button>
          </div>
        </div>
      </div>

      <div className="space-y-2" style={{ marginBottom: '1.5rem' }}>
        <p><strong>Total Spent:</strong> ${totalSpent.toFixed(2)}</p>
        <p><strong>Average Monthly:</strong> ${avgMonthly.toFixed(2)}</p>
        <p><strong>Months Tracked:</strong> {data.length}</p>
      </div>

      <div style={{ width: '100%', height: '400px' }}>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'line' ? (
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="month" 
                angle={-45}
                textAnchor="end"
                height={80}
                fontSize={12}
              />
              <YAxis tickFormatter={formatCurrency} />
              <Tooltip formatter={formatTooltip} />
              <Line 
                type="monotone" 
                dataKey="amount" 
                stroke="#dc2626" 
                strokeWidth={2}
                dot={{ fill: '#dc2626', strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          ) : (
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="month" 
                angle={-45}
                textAnchor="end"
                height={80}
                fontSize={12}
              />
              <YAxis tickFormatter={formatCurrency} />
              <Tooltip formatter={formatTooltip} />
              <Bar dataKey="amount" fill="#dc2626" />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
      
      {data.length > 0 && (
        <div style={{ marginTop: '1rem', fontSize: '0.875rem', color: '#666' }}>
          <p>Showing fast food spending from {data[0]?.month} to {data[data.length - 1]?.month}</p>
        </div>
      )}
    </div>
  );
};