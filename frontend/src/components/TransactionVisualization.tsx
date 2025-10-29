import React, { useState, useEffect, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { useTimeRange } from '../contexts/TimeRangeContext';
import { useTheme } from '../contexts/ThemeContext';
import { getChartTheme, getGridProps, getAxisProps, getTooltipProps } from '../styles/chartTheme';

interface Category {
  id: number;
  name: string;
}

interface Subcategory {
  id: number;
  name: string;
  category_id: number;
  category_name: string;
}

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

const TransactionVisualization: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [subcategories, setSubcategories] = useState<Subcategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedSubcategory, setSelectedSubcategory] = useState<string>('');
  const [data, setData] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartType, setChartType] = useState<'line' | 'bar'>('bar');
  
  const { timeRange, getDateFilter, startFromZero } = useTimeRange();
  const { isDarkMode } = useTheme();

  // Get consistent chart theme from centralized theme system
  const chartTheme = useMemo(() => getChartTheme(isDarkMode), [isDarkMode]);
  const gridProps = useMemo(() => getGridProps(isDarkMode), [isDarkMode]);
  const axisProps = useMemo(() => getAxisProps(isDarkMode), [isDarkMode]);
  const tooltipProps = useMemo(() => getTooltipProps(isDarkMode), [isDarkMode]);

  // Helper function to calculate Y-axis domain with padding for non-zero mode
  const getYAxisDomain = (data: ChartData[]) => {
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

  // Filter subcategories based on selected category
  const filteredSubcategories = useMemo(() => {
    if (!selectedCategory) return [];
    return subcategories.filter(sub => 
      selectedCategory === 'all' || sub.category_name === selectedCategory
    );
  }, [subcategories, selectedCategory]);

  // Load categories and subcategories on mount
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await fetch('/api/categories');
        const result = await response.json();
        
        if (!response.ok) {
          throw new Error('Failed to fetch categories');
        }

        setCategories(result.categories || []);
        setSubcategories(result.subcategories || []);
      } catch (err) {
        console.error('Error fetching categories:', err);
        setError('Failed to load categories');
      }
    };

    fetchCategories();
  }, []);

  // Fetch transaction data when filters change
  useEffect(() => {
    const fetchTransactionData = async () => {
      if (!selectedCategory) {
        setData([]);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        
        // Get date filter from time range context
        const dateFilter = getDateFilter();
        
        // Build API URL with filters
        const params = new URLSearchParams({
          limit: '5000'
        });
        
        if (dateFilter.startDate) {
          params.append('start_date', dateFilter.startDate);
        }
        
        if (selectedCategory !== 'all') {
          params.append('category', selectedCategory);
        }
        
        if (selectedSubcategory && selectedSubcategory !== 'all') {
          params.append('subcategory', selectedSubcategory);
        }
        
        const apiUrl = `/api/transactions?${params.toString()}`;
        
        // Fetch filtered transactions
        const response = await fetch(apiUrl);
        const result = await response.json();
        
        if (!response.ok) {
          throw new Error('Failed to fetch transaction data');
        }

        let transactions: Transaction[] = result.transactions || [];
        
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
          
          acc[key].amount += Math.abs(transaction.amount);
          acc[key].count += 1;
          
          return acc;
        }, {} as Record<string, ChartData & { sortKey: string }>);

        // Convert to array and sort by date
        const chartData = Object.values(groupedData)
          .sort((a, b) => a.sortKey.localeCompare(b.sortKey))
          .map(({ sortKey, ...data }) => data);

        setData(chartData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load transaction data');
      } finally {
        setLoading(false);
      }
    };

    fetchTransactionData();
  }, [timeRange, selectedCategory, selectedSubcategory, getDateFilter]);

  const formatCurrency = (value: number) => `$${value.toFixed(0)}`;
  const formatTooltip = (value: number, name: string) => {
    if (name === 'amount') {
      return [`$${value.toFixed(2)}`, 'Total'];
    }
    return [value, 'Transactions'];
  };

  const totalSpent = data.reduce((sum, item) => sum + item.amount, 0);
  const avgPeriod = totalSpent / (data.length || 1);
  const useWeeklyBinning = timeRange === '1M' || timeRange === '3M';

  const getChartTitle = () => {
    if (!selectedCategory) return 'Select a category to view data';
    if (selectedCategory === 'all') return 'All Categories';
    if (selectedSubcategory && selectedSubcategory !== 'all') {
      return `${selectedCategory} - ${selectedSubcategory}`;
    }
    return selectedCategory;
  };

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="text-2xl font-bold mb-6 text-gray-900 dark:text-ember-100">
          💰 Transaction Visualization
        </h2>
        
        {/* Category and Subcategory Dropdowns */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <label htmlFor="category-select" className="block text-sm font-medium text-gray-700 dark:text-warm-300 mb-2">
              Category
            </label>
            <select
              id="category-select"
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setSelectedSubcategory(''); // Reset subcategory when category changes
              }}
              className="w-full p-2 border border-gray-300 dark:border-dark-border rounded-lg bg-white dark:bg-dark-card text-gray-900 dark:text-ember-100 focus:ring-2 focus:ring-ember-500 focus:border-transparent"
            >
              <option value="">Select a category...</option>
              <option value="all">All Categories</option>
              {categories.map(category => (
                <option key={category.id} value={category.name}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="subcategory-select" className="block text-sm font-medium text-gray-700 dark:text-warm-300 mb-2">
              Subcategory
            </label>
            <select
              id="subcategory-select"
              value={selectedSubcategory}
              onChange={(e) => setSelectedSubcategory(e.target.value)}
              disabled={!selectedCategory || selectedCategory === 'all'}
              className="w-full p-2 border border-gray-300 dark:border-dark-border rounded-lg bg-white dark:bg-dark-card text-gray-900 dark:text-ember-100 focus:ring-2 focus:ring-ember-500 focus:border-transparent disabled:bg-gray-100 dark:disabled:bg-dark-bg disabled:text-gray-500"
            >
              <option value="">All subcategories</option>
              <option value="all">All subcategories</option>
              {filteredSubcategories.map(subcategory => (
                <option key={subcategory.id} value={subcategory.name}>
                  {subcategory.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Chart Section */}
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-ember-100">
            {getChartTitle()}
          </h3>
          
          {selectedCategory && (
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600 dark:text-warm-400">
                {timeRange === 'ALL' ? 'All Time' : timeRange}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setChartType('line')}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                    chartType === 'line'
                      ? 'bg-ember-500 text-white shadow-ember-glow'
                      : 'bg-gray-200 dark:bg-dark-card text-gray-700 dark:text-warm-300 hover:bg-gray-300 dark:hover:bg-dark-border'
                  }`}
                >
                  Line
                </button>
                <button
                  onClick={() => setChartType('bar')}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                    chartType === 'bar'
                      ? 'bg-ember-500 text-white shadow-ember-glow'
                      : 'bg-gray-200 dark:bg-dark-card text-gray-700 dark:text-warm-300 hover:bg-gray-300 dark:hover:bg-dark-border'
                  }`}
                >
                  Bar
                </button>
              </div>
            </div>
          )}
        </div>

        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-ember-500"></div>
            <p className="mt-2 text-gray-600 dark:text-warm-400">Loading data...</p>
          </div>
        )}

        {error && (
          <div className="text-center py-12">
            <p className="text-red-600 dark:text-red-400">Error: {error}</p>
          </div>
        )}

        {!loading && !error && selectedCategory && data.length > 0 && (
          <>
            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 dark:bg-dark-bg rounded-lg">
              <div className="text-center">
                <p className="text-sm text-gray-600 dark:text-warm-400">Total Amount</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-ember-100">
                  ${totalSpent.toFixed(2)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-600 dark:text-warm-400">
                  Average {useWeeklyBinning ? 'Weekly' : 'Monthly'}
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-ember-100">
                  ${avgPeriod.toFixed(2)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-600 dark:text-warm-400">Total Transactions</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-ember-100">
                  {data.reduce((sum, item) => sum + item.count, 0)}
                </p>
              </div>
            </div>

            {/* Chart */}
            <div style={{ width: '100%', height: '450px' }}>
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
                      stroke="#f97316" 
                      strokeWidth={3}
                      dot={{ fill: '#f97316', strokeWidth: 2, r: 4 }}
                      activeDot={{ r: 6 }}
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
                    <Bar dataKey="amount" fill="#f97316" fillOpacity={0.7} animationDuration={200} />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>
          </>
        )}

        {!loading && !error && selectedCategory && data.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-600 dark:text-warm-400">
              No transactions found for the selected filters and time range.
            </p>
          </div>
        )}

        {!selectedCategory && !loading && (
          <div className="text-center py-12">
            <p className="text-gray-600 dark:text-warm-400">
              Select a category above to view transaction data over time.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default TransactionVisualization;