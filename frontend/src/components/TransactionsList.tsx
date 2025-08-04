import React, { useState, useEffect } from 'react';
import styles from './TransactionsList.module.css';

interface Transaction {
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

interface TransactionsListProps {
  initialFilters?: {
    category?: string;
    subcategory?: string;
  };
}

const TransactionsList: React.FC<TransactionsListProps> = ({ initialFilters }) => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [subcategories, setSubcategories] = useState<Subcategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTransactions, setSelectedTransactions] = useState<Set<number>>(new Set());
  const [editingTransaction, setEditingTransaction] = useState<number | null>(null);
  const [pendingEdit, setPendingEdit] = useState<{
    categoryId: number | null;
    subcategoryId: number | null;
  } | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [sortColumn, setSortColumn] = useState<keyof Transaction>('date');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState(initialFilters?.category || '');
  const [subcategoryFilter, setSubcategoryFilter] = useState(initialFilters?.subcategory || '');
  const [accountFilter, setAccountFilter] = useState('');
  const [availableAccounts, setAvailableAccounts] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalTransactions, setTotalTransactions] = useState(0);
  const pageSize = 50;

  useEffect(() => {
    fetchData();
  }, [currentPage, searchTerm, categoryFilter, subcategoryFilter, accountFilter, sortColumn, sortDirection]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: pageSize.toString()
      });

      // Add search filter
      if (searchTerm.trim()) {
        params.append('search', searchTerm.trim());
      }

      // Add category filter
      if (categoryFilter) {
        params.append('category', categoryFilter);
      }

      // Add subcategory filter
      if (subcategoryFilter) {
        params.append('subcategory', subcategoryFilter);
      }

      // Add account filter
      if (accountFilter) {
        params.append('account', accountFilter);
      }

      const [transactionsResponse, categoriesResponse, filtersResponse] = await Promise.all([
        fetch(`/api/transactions?${params.toString()}`),
        fetch('/api/categories'),
        fetch('/api/filters')
      ]);

      if (!transactionsResponse.ok || !categoriesResponse.ok || !filtersResponse.ok) {
        throw new Error('Failed to fetch data');
      }

      const transactionsResult = await transactionsResponse.json();
      const categoriesResult = await categoriesResponse.json();
      const filtersResult = await filtersResponse.json();

      setTransactions(transactionsResult.transactions || []);
      setTotalPages(transactionsResult.pagination?.pages || 1);
      setTotalTransactions(transactionsResult.pagination?.total || 0);
      setCategories(categoriesResult.categories || []);
      setSubcategories(categoriesResult.subcategories || []);
      setAvailableAccounts(filtersResult.accounts || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (column: keyof Transaction) => {
    if (column === sortColumn) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
    setCurrentPage(1); // Reset to first page when sorting
  };

  const handleSearch = (term: string) => {
    setSearchTerm(term);
    setCurrentPage(1); // Reset to first page when searching
  };

  const handleCategoryFilter = (category: string) => {
    setCategoryFilter(category);
    // Clear subcategory filter when category changes
    if (category !== categoryFilter) {
      setSubcategoryFilter('');
    }
    setCurrentPage(1); // Reset to first page when filtering
  };

  const handleSubcategoryFilter = (subcategory: string) => {
    setSubcategoryFilter(subcategory);
    setCurrentPage(1); // Reset to first page when filtering
  };

  const handleAccountFilter = (account: string) => {
    setAccountFilter(account);
    setCurrentPage(1); // Reset to first page when filtering
  };

  const handleClearFilters = () => {
    setSearchTerm('');
    setCategoryFilter('');
    setSubcategoryFilter('');
    setAccountFilter('');
    setCurrentPage(1); // Reset to first page when clearing filters
  };

  const handleTransactionUpdate = async (transactionId: number, categoryId: number | null, subcategoryId: number | null) => {
    try {
      const response = await fetch(`/api/transactions/${transactionId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          category_id: categoryId,
          subcategory_id: subcategoryId,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update transaction');
      }

      setTransactions(transactions.map(t => 
        t.id === transactionId 
          ? {
              ...t,
              category_id: categoryId,
              subcategory_id: subcategoryId,
              category: categories.find(c => c.id === categoryId)?.name || '',
              subcategory: subcategories.find(s => s.id === subcategoryId)?.name || ''
            }
          : t
      ));
      
      setEditingTransaction(null);
      setPendingEdit(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update transaction');
    }
  };

  const handleEditStart = (transactionId: number) => {
    const transaction = transactions.find(t => t.id === transactionId);
    if (transaction) {
      setEditingTransaction(transactionId);
      setPendingEdit({
        categoryId: transaction.category_id,
        subcategoryId: transaction.subcategory_id
      });
    }
  };

  const handleEditCancel = () => {
    setEditingTransaction(null);
    setPendingEdit(null);
  };

  const handleEditApply = () => {
    if (editingTransaction && pendingEdit) {
      handleTransactionUpdate(editingTransaction, pendingEdit.categoryId, pendingEdit.subcategoryId);
    }
  };

  const handleBulkCategorize = async (categoryId: number | null, subcategoryId: number | null) => {
    if (selectedTransactions.size === 0) return;

    try {
      const response = await fetch('/api/transactions/bulk-categorize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          transaction_ids: Array.from(selectedTransactions),
          category_id: categoryId,
          subcategory_id: subcategoryId,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to bulk categorize transactions');
      }

      setTransactions(transactions.map(t => 
        selectedTransactions.has(t.id)
          ? {
              ...t,
              category_id: categoryId,
              subcategory_id: subcategoryId,
              category: categories.find(c => c.id === categoryId)?.name || '',
              subcategory: subcategories.find(s => s.id === subcategoryId)?.name || ''
            }
          : t
      ));
      
      setSelectedTransactions(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to bulk categorize');
    }
  };

  const toggleTransactionSelection = (transactionId: number) => {
    const newSelection = new Set(selectedTransactions);
    if (newSelection.has(transactionId)) {
      newSelection.delete(transactionId);
    } else {
      newSelection.add(transactionId);
    }
    setSelectedTransactions(newSelection);
  };

  const toggleAllSelection = () => {
    if (selectedTransactions.size === transactions.length) {
      setSelectedTransactions(new Set());
    } else {
      setSelectedTransactions(new Set(transactions.map(t => t.id)));
    }
  };

  const toggleRowExpansion = (transactionId: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(transactionId)) {
      newExpanded.delete(transactionId);
    } else {
      newExpanded.add(transactionId);
    }
    setExpandedRows(newExpanded);
  };

  const formatCurrency = (amount: number) => {
    const sign = amount < 0 ? '-' : '';
    return `${sign}$${Math.abs(amount).toFixed(2)}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Generate consistent color for category/subcategory labels
  const getCategoryColor = (text: string, isSubcategory = false) => {
    if (!text) return null;
    
    // Create a simple hash from the text
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
      const char = text.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    
    // Generate HSL color with good readability
    const hue = Math.abs(hash) % 360;
    
    if (isSubcategory) {
      // More vibrant colors for subcategories
      const saturation = 65 + (Math.abs(hash) % 20); // 65-85%
      const lightness = 85 + (Math.abs(hash) % 10); // 85-95% for light backgrounds
      
      return {
        backgroundColor: `hsl(${hue}, ${saturation}%, ${lightness}%)`,
        color: `hsl(${hue}, ${Math.min(saturation + 20, 100)}%, 25%)`, // Darker text
        borderColor: `hsl(${hue}, ${saturation}%, ${lightness - 15}%)`
      };
    } else {
      // More subtle colors for categories
      const saturation = 30 + (Math.abs(hash) % 15); // 30-45%
      const lightness = 90 + (Math.abs(hash) % 8); // 90-98% for very light backgrounds
      
      return {
        backgroundColor: `hsl(${hue}, ${saturation}%, ${lightness}%)`,
        color: `hsl(${hue}, ${Math.min(saturation + 30, 100)}%, 30%)`, // Darker text
        borderColor: `hsl(${hue}, ${saturation}%, ${lightness - 10}%)`
      };
    }
  };

  return (
    <div className="container">
      <h1 className="text-3xl mb-6">
        All Transactions
        {(categoryFilter || subcategoryFilter || accountFilter) && (
          <span className={styles.filterIndicator}>
            {accountFilter && ` • ${accountFilter}`}
            {categoryFilter && ` • ${categoryFilter}`}
            {subcategoryFilter && ` • ${subcategoryFilter}`}
          </span>
        )}
      </h1>

      {/* Filters and Search */}
      <div className={styles.filtersContainer}>
        <div className={styles.searchContainer}>
          <input
            type="text"
            placeholder="Search description, payee, action, category..."
            value={searchTerm}
            onChange={(e) => handleSearch(e.target.value)}
            className={styles.searchInput}
          />
        </div>
        <div className={styles.filterContainer}>
          <select
            value={accountFilter}
            onChange={(e) => handleAccountFilter(e.target.value)}
            className={styles.categoryFilter}
          >
            <option value="">All Accounts</option>
            {availableAccounts.map(account => (
              <option key={account} value={account}>{account}</option>
            ))}
          </select>
          <select
            value={categoryFilter}
            onChange={(e) => handleCategoryFilter(e.target.value)}
            className={styles.categoryFilter}
          >
            <option value="">All Categories</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.name}>{cat.name}</option>
            ))}
          </select>
          <select
            value={subcategoryFilter}
            onChange={(e) => handleSubcategoryFilter(e.target.value)}
            className={styles.categoryFilter}
            disabled={!categoryFilter}
          >
            <option value="">All Subcategories</option>
            {subcategories
              .filter(sub => !categoryFilter || sub.category_name === categoryFilter)
              .map(sub => (
                <option key={sub.id} value={sub.name}>{sub.name}</option>
              ))}
          </select>
          <button
            onClick={handleClearFilters}
            className={styles.clearFiltersButton}
            title="Clear all filters"
          >
            Clear Filters
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className={styles.summaryContainer}>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{totalTransactions.toLocaleString()}</div>
          <div className={styles.statLabel}>Total Transactions</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>
            ${Math.abs(transactions.reduce((sum, t) => sum + t.amount, 0)).toLocaleString()}
          </div>
          <div className={styles.statLabel}>Page Amount</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>
            {transactions.filter(t => !t.category_id).length.toLocaleString()}
          </div>
          <div className={styles.statLabel}>Uncategorized (Page)</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>
            Page {currentPage} of {totalPages}
          </div>
          <div className={styles.statLabel}>Pagination</div>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedTransactions.size > 0 && (
        <div className={styles.bulkActions}>
          <span className={styles.selectedCount}>
            {selectedTransactions.size} selected
          </span>
          <select
            className={styles.bulkSelect}
            onChange={(e) => {
              const categoryId = parseInt(e.target.value);
              const subcategoryId = null;
              handleBulkCategorize(categoryId || null, subcategoryId);
            }}
          >
            <option value="">Bulk Categorize...</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Transaction Table */}
      <div className="card">
        {loading && (
          <div className={styles.loading}>
            <p>Loading transactions...</p>
          </div>
        )}

        {error && (
          <div className={styles.error}>
            <p>Error: {error}</p>
          </div>
        )}

        {!loading && !error && (
          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr className={styles.tableHeader}>
                  <th className={styles.tableHeaderCell}>
                    <input
                      type="checkbox"
                      checked={selectedTransactions.size === transactions.length && transactions.length > 0}
                      onChange={toggleAllSelection}
                    />
                  </th>
                  {(['date', 'account', 'payee', 'description', 'amount', 'category', 'subcategory'] as const).map(column => (
                    <th 
                      key={column}
                      onClick={() => handleSort(column)}
                      className={styles.tableHeaderCell}
                    >
                      {column.charAt(0).toUpperCase() + column.slice(1)}
                      {sortColumn === column && (
                        <span className={styles.sortIcon}>
                          {sortDirection === 'asc' ? '↑' : '↓'}
                        </span>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {transactions.map((transaction, index) => (
                  <React.Fragment key={transaction.id}>
                    <tr 
                      className={`${styles.tableRow} ${index % 2 === 0 ? styles.tableRowEven : styles.tableRowOdd} ${styles.clickableRow}`}
                      onClick={() => toggleRowExpansion(transaction.id)}
                    >
                      <td className={styles.tableCell}>
                        <input
                          type="checkbox"
                          checked={selectedTransactions.has(transaction.id)}
                          onChange={(e) => {
                            e.stopPropagation();
                            toggleTransactionSelection(transaction.id);
                          }}
                        />
                      </td>
                      <td className={styles.tableCell}>
                        <div className={styles.cellWithExpander}>
                          {formatDate(transaction.date)}
                          <span className={`${styles.expandIcon} ${expandedRows.has(transaction.id) ? styles.expandIconOpen : ''}`}>
                            ▶
                          </span>
                        </div>
                      </td>
                      <td className={`${styles.tableCell} ${styles.tableCellAccount}`}>
                        <div className={styles.ellipsis}>
                          {transaction.account}
                        </div>
                      </td>
                      <td className={`${styles.tableCell} ${styles.tableCellPayee}`}>
                        <div className={styles.ellipsis}>
                          {transaction.payee || '-'}
                        </div>
                      </td>
                      <td className={`${styles.tableCell} ${styles.tableCellDescription}`}>
                        <div className={styles.ellipsis}>
                          {transaction.description}
                        </div>
                      </td>
                      <td className={`${styles.tableCell} ${styles.tableCellAmount} ${transaction.amount < 0 ? styles.amountNegative : styles.amountPositive}`}>
                        {formatCurrency(transaction.amount)}
                      </td>
                      <td className={`${styles.tableCell} ${styles.tableCellCategory}`}>
                        {editingTransaction === transaction.id ? (
                          <div className={styles.editContainer} onClick={(e) => e.stopPropagation()}>
                            <select
                              value={pendingEdit?.categoryId || ''}
                              onChange={(e) => {
                                const categoryId = parseInt(e.target.value) || null;
                                setPendingEdit({
                                  categoryId,
                                  subcategoryId: null // Reset subcategory when category changes
                                });
                              }}
                              className={styles.categorySelect}
                            >
                              <option value="">Uncategorized</option>
                              {categories.map(cat => (
                                <option key={cat.id} value={cat.id}>{cat.name}</option>
                              ))}
                            </select>
                            <div className={styles.editActions}>
                              <button
                                onClick={handleEditApply}
                                className={`${styles.editButton} ${styles.editButtonApply}`}
                                title="Apply changes"
                              >
                                ✓
                              </button>
                              <button
                                onClick={handleEditCancel}
                                className={`${styles.editButton} ${styles.editButtonCancel}`}
                                title="Cancel changes"
                              >
                                ✕
                              </button>
                            </div>
                          </div>
                        ) : (
                          <span
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEditStart(transaction.id);
                            }}
                            className={`${styles.categorySpan} ${transaction.category ? styles.categoryColored : styles.uncategorized}`}
                            style={transaction.category ? getCategoryColor(transaction.category, false) : undefined}
                          >
                            {transaction.category || 'Uncategorized'}
                          </span>
                        )}
                      </td>
                      <td className={`${styles.tableCell} ${styles.tableCellCategory}`}>
                        {editingTransaction === transaction.id && pendingEdit?.categoryId ? (
                          <div className={styles.editContainer} onClick={(e) => e.stopPropagation()}>
                            <select
                              value={pendingEdit?.subcategoryId || ''}
                              onChange={(e) => {
                                const subcategoryId = parseInt(e.target.value) || null;
                                setPendingEdit({
                                  ...pendingEdit,
                                  subcategoryId
                                });
                              }}
                              className={styles.categorySelect}
                            >
                              <option value="">None</option>
                              {subcategories
                                .filter(sub => sub.category_id === pendingEdit.categoryId)
                                .map(sub => (
                                  <option key={sub.id} value={sub.id}>{sub.name}</option>
                                ))}
                            </select>
                          </div>
                        ) : (
                          <span
                            onClick={(e) => {
                              e.stopPropagation();
                              if (transaction.category_id) handleEditStart(transaction.id);
                            }}
                            className={`${styles.categorySpan} ${transaction.subcategory ? styles.subcategoryColored : styles.categorized} ${!transaction.category_id ? styles.subcategorySpanDisabled : ''}`}
                            style={transaction.subcategory ? getCategoryColor(transaction.subcategory, true) : undefined}
                          >
                            {transaction.subcategory || (transaction.category_id ? 'None' : '-')}
                          </span>
                        )}
                      </td>
                    </tr>
                    {expandedRows.has(transaction.id) && (
                      <tr className={styles.expandedRow}>
                        <td colSpan={8} className={styles.expandedContent}>
                          <div className={styles.expandedDetails}>
                            <div className={styles.detailItem}>
                              <span className={styles.detailLabel}>Action:</span>
                              <span className={styles.detailValue}>{transaction.action || 'No action recorded'}</span>
                            </div>
                            <div className={styles.detailItem}>
                              <span className={styles.detailLabel}>Transaction Type:</span>
                              <span className={styles.detailValue}>{transaction.transaction_type || 'Unknown'}</span>
                            </div>
                            <div className={styles.detailItem}>
                              <span className={styles.detailLabel}>Transaction ID:</span>
                              <span className={styles.detailValue}>{transaction.id}</span>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
            
            {/* Pagination Controls */}
            <div className={styles.paginationContainer}>
              <div className={styles.paginationInfo}>
                Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, totalTransactions)} of {totalTransactions.toLocaleString()} transactions
              </div>
              <div className={styles.paginationControls}>
                <button
                  onClick={() => setCurrentPage(1)}
                  disabled={currentPage === 1}
                  className={styles.paginationButton}
                >
                  First
                </button>
                <button
                  onClick={() => setCurrentPage(currentPage - 1)}
                  disabled={currentPage === 1}
                  className={styles.paginationButton}
                >
                  Previous
                </button>
                <span className={styles.paginationInfo}>
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className={styles.paginationButton}
                >
                  Next
                </button>
                <button
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={currentPage === totalPages}
                  className={styles.paginationButton}
                >
                  Last
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TransactionsList;