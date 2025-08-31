import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import styles from './Budget.module.css';
import { TransactionModal } from './TransactionModal';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import Dialog from './Dialog';
import ConfirmDialog from './ConfirmDialog';

interface BudgetItem {
  id: string;
  category: string;
  subcategory?: string;
  budgeted: number;
  actual: number;
  expected?: number; // Expected amount from recurring patterns
  type: 'expense' | 'income';
}

interface PatternProjection {
  category: string;
  subcategory?: string;
  income_projected: number;
  expense_projected: number;
  patterns: Array<{
    pattern_name: string;
    payee: string;
    amount: number;
    type: 'income' | 'expense';
    frequency: string;
    occurrences: number;
  }>;
}

interface BudgetTotals {
  income: { budgeted: number; actual: number };
  expenses: { budgeted: number; actual: number };
  net: { budgeted: number; actual: number };
}

interface BudgetInfo {
  id: number;
  year: number;
  month: number;
  status: string;
  created_at: string;
}

interface CategorySpending {
  category: string;
  amount: number;
  percentage: number;
  transaction_count: number;
}

interface SpendingData {
  year: number;
  month: number;
  categories: CategorySpending[];
  total_spending: number;
}

interface UnbudgetedData {
  year: number;
  month: number;
  categories: CategorySpending[];
  total_unbudgeted: number;
  count: number;
}

const Budget: React.FC = () => {
  const params = useParams<{ year?: string; month?: string }>();
  const navigate = useNavigate();
  const [budgetItems, setBudgetItems] = useState<BudgetItem[]>([]);
  const [totals, setTotals] = useState<BudgetTotals | null>(null);
  const [budgetInfo, setBudgetInfo] = useState<BudgetInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [availableMonths, setAvailableMonths] = useState<{year: number, month: number}[]>([]);
  const [currentBudgetIndex, setCurrentBudgetIndex] = useState<number>(0);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<{
    category: string;
    subcategory: string;
    startDate: string;
    endDate: string;
    title: string;
  } | null>(null);
  const [spendingData, setSpendingData] = useState<SpendingData | null>(null);
  const [unbudgetedData, setUnbudgetedData] = useState<UnbudgetedData | null>(null);
  const [addingCategory, setAddingCategory] = useState<string | null>(null);
  const [dialog, setDialog] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    type: 'success' | 'error' | 'warning' | 'info';
  }>({ isOpen: false, title: '', message: '', type: 'info' });
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    details?: string[];
    onConfirm: () => void;
    type: 'success' | 'error' | 'warning' | 'info';
  }>({ isOpen: false, title: '', message: '', onConfirm: () => {}, type: 'info' });
  const [patternProjections, setPatternProjections] = useState<PatternProjection[]>([]);

  useEffect(() => {
    const fetchAvailableMonths = async () => {
      try {
        const response = await fetch('/api/budget/available-months');
        if (response.ok) {
          const data = await response.json();
          const months = data.available_months || [];
          setAvailableMonths(months);
          
          // Find the current month's budget
          const now = new Date();
          const currentYear = now.getFullYear();
          const currentMonth = now.getMonth() + 1; // getMonth() returns 0-11, but we need 1-12
          
          const currentMonthIndex = months.findIndex(
            (month: {year: number, month: number}) => 
              month.year === currentYear && month.month === currentMonth
          );
          
          // Use current month if available, otherwise use the most recent (index 0)
          setCurrentBudgetIndex(currentMonthIndex >= 0 ? currentMonthIndex : 0);
        }
      } catch (err) {
        console.error('Error fetching available months:', err);
      }
    };

    fetchAvailableMonths();
  }, []);

  useEffect(() => {
    const fetchBudgetData = async () => {
      if (availableMonths.length === 0) return;
      
      try {
        setLoading(true);
        setError(null);
        
        // Get current budget year/month from available months
        const currentBudget = availableMonths[currentBudgetIndex];
        if (!currentBudget) return;

        const response = await fetch(`/api/budget/${currentBudget.year}/${currentBudget.month}`);
        
        if (!response.ok) {
          throw new Error('Failed to fetch budget data');
        }
        
        const data = await response.json();
        setBudgetItems(data.items || []);
        setTotals(data.totals || null);
        setBudgetInfo(data.budget || null);
        
        // Fetch spending data for pie chart
        const spendingResponse = await fetch(`/api/budget/${currentBudget.year}/${currentBudget.month}/spending-by-category`);
        if (spendingResponse.ok) {
          const spendingData = await spendingResponse.json();
          setSpendingData(spendingData);
        }
        
        // Fetch unbudgeted categories data
        const unbudgetedResponse = await fetch(`/api/budget/${currentBudget.year}/${currentBudget.month}/unbudgeted-categories`);
        if (unbudgetedResponse.ok) {
          const unbudgetedData = await unbudgetedResponse.json();
          setUnbudgetedData(unbudgetedData);
        }

        // Fetch pattern projections
        const patternResponse = await fetch(`/api/monthly-pattern-projections?year=${currentBudget.year}&month=${currentBudget.month}`);
        if (patternResponse.ok) {
          const patternData = await patternResponse.json();
          setPatternProjections(patternData.category_projections || []);
        }
        
      } catch (err) {
        console.error('Error fetching budget data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load budget data');
      } finally {
        setLoading(false);
      }
    };

    fetchBudgetData();
  }, [availableMonths, currentBudgetIndex]);

  // Merge pattern projections with budget items
  const getBudgetItemsWithProjections = (): BudgetItem[] => {
    return budgetItems.map(item => {
      // Find matching pattern projection
      const projection = patternProjections.find(p => 
        p.category === item.category && 
        (p.subcategory === item.subcategory || (!p.subcategory && !item.subcategory))
      );
      
      if (projection) {
        const expectedAmount = item.type === 'income' ? projection.income_projected : projection.expense_projected;
        return { ...item, expected: expectedAmount };
      }
      
      return item;
    });
  };

  // Refresh all budget data from server
  const refreshBudgetData = async () => {
    if (availableMonths.length === 0) return;
    
    try {
      const currentBudget = availableMonths[currentBudgetIndex];
      if (!currentBudget) return;

      // Refresh budget items and totals
      const response = await fetch(`/api/budget/${currentBudget.year}/${currentBudget.month}`);
      if (response.ok) {
        const data = await response.json();
        setBudgetItems(data.items || []);
        setTotals(data.totals || null);
        setBudgetInfo(data.budget || null);
      }
      
      // Refresh spending data for pie chart
      const spendingResponse = await fetch(`/api/budget/${currentBudget.year}/${currentBudget.month}/spending-by-category`);
      if (spendingResponse.ok) {
        const spendingData = await spendingResponse.json();
        setSpendingData(spendingData);
      }
      
      // Refresh unbudgeted categories data
      const unbudgetedResponse = await fetch(`/api/budget/${currentBudget.year}/${currentBudget.month}/unbudgeted-categories`);
      if (unbudgetedResponse.ok) {
        const unbudgetedData = await unbudgetedResponse.json();
        setUnbudgetedData(unbudgetedData);
      }

      // Refresh pattern projections
      const patternResponse = await fetch(`/api/monthly-pattern-projections?year=${currentBudget.year}&month=${currentBudget.month}`);
      if (patternResponse.ok) {
        const patternData = await patternResponse.json();
        setPatternProjections(patternData.category_projections || []);
      }
    } catch (err) {
      console.error('Error refreshing budget data:', err);
    }
  };

  // Dialog helper functions
  const showDialog = (title: string, message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info') => {
    setDialog({ isOpen: true, title, message, type });
  };

  const showConfirmDialog = (
    title: string, 
    message: string, 
    onConfirm: () => void, 
    type: 'success' | 'error' | 'warning' | 'info' = 'warning',
    details?: string[]
  ) => {
    setConfirmDialog({ isOpen: true, title, message, onConfirm, type, details });
  };

  // Function to add unbudgeted category to budget
  const addCategoryToBudget = async (categoryName: string) => {
    if (!budgetInfo) return;
    
    try {
      setAddingCategory(categoryName);
      
      const response = await fetch(`/api/budget/${budgetInfo.year}/${budgetInfo.month}/add-category`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: categoryName,
          budgeted_amount: 0.0,  // Start with $0, user can edit later
          budget_type: 'expense'
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to add category to budget');
      }

      const result = await response.json();
      
      // Refresh budget data to show the new item
      const currentBudget = availableMonths[currentBudgetIndex];
      if (currentBudget) {
        // Refresh budget items
        const budgetResponse = await fetch(`/api/budget/${currentBudget.year}/${currentBudget.month}`);
        if (budgetResponse.ok) {
          const data = await budgetResponse.json();
          setBudgetItems(data.items || []);
          setTotals(data.totals || null);
        }
        
        // Refresh unbudgeted categories
        const unbudgetedResponse = await fetch(`/api/budget/${currentBudget.year}/${currentBudget.month}/unbudgeted-categories`);
        if (unbudgetedResponse.ok) {
          const unbudgetedData = await unbudgetedResponse.json();
          setUnbudgetedData(unbudgetedData);
        }
      }
      
      // Show success message
      showDialog(
        'Category Added',
        `Successfully added "${categoryName}" to budget. You can now set a budget amount.`,
        'success'
      );
      
    } catch (err) {
      console.error('Error adding category to budget:', err);
      showDialog(
        'Error Adding Category',
        `Failed to add category to budget: ${err instanceof Error ? err.message : 'Unknown error'}`,
        'error'
      );
    } finally {
      setAddingCategory(null);
    }
  };

  // Format month/year for display
  const formatBudgetPeriod = (budgetInfo: BudgetInfo | null): string => {
    if (!budgetInfo) return 'Loading...';
    
    const monthNames = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    
    const monthName = monthNames[budgetInfo.month - 1];
    return `${monthName} ${budgetInfo.year}`;
  };

  // Budget editing functions
  const startEditing = (itemId: string, currentAmount: number) => {
    setEditingItem(itemId);
    setEditValue(currentAmount.toString());
  };

  const cancelEditing = () => {
    setEditingItem(null);
    setEditValue('');
  };

  const acceptEdit = async (itemId: string) => {
    const newAmount = parseFloat(editValue);
    if (isNaN(newAmount) || newAmount < 0) {
      showDialog('Invalid Amount', 'Please enter a valid positive number', 'warning');
      return;
    }

    try {
      // API call to update budget item
      const response = await fetch(`/api/budget/items/${itemId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ budgeted_amount: newAmount })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update budget item');
      }

      // Refresh all budget data from server to ensure consistency
      await refreshBudgetData();

      cancelEditing();
    } catch (err) {
      console.error('Error updating budget item:', err);
      showDialog(
        'Update Failed',
        `Failed to update budget item: ${err instanceof Error ? err.message : 'Unknown error'}`,
        'error'
      );
    }
  };

  const handleAutoUpdate = async (itemId: string) => {
    try {
      // Get historical average calculation
      const response = await fetch(`/api/budget/items/${itemId}/auto-calculate`);
      
      if (!response.ok) {
        const errorData = await response.json();
        if (response.status === 400) {
          showDialog(
            'Auto-calculation Not Available',
            errorData.message || 'Insufficient historical data for auto-calculation',
            'warning'
          );
        } else {
          throw new Error(errorData.error || 'Failed to calculate auto amount');
        }
        return;
      }

      const data = await response.json();
      const suggestedAmount = data.suggested_amount;
      const analysis = data.analysis;
      
      // Show confirmation dialog with analysis
      const details = [
        `Based on ${analysis.months_used} months of data`,
        `Confidence: ${(data.confidence * 100).toFixed(0)}% (${analysis.confidence_description})`,
        `Median spending: $${analysis.median.toLocaleString()}`,
        ...(analysis.outliers_removed > 0 ? [`Removed ${analysis.outliers_removed} outlier month(s)`] : [])
      ];

      showConfirmDialog(
        'Auto-calculated Amount',
        `Set budget to $${suggestedAmount.toLocaleString()}?`,
        async () => {
        // Update the edit value and trigger accept
        setEditValue(suggestedAmount.toString());
        
        // Auto-apply the calculated amount
        const updateResponse = await fetch(`/api/budget/items/${itemId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ budgeted_amount: suggestedAmount })
        });

        if (!updateResponse.ok) {
          const errorData = await updateResponse.json();
          throw new Error(errorData.error || 'Failed to update budget item');
        }

        // Refresh all budget data from server to ensure consistency
        await refreshBudgetData();

        cancelEditing();
        },
        'info',
        details
      );
    } catch (err) {
      console.error('Error with auto-update:', err);
      showDialog(
        'Auto-update Failed',
        `Auto-update failed: ${err instanceof Error ? err.message : 'Unknown error'}`,
        'error'
      );
    }
  };

  // Progress bar click handler for drilldown
  const handleProgressBarClick = (item: BudgetItem) => {
    if (!budgetInfo) return;
    
    // Calculate date range for the current budget month
    const year = budgetInfo.year;
    const month = budgetInfo.month;
    
    const startDate = new Date(year, month - 1, 1); // month - 1 because Date month is 0-based
    const endDate = new Date(year, month, 0); // Last day of the month
    
    const monthNames = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    
    const monthName = monthNames[month - 1];
    
    setSelectedCategory({
      category: item.category,
      subcategory: item.subcategory || '',
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0],
      title: `${item.category}${item.subcategory ? ` - ${item.subcategory}` : ''} - ${monthName} ${year}`
    });
    setModalOpen(true);
  };

  // Navigation functions
  const navigateToPrevious = () => {
    if (currentBudgetIndex < availableMonths.length - 1) {
      const previousMonth = availableMonths[currentBudgetIndex + 1];
      navigate(`/budget/${previousMonth.year}/${previousMonth.month}`);
      setCurrentBudgetIndex(currentBudgetIndex + 1);
    }
  };

  const navigateToNext = () => {
    if (currentBudgetIndex > 0) {
      const nextMonth = availableMonths[currentBudgetIndex - 1];
      navigate(`/budget/${nextMonth.year}/${nextMonth.month}`);
      setCurrentBudgetIndex(currentBudgetIndex - 1);
    }
  };

  // Create next month's budget
  const createNextMonthBudget = async () => {
    try {
      const response = await fetch('/api/budget/create-next-month', {
        method: 'POST'
      });

      if (!response.ok) {
        const errorData = await response.json();
        if (response.status === 400) {
          showDialog(
            'Budget Already Exists',
            errorData.message || 'Budget already exists for next month',
            'warning'
          );
        } else {
          throw new Error(errorData.error || 'Failed to create next month budget');
        }
        return;
      }

      const data = await response.json();
      showDialog(
        'Budget Created',
        `Successfully created budget for ${data.year}-${data.month.toString().padStart(2, '0')}`,
        'success'
      );
      
      // Refresh available months and navigate to the new budget
      const monthsResponse = await fetch('/api/budget/available-months');
      if (monthsResponse.ok) {
        const monthsData = await monthsResponse.json();
        setAvailableMonths(monthsData.available_months || []);
        setCurrentBudgetIndex(0); // Navigate to the newest budget
      }
    } catch (err) {
      console.error('Error creating next month budget:', err);
      showDialog(
        'Budget Creation Failed',
        `Failed to create next month budget: ${err instanceof Error ? err.message : 'Unknown error'}`,
        'error'
      );
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h2 className={styles.title}>💰 Monthly Budget - {formatBudgetPeriod(budgetInfo)}</h2>
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <p>Loading budget data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h2 className={styles.title}>💰 Monthly Budget - {formatBudgetPeriod(budgetInfo)}</h2>
          <div style={{ textAlign: 'center', padding: '2rem', color: '#dc2626' }}>
            <p>Error: {error}</p>
            <p>Please check the API connection.</p>
          </div>
        </div>
      </div>
    );
  }

  // If no budget items loaded, show empty state
  if (budgetItems.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h2 className={styles.title}>💰 Monthly Budget - {formatBudgetPeriod(budgetInfo)}</h2>
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <p>No budget data available for {formatBudgetPeriod(budgetInfo)}.</p>
            <p>Please create a budget or check the API connection.</p>
          </div>
        </div>
      </div>
    );
  }

  const calculateProgress = (actual: number, budgeted: number, type: 'expense' | 'income'): number => {
    if (budgeted === 0) return 0;
    
    if (type === 'income') {
      // For income, higher actual is better
      return Math.min((actual / budgeted) * 100, 100);
    } else {
      // For expenses, lower actual is better, but show actual usage
      return (actual / budgeted) * 100;
    }
  };

  const getProgressColor = (actual: number, budgeted: number, type: 'expense' | 'income'): string => {
    const percentage = (actual / budgeted) * 100;
    
    if (type === 'income') {
      if (percentage >= 100) return '#10b981'; // green - income target met
      if (percentage >= 80) return '#f59e0b'; // yellow - close to target
      return '#ef4444'; // red - income shortfall
    } else {
      if (percentage <= 80) return '#10b981'; // green - well under budget
      if (percentage <= 100) return '#f59e0b'; // yellow - close to budget
      return '#ef4444'; // red - over budget
    }
  };

  const getVarianceText = (actual: number, budgeted: number, type: 'expense' | 'income'): string => {
    const difference = actual - budgeted;
    const percentage = budgeted > 0 ? (difference / budgeted) * 100 : 0;
    
    if (type === 'income') {
      if (difference >= 0) {
        return `+$${difference.toFixed(0)} (${percentage.toFixed(0)}% over target)`;
      } else {
        return `-$${Math.abs(difference).toFixed(0)} (${Math.abs(percentage).toFixed(0)}% under target)`;
      }
    } else {
      if (difference > 0) {
        return `+$${difference.toFixed(0)} over (${percentage.toFixed(0)}%)`;
      } else if (difference < 0) {
        return `$${Math.abs(difference).toFixed(0)} under (${Math.abs(percentage).toFixed(0)}%)`;
      } else {
        return 'On budget';
      }
    }
  };

  // Get budget items with pattern projections
  const budgetItemsWithProjections = getBudgetItemsWithProjections();

  // Calculate totals including expected amounts from recurring patterns
  const totalBudgetedExpenses = totals?.expenses.budgeted ?? budgetItemsWithProjections.filter(item => item.type === 'expense').reduce((sum, item) => sum + item.budgeted, 0);
  const totalActualExpenses = totals?.expenses.actual ?? budgetItemsWithProjections.filter(item => item.type === 'expense').reduce((sum, item) => sum + item.actual, 0);
  const totalExpectedExpenses = budgetItemsWithProjections.filter(item => item.type === 'expense').reduce((sum, item) => sum + (item.expected || 0), 0);

  const totalBudgetedIncome = totals?.income.budgeted ?? budgetItemsWithProjections.filter(item => item.type === 'income').reduce((sum, item) => sum + item.budgeted, 0);
  const totalActualIncome = totals?.income.actual ?? budgetItemsWithProjections.filter(item => item.type === 'income').reduce((sum, item) => sum + item.actual, 0);
  const totalExpectedIncome = budgetItemsWithProjections.filter(item => item.type === 'income').reduce((sum, item) => sum + (item.expected || 0), 0);
  
  // Use the higher of actual vs expected for display (don't double-count)
  const totalDisplayIncome = Math.max(totalActualIncome, totalExpectedIncome);
  const totalDisplayExpenses = Math.max(totalActualExpenses, totalExpectedExpenses);
  
  // Group items by category
  const groupedByCategory = budgetItemsWithProjections.reduce((acc, item) => {
    if (!acc[item.category]) {
      acc[item.category] = [];
    }
    acc[item.category].push(item);
    return acc;
  }, {} as Record<string, BudgetItem[]>);

  // Separate income and expense categories
  const incomeCategories = Object.keys(groupedByCategory).filter(category => 
    groupedByCategory[category].some(item => item.type === 'income')
  );
  const expenseCategories = Object.keys(groupedByCategory).filter(category => 
    groupedByCategory[category].some(item => item.type === 'expense')
  );

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.titleSection}>
          <div className={styles.navigation}>
            <button 
              onClick={navigateToPrevious}
              disabled={currentBudgetIndex >= availableMonths.length - 1}
              className={styles.navButton}
              title="Previous month"
            >
              ◀
            </button>
            <h2 className={styles.title}>💰 Monthly Budget - {formatBudgetPeriod(budgetInfo)}</h2>
            <button 
              onClick={navigateToNext}
              disabled={currentBudgetIndex <= 0}
              className={styles.navButton}
              title="Next month"
            >
              ▶
            </button>
          </div>
          <button 
            onClick={createNextMonthBudget}
            className={styles.createButton}
            title="Create budget for next month"
          >
            📅 Create Next Month
          </button>
        </div>
        <div className={styles.summary}>
          <div className={styles.summaryCard}>
            <h3>Income</h3>
            <div className={styles.summaryAmount}>
              <span className={styles.actualAmount}>
                ${totalDisplayIncome.toLocaleString()}
              </span>
            </div>
            <div className={styles.summarySubtext}>
              Budget: ${totalBudgetedIncome.toLocaleString()}
            </div>
          </div>
          <div className={styles.summaryCard}>
            <h3>Expenses</h3>
            <div className={styles.summaryAmount}>
              <span className={styles.actualAmount}>
                ${totalDisplayExpenses.toLocaleString()}
              </span>
            </div>
            <div className={styles.summarySubtext}>
              Budget: ${totalBudgetedExpenses.toLocaleString()}
            </div>
          </div>
          <div className={styles.summaryCard}>
            <h3>Net</h3>
            <div className={styles.summaryAmount}>
              <span className={`${styles.actualAmount} ${(totalDisplayIncome - totalDisplayExpenses) >= 0 ? styles.positive : styles.negative}`}>
                ${(totalDisplayIncome - totalDisplayExpenses).toLocaleString()}
              </span>
            </div>
            <div className={styles.summarySubtext}>
              Budget: ${(totalBudgetedIncome - totalBudgetedExpenses).toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className={styles.chartsRow}>
        {/* Spending by Category Pie Chart */}
        {spendingData && spendingData.categories.length > 0 && (
          <div className={styles.pieChartSection}>
            <h3 className={styles.chartTitle}>Spending by Category</h3>
            <div className={styles.pieChartContainer}>
              <div className={styles.pieChartWrapper}>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={spendingData.categories.slice(0, 8).map(category => ({
                        name: category.category,
                        value: category.amount,
                        percentage: category.percentage,
                        count: category.transaction_count
                      }))}
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      innerRadius={0}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {spendingData.categories.slice(0, 8).map((entry, index) => {
                        const colors = [
                          '#3b82f6', '#ef4444', '#10b981', '#f59e0b', 
                          '#8b5cf6', '#f97316', '#06b6d4', '#84cc16'
                        ];
                        return <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />;
                      })}
                    </Pie>
                    <Tooltip 
                      formatter={(value: number, name: string, props: any) => [
                        `$${value.toLocaleString()}`,
                        name,
                        `${props.payload.percentage.toFixed(1)}% (${props.payload.count} transactions)`
                      ]}
                      labelFormatter={(label) => `${label}`}
                    />
                    <Legend 
                      verticalAlign="bottom" 
                      height={60}
                      layout="horizontal"
                      wrapperStyle={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        justifyContent: 'center',
                        gap: '16px',
                        paddingTop: '16px'
                      }}
                      formatter={(value, entry) => `${value} ($${entry.payload?.value?.toLocaleString()})`}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* Unbudgeted Categories */}
        {unbudgetedData && (
          <div className={styles.unbudgetedSection}>
            <h3 className={styles.chartTitle}>Unbudgeted Categories</h3>
            <div className={styles.unbudgetedContainer}>
              {unbudgetedData.categories.length === 0 ? (
                <div className={styles.emptyState}>
                  <p className={styles.emptyMessage}>✅ All spending categories are budgeted!</p>
                </div>
              ) : (
                <>
                  <div className={styles.unbudgetedSummary}>
                    <div className={styles.totalUnbudgeted}>
                      <span className={styles.amount}>${unbudgetedData.total_unbudgeted.toLocaleString()}</span>
                      <span className={styles.label}>Total Unbudgeted</span>
                    </div>
                    <div className={styles.categoryCount}>
                      <span className={styles.count}>{unbudgetedData.count}</span>
                      <span className={styles.label}>Categories</span>
                    </div>
                  </div>
                  <div className={styles.unbudgetedList}>
                    {unbudgetedData.categories.slice(0, 6).map((category, index) => (
                      <div key={category.category} className={styles.unbudgetedItem}>
                        <div className={styles.categoryInfo}>
                          <span className={styles.categoryName}>{category.category}</span>
                          <span className={styles.categoryAmount}>${category.amount.toLocaleString()}</span>
                        </div>
                        <div className={styles.categoryDetails}>
                          <span className={styles.percentage}>{category.percentage.toFixed(1)}%</span>
                          <span className={styles.transactionCount}>{category.transaction_count} transactions</span>
                        </div>
                        <button
                          onClick={() => addCategoryToBudget(category.category)}
                          disabled={addingCategory === category.category}
                          className={styles.addButton}
                          title={`Add ${category.category} to budget`}
                        >
                          {addingCategory === category.category ? '...' : '+'}
                        </button>
                      </div>
                    ))}
                    {unbudgetedData.categories.length > 6 && (
                      <div className={styles.moreCategories}>
                        +{unbudgetedData.categories.length - 6} more categories
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      <div className={styles.budgetList}>
        {/* Income Section */}
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>💼 Income</h3>
          {incomeCategories.map(categoryName => (
            <div key={categoryName} className={styles.categoryContainer}>
              <div className={styles.categoryHeader}>{categoryName}</div>
              {groupedByCategory[categoryName].map(item => (
                <div key={item.id} className={styles.subcategoryItem}>
                  <div className={styles.subcategoryHeader}>
                    <span className={styles.subcategoryName}>{item.subcategory}</span>
                    <div className={styles.progressContainer}>
                      <div 
                        className={styles.progressBar}
                        onClick={() => handleProgressBarClick(item)}
                        title="Click to view transactions"
                      >
                        {/* Actual amount bar */}
                        <div 
                          className={`${styles.progressFill} ${styles.actualFill}`}
                          style={{ 
                            width: `${Math.min(calculateProgress(item.actual, item.budgeted, item.type), 100)}%`,
                            backgroundColor: getProgressColor(item.actual, item.budgeted, item.type),
                            position: 'relative',
                            zIndex: 2
                          }}
                        />
                        {/* Expected amount bar (if available) */}
                        {item.expected && item.expected > 0 && (
                          <div 
                            className={`${styles.progressFill} ${styles.expectedFill}`}
                            style={{ 
                              width: `${Math.min(calculateProgress(item.expected, item.budgeted, item.type), 100)}%`,
                              backgroundColor: 'rgba(59, 130, 246, 0.3)', // Blue with transparency
                              position: 'absolute',
                              top: 0,
                              left: 0,
                              zIndex: 1
                            }}
                          />
                        )}
                      </div>
                      <div className={styles.progressInfo}>
                        <span className={styles.currentAmount}>${item.actual.toLocaleString()}</span>
                        <span className={styles.separator}>|</span>
                        {item.expected && item.expected > 0 && (
                          <>
                            <span className={styles.expectedAmount} title="Expected from recurring patterns">
                              ${item.expected.toLocaleString()} exp
                            </span>
                            <span className={styles.separator}>|</span>
                          </>
                        )}
                        <span className={styles.budgetAmount}>${item.budgeted.toLocaleString()}</span>
                        <span className={styles.separator}>|</span>
                        <span className={styles.variance}>
                          {getVarianceText(item.actual, item.budgeted, item.type)}
                        </span>
                      </div>
                    </div>
                    <div className={styles.amounts}>
                      {editingItem === item.id ? (
                        <div className={styles.editContainer}>
                          <input
                            type="number"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className={styles.editInput}
                            min="0"
                            step="0.01"
                            autoFocus
                          />
                          <button 
                            onClick={() => acceptEdit(item.id)}
                            className={styles.acceptButton}
                            title="Accept changes"
                          >
                            ✓
                          </button>
                          <button 
                            onClick={cancelEditing}
                            className={styles.cancelButton}
                            title="Cancel changes"
                          >
                            ✕
                          </button>
                          <button 
                            onClick={() => handleAutoUpdate(item.id)}
                            className={styles.autoButton}
                            title="Auto-update from transactions"
                          >
                            Auto
                          </button>
                        </div>
                      ) : (
                        <span 
                          className={styles.budgetedAmountEditable}
                          onClick={() => startEditing(item.id, item.budgeted)}
                          title="Click to edit budget amount"
                        >
                          ${item.budgeted.toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* Expenses Section */}
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>💸 Expenses</h3>
          {expenseCategories.map(categoryName => (
            <div key={categoryName} className={styles.categoryContainer}>
              <div className={styles.categoryHeader}>{categoryName}</div>
              {groupedByCategory[categoryName].map(item => (
                <div key={item.id} className={styles.subcategoryItem}>
                  <div className={styles.subcategoryHeader}>
                    <span className={styles.subcategoryName}>{item.subcategory}</span>
                    <div className={styles.progressContainer}>
                      <div 
                        className={styles.progressBar}
                        onClick={() => handleProgressBarClick(item)}
                        title="Click to view transactions"
                      >
                        {/* Actual amount bar */}
                        <div 
                          className={`${styles.progressFill} ${styles.actualFill}`}
                          style={{ 
                            width: `${Math.min(calculateProgress(item.actual, item.budgeted, item.type), 100)}%`,
                            backgroundColor: getProgressColor(item.actual, item.budgeted, item.type),
                            position: 'relative',
                            zIndex: 2
                          }}
                        />
                        {/* Expected amount bar (if available) */}
                        {item.expected && item.expected > 0 && (
                          <div 
                            className={`${styles.progressFill} ${styles.expectedFill}`}
                            style={{ 
                              width: `${Math.min(calculateProgress(item.expected, item.budgeted, item.type), 100)}%`,
                              backgroundColor: 'rgba(59, 130, 246, 0.3)', // Blue with transparency
                              position: 'absolute',
                              top: 0,
                              left: 0,
                              zIndex: 1
                            }}
                          />
                        )}
                      </div>
                      <div className={styles.progressInfo}>
                        <span className={styles.currentAmount}>${item.actual.toLocaleString()}</span>
                        <span className={styles.separator}>|</span>
                        {item.expected && item.expected > 0 && (
                          <>
                            <span className={styles.expectedAmount} title="Expected from recurring patterns">
                              ${item.expected.toLocaleString()} exp
                            </span>
                            <span className={styles.separator}>|</span>
                          </>
                        )}
                        <span className={styles.budgetAmount}>${item.budgeted.toLocaleString()}</span>
                        <span className={styles.separator}>|</span>
                        <span className={styles.variance}>
                          {getVarianceText(item.actual, item.budgeted, item.type)}
                        </span>
                      </div>
                    </div>
                    <div className={styles.amounts}>
                      {editingItem === item.id ? (
                        <div className={styles.editContainer}>
                          <input
                            type="number"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className={styles.editInput}
                            min="0"
                            step="0.01"
                            autoFocus
                          />
                          <button 
                            onClick={() => acceptEdit(item.id)}
                            className={styles.acceptButton}
                            title="Accept changes"
                          >
                            ✓
                          </button>
                          <button 
                            onClick={cancelEditing}
                            className={styles.cancelButton}
                            title="Cancel changes"
                          >
                            ✕
                          </button>
                          <button 
                            onClick={() => handleAutoUpdate(item.id)}
                            className={styles.autoButton}
                            title="Auto-update from transactions"
                          >
                            Auto
                          </button>
                        </div>
                      ) : (
                        <span 
                          className={styles.budgetedAmountEditable}
                          onClick={() => startEditing(item.id, item.budgeted)}
                          title="Click to edit budget amount"
                        >
                          ${item.budgeted.toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
      
      {/* Transaction Modal for drilldown */}
      <TransactionModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        category={selectedCategory?.category}
        subcategory={selectedCategory?.subcategory}
        startDate={selectedCategory?.startDate}
        endDate={selectedCategory?.endDate}
        title={selectedCategory?.title}
      />
      
      {/* Dialog Components */}
      <Dialog
        isOpen={dialog.isOpen}
        onClose={() => setDialog({ ...dialog, isOpen: false })}
        title={dialog.title}
        message={dialog.message}
        type={dialog.type}
      />
      
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        onClose={() => setConfirmDialog({ ...confirmDialog, isOpen: false })}
        onConfirm={confirmDialog.onConfirm}
        title={confirmDialog.title}
        message={confirmDialog.message}
        details={confirmDialog.details}
        type={confirmDialog.type}
        confirmText="Apply Amount"
        cancelText="Cancel"
      />
    </div>
  );
};

export default Budget;