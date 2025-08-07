import React, { useState, useEffect } from 'react';
import styles from './Budget.module.css';
import { TransactionModal } from './TransactionModal';

interface BudgetItem {
  id: string;
  category: string;
  subcategory?: string;
  budgeted: number;
  actual: number;
  type: 'expense' | 'income';
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

const Budget: React.FC = () => {
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
        
      } catch (err) {
        console.error('Error fetching budget data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load budget data');
      } finally {
        setLoading(false);
      }
    };

    fetchBudgetData();
  }, [availableMonths, currentBudgetIndex]);

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
      alert('Please enter a valid positive number');
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

      // Update locally
      setBudgetItems(prev => prev.map(item => 
        item.id === itemId ? { ...item, budgeted: newAmount } : item
      ));

      // Update totals locally
      if (totals) {
        const item = budgetItems.find(i => i.id === itemId);
        if (item) {
          const difference = newAmount - item.budgeted;
          if (item.type === 'income') {
            setTotals(prev => prev ? {
              ...prev,
              income: { ...prev.income, budgeted: prev.income.budgeted + difference },
              net: { ...prev.net, budgeted: prev.net.budgeted + difference }
            } : null);
          } else {
            setTotals(prev => prev ? {
              ...prev,
              expenses: { ...prev.expenses, budgeted: prev.expenses.budgeted + difference },
              net: { ...prev.net, budgeted: prev.net.budgeted - difference }
            } : null);
          }
        }
      }

      cancelEditing();
    } catch (err) {
      console.error('Error updating budget item:', err);
      alert(`Failed to update budget item: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const handleAutoUpdate = async (itemId: string) => {
    try {
      // Get historical average calculation
      const response = await fetch(`/api/budget/items/${itemId}/auto-calculate`);
      
      if (!response.ok) {
        const errorData = await response.json();
        if (response.status === 400) {
          alert(errorData.message || 'Insufficient historical data for auto-calculation');
        } else {
          throw new Error(errorData.error || 'Failed to calculate auto amount');
        }
        return;
      }

      const data = await response.json();
      const suggestedAmount = data.suggested_amount;
      const analysis = data.analysis;
      
      // Show confirmation dialog with analysis
      const message = `Auto-calculated amount: $${suggestedAmount.toLocaleString()}\n\n` +
        `Analysis:\n` +
        `• Based on ${analysis.months_used} months of data\n` +
        `• Confidence: ${(data.confidence * 100).toFixed(0)}% (${analysis.confidence_description})\n` +
        `• Median spending: $${analysis.median.toLocaleString()}\n` +
        `${analysis.outliers_removed > 0 ? `• Removed ${analysis.outliers_removed} outlier month(s)\n` : ''}` +
        `\nApply this amount?`;
      
      if (confirm(message)) {
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

        // Update locally
        setBudgetItems(prev => prev.map(item => 
          item.id === itemId ? { ...item, budgeted: suggestedAmount } : item
        ));

        // Update totals locally
        if (totals) {
          const item = budgetItems.find(i => i.id === itemId);
          if (item) {
            const difference = suggestedAmount - item.budgeted;
            if (item.type === 'income') {
              setTotals(prev => prev ? {
                ...prev,
                income: { ...prev.income, budgeted: prev.income.budgeted + difference },
                net: { ...prev.net, budgeted: prev.net.budgeted + difference }
              } : null);
            } else {
              setTotals(prev => prev ? {
                ...prev,
                expenses: { ...prev.expenses, budgeted: prev.expenses.budgeted + difference },
                net: { ...prev.net, budgeted: prev.net.budgeted - difference }
              } : null);
            }
          }
        }

        cancelEditing();
      }
    } catch (err) {
      console.error('Error with auto-update:', err);
      alert(`Auto-update failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
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
      setCurrentBudgetIndex(currentBudgetIndex + 1);
    }
  };

  const navigateToNext = () => {
    if (currentBudgetIndex > 0) {
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
          alert(errorData.message || 'Budget already exists for next month');
        } else {
          throw new Error(errorData.error || 'Failed to create next month budget');
        }
        return;
      }

      const data = await response.json();
      alert(`Successfully created budget for ${data.year}-${data.month.toString().padStart(2, '0')}`);
      
      // Refresh available months and navigate to the new budget
      const monthsResponse = await fetch('/api/budget/available-months');
      if (monthsResponse.ok) {
        const monthsData = await monthsResponse.json();
        setAvailableMonths(monthsData.available_months || []);
        setCurrentBudgetIndex(0); // Navigate to the newest budget
      }
    } catch (err) {
      console.error('Error creating next month budget:', err);
      alert(`Failed to create next month budget: ${err instanceof Error ? err.message : 'Unknown error'}`);
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

  // Use totals from API if available, otherwise calculate from items
  const totalBudgetedExpenses = totals?.expenses.budgeted ?? budgetItems.filter(item => item.type === 'expense').reduce((sum, item) => sum + item.budgeted, 0);
  const totalActualExpenses = totals?.expenses.actual ?? budgetItems.filter(item => item.type === 'expense').reduce((sum, item) => sum + item.actual, 0);
  const totalBudgetedIncome = totals?.income.budgeted ?? budgetItems.filter(item => item.type === 'income').reduce((sum, item) => sum + item.budgeted, 0);
  const totalActualIncome = totals?.income.actual ?? budgetItems.filter(item => item.type === 'income').reduce((sum, item) => sum + item.actual, 0);

  // Group items by category
  const groupedByCategory = budgetItems.reduce((acc, item) => {
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
              <span className={styles.actualAmount}>${totalActualIncome.toLocaleString()}</span>
            </div>
          </div>
          <div className={styles.summaryCard}>
            <h3>Expenses</h3>
            <div className={styles.summaryAmount}>
              <span className={styles.actualAmount}>${totalActualExpenses.toLocaleString()}</span>
            </div>
          </div>
          <div className={styles.summaryCard}>
            <h3>Net</h3>
            <div className={styles.summaryAmount}>
              <span className={`${styles.actualAmount} ${(totalActualIncome - totalActualExpenses) >= 0 ? styles.positive : styles.negative}`}>
                ${(totalActualIncome - totalActualExpenses).toLocaleString()}
              </span>
            </div>
          </div>
        </div>
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
                    <div className={styles.amounts}>
                      <span className={styles.actualAmount}>${item.actual.toLocaleString()}</span>
                      <span className={styles.budgetedAmount}>/ </span>
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
                  <div className={styles.progressContainer}>
                    <div 
                      className={styles.progressBar}
                      onClick={() => handleProgressBarClick(item)}
                      title="Click to view transactions"
                    >
                      <div 
                        className={styles.progressFill}
                        style={{ 
                          width: `${Math.min(calculateProgress(item.actual, item.budgeted, item.type), 100)}%`,
                          backgroundColor: getProgressColor(item.actual, item.budgeted, item.type)
                        }}
                      />
                    </div>
                    <div className={styles.progressInfo}>
                      <span className={styles.currentAmount}>${item.actual.toLocaleString()}</span>
                      <span className={styles.separator}>|</span>
                      <span className={styles.budgetAmount}>${item.budgeted.toLocaleString()}</span>
                      <span className={styles.separator}>|</span>
                      <span className={styles.variance}>
                        {getVarianceText(item.actual, item.budgeted, item.type)}
                      </span>
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
                    <div className={styles.amounts}>
                      <span className={styles.actualAmount}>${item.actual.toLocaleString()}</span>
                      <span className={styles.budgetedAmount}>/ </span>
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
                  <div className={styles.progressContainer}>
                    <div 
                      className={styles.progressBar}
                      onClick={() => handleProgressBarClick(item)}
                      title="Click to view transactions"
                    >
                      <div 
                        className={styles.progressFill}
                        style={{ 
                          width: `${Math.min(calculateProgress(item.actual, item.budgeted, item.type), 100)}%`,
                          backgroundColor: getProgressColor(item.actual, item.budgeted, item.type)
                        }}
                      />
                    </div>
                    <div className={styles.progressInfo}>
                      <span className={styles.currentAmount}>${item.actual.toLocaleString()}</span>
                      <span className={styles.separator}>|</span>
                      <span className={styles.budgetAmount}>${item.budgeted.toLocaleString()}</span>
                      <span className={styles.separator}>|</span>
                      <span className={styles.variance}>
                        {getVarianceText(item.actual, item.budgeted, item.type)}
                      </span>
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
    </div>
  );
};

export default Budget;