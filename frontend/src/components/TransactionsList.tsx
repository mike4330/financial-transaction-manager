import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import styles from './TransactionsList.module.css';
import { usePreferences } from '../contexts/PreferencesContext';
import SplitTransactionDialog from './SplitTransactionDialog';
import { Transaction as TransactionType, Split } from '../types';
import { transactionApi } from '../utils/api';

interface Transaction extends TransactionType {
  action: string;
  description: string;
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
  const params = useParams<{ category?: string; subcategory?: string }>();
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
  const [editingNote, setEditingNote] = useState<number | null>(null);
  const [pendingNote, setPendingNote] = useState<string>('');
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [sortColumn, setSortColumn] = useState<keyof Transaction>('date');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState(
    params.category || initialFilters?.category || ''
  );
  const [subcategoryFilter, setSubcategoryFilter] = useState(
    params.subcategory || initialFilters?.subcategory || ''
  );
  const [accountFilter, setAccountFilter] = useState('');
  const [availableAccounts, setAvailableAccounts] = useState<string[]>([]);
  const [transactionTypeFilter, setTransactionTypeFilter] = useState('');
  const [availableTransactionTypes, setAvailableTransactionTypes] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalTransactions, setTotalTransactions] = useState(0);
  const [showBulkCategoryMenu, setShowBulkCategoryMenu] = useState(false);
  const [selectedBulkCategory, setSelectedBulkCategory] = useState<number | null>(null);
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [splitDialogOpen, setSplitDialogOpen] = useState(false);
  const [selectedTransactionForSplit, setSelectedTransactionForSplit] = useState<Transaction | null>(null);
  const [transactionSplits, setTransactionSplits] = useState<Map<number, Split[]>>(new Map());
  const pageSize = 50;

  // Get preferences
  const { transactionsPreferences } = usePreferences();

  useEffect(() => {
    fetchData();
    // Collapse all rows when data changes (page, filters, sorting, etc.)
    setExpandedRows(new Set());
  }, [currentPage, searchTerm, categoryFilter, subcategoryFilter, accountFilter, transactionTypeFilter, sortColumn, sortDirection, transactionsPreferences.hideInvestments]);

  // Close bulk menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (showBulkCategoryMenu && !target.closest(`[class*="bulkCategoryContainer"]`)) {
        setShowBulkCategoryMenu(false);
        setSelectedBulkCategory(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showBulkCategoryMenu]);

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

      // Add transaction type filter
      if (transactionTypeFilter) {
        params.append('type', transactionTypeFilter);
      }

      // Add investment exclusion filter based on preferences
      if (transactionsPreferences.hideInvestments) {
        params.append('exclude_investments', 'true');
      }

      // Add sorting parameters
      params.append('sort_column', sortColumn);
      params.append('sort_direction', sortDirection);

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
      setAvailableTransactionTypes(filtersResult.transaction_types || []);
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

  const handleTransactionTypeFilter = (transactionType: string) => {
    setTransactionTypeFilter(transactionType);
    setCurrentPage(1); // Reset to first page when filtering
  };

  const handleClearFilters = () => {
    setSearchTerm('');
    setCategoryFilter('');
    setSubcategoryFilter('');
    setAccountFilter('');
    setTransactionTypeFilter('');
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

      setEditingTransaction(null);
      setPendingEdit(null);
      
      // Refresh the view to get updated data
      await fetchData();
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

  // Note editing functions
  const handleNoteEditStart = (transactionId: number, currentNote: string) => {
    setEditingNote(transactionId);
    setPendingNote(currentNote);
  };

  const handleNoteCancel = () => {
    setEditingNote(null);
    setPendingNote('');
  };

  const handleNoteApply = async (transactionId: number) => {
    try {
      const response = await fetch(`/api/transactions/${transactionId}/note`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ note: pendingNote || null })
      });

      if (!response.ok) {
        throw new Error('Failed to update note');
      }

      // Update the transaction in the local state
      setTransactions(prev => prev.map(t =>
        t.id === transactionId ? { ...t, note: pendingNote || null } : t
      ));

      setEditingNote(null);
      setPendingNote('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update note');
    }
  };

  // Split transaction functions
  const handleSplitTransaction = async (transaction: Transaction) => {
    // Load existing splits if transaction is already split
    if (transaction.is_split) {
      try {
        const response = await transactionApi.getSplits(transaction.id);
        setTransactionSplits(prev => new Map(prev).set(transaction.id, response.splits));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load splits');
      }
    }

    setSelectedTransactionForSplit(transaction);
    setSplitDialogOpen(true);
  };

  const handleSplitCreated = async () => {
    // Refresh transactions to get updated is_split and split_count
    await fetchData();
  };

  const loadSplitsForTransaction = async (transactionId: number) => {
    try {
      const response = await transactionApi.getSplits(transactionId);
      setTransactionSplits(prev => new Map(prev).set(transactionId, response.splits));
    } catch (err) {
      console.error('Failed to load splits:', err);
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

  const handleBulkDelete = async () => {
    if (selectedTransactions.size === 0) return;

    try {
      const response = await fetch('/api/transactions/bulk-delete', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          transaction_ids: Array.from(selectedTransactions)
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to delete transactions');
      }

      // Remove deleted transactions from local state
      setTransactions(transactions.filter(t => !selectedTransactions.has(t.id)));
      setSelectedTransactions(new Set());
      setShowDeleteConfirmation(false);
      
      // Refresh the view to get updated pagination
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete transactions');
      setShowDeleteConfirmation(false);
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

  const handleBulkCategorySelect = (categoryId: number) => {
    setSelectedBulkCategory(categoryId);
  };

  const handleBulkSubcategorySelect = (subcategoryId: number | null) => {
    if (selectedBulkCategory) {
      handleBulkCategorize(selectedBulkCategory, subcategoryId);
      setShowBulkCategoryMenu(false);
      setSelectedBulkCategory(null);
    }
  };

  const closeBulkMenu = () => {
    setShowBulkCategoryMenu(false);
    setSelectedBulkCategory(null);
  };

  const collapseAllRows = () => {
    setExpandedRows(new Set());
  };

  const generateExportHTML = () => {
    const selectedTransactionsList = transactions.filter(t => selectedTransactions.has(t.id));
    
    if (selectedTransactionsList.length === 0) {
      return '<p>No transactions selected for export.</p>';
    }

    let html = `
<table border="1" cellpadding="5" cellspacing="0">
  <thead>
    <tr>
      <th>Date</th>
      <th>Account</th>
      <th>Amount</th>
      <th>Payee</th>
      <th>Action</th>
      <th>Category</th>
      <th>Subcategory</th>
    </tr>
  </thead>
  <tbody>
`;

    selectedTransactionsList.forEach(transaction => {
      html += `
    <tr>
      <td>${formatDate(transaction.date)}</td>
      <td>${transaction.account || ''}</td>
      <td>${formatCurrency(transaction.amount)}</td>
      <td>${transaction.payee || ''}</td>
      <td>${transaction.action || ''}</td>
      <td>${transaction.category || ''}</td>
      <td>${transaction.subcategory || ''}</td>
    </tr>`;
    });

    html += `
  </tbody>
</table>

<p><strong>Exported ${selectedTransactionsList.length} transaction(s) on ${new Date().toLocaleString()}</strong></p>`;

    return html;
  };

  const formatCurrency = (amount: number) => {
    const sign = amount < 0 ? '-' : '';
    return `${sign}$${Math.abs(amount).toFixed(2)}`;
  };

  const formatDate = (dateString: string) => {
    // Parse date string safely without timezone conversion issues
    const [year, month, day] = dateString.split('-').map(Number);
    const date = new Date(year, month - 1, day); // month is 0-based in Date constructor
    return date.toLocaleDateString('en-US', {
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

    // Generate HSL color with good readability and divergence
    const hue = Math.abs(hash) % 360;

    if (isSubcategory) {
      // Vibrant, saturated colors for subcategories
      const saturation = 70 + (Math.abs(hash) % 25); // 70-95% - much more vibrant
      const lightness = 75 + (Math.abs(hash) % 15); // 75-90% - darker backgrounds for better contrast

      return {
        backgroundColor: `hsl(${hue}, ${saturation}%, ${lightness}%)`,
        color: `hsl(${hue}, ${Math.min(saturation + 10, 100)}%, 20%)`, // Much darker text for contrast
        borderColor: `hsl(${hue}, ${saturation}%, ${lightness - 20}%)` // Stronger border
      };
    } else {
      // Moderate saturation for categories with wider range
      const saturation = 45 + (Math.abs(hash) % 35); // 45-80% - much wider range for differentiation
      const lightness = 82 + (Math.abs(hash) % 13); // 82-95% - moderate backgrounds

      return {
        backgroundColor: `hsl(${hue}, ${saturation}%, ${lightness}%)`,
        color: `hsl(${hue}, ${Math.min(saturation + 15, 100)}%, 22%)`, // Darker text for better contrast
        borderColor: `hsl(${hue}, ${saturation}%, ${lightness - 18}%)` // Stronger border
      };
    }
  };

  return (
    <div className="container">
      <h1 className="text-3xl mb-6">
        All Transactions
        {(categoryFilter || subcategoryFilter || accountFilter || transactionTypeFilter) && (
          <span className={styles.filterIndicator}>
            {accountFilter && ` • ${accountFilter}`}
            {categoryFilter && ` • ${categoryFilter}`}
            {subcategoryFilter && ` • ${subcategoryFilter}`}
            {transactionTypeFilter && ` • ${transactionTypeFilter}`}
          </span>
        )}
      </h1>

      {/* Filters and Search */}
      <div className={styles.filtersContainer}>
        <div className={styles.searchContainer}>
          <input
            type="text"
            placeholder="Search description, payee, action, category, amount..."
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
            <option value="Uncategorized">Uncategorized</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.name}>{cat.name}</option>
            ))}
          </select>
          <select
            value={subcategoryFilter}
            onChange={(e) => handleSubcategoryFilter(e.target.value)}
            className={styles.categoryFilter}
            disabled={!categoryFilter || categoryFilter === 'Uncategorized'}
          >
            <option value="">All Subcategories</option>
            {subcategories
              .filter(sub => !categoryFilter || sub.category_name === categoryFilter)
              .map(sub => (
                <option key={sub.id} value={sub.name}>{sub.name}</option>
              ))}
          </select>
          {!transactionsPreferences.hideInvestments && (
            <select
              value={transactionTypeFilter}
              onChange={(e) => handleTransactionTypeFilter(e.target.value)}
              className={styles.categoryFilter}
            >
              <option value="">All Transaction Types</option>
              {availableTransactionTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          )}
          <button
            onClick={handleClearFilters}
            className={styles.clearFiltersButton}
            title="Clear all filters"
          >
            Clear Filters
          </button>
          <button
            onClick={collapseAllRows}
            className={styles.collapseAllButton}
            title="Collapse all expanded rows"
          >
            Collapse All
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
          <button
            className={styles.bulkDeleteButton}
            onClick={() => setShowDeleteConfirmation(true)}
            title="Delete selected transactions"
          >
            Delete Selected
          </button>
          <button
            className={styles.bulkExportButton}
            onClick={() => setShowExportModal(true)}
            title="Export selected transactions"
          >
            Export Selected
          </button>
          <div className={styles.bulkCategoryContainer}>
            <button
              className={styles.bulkCategoryButton}
              onClick={() => setShowBulkCategoryMenu(!showBulkCategoryMenu)}
            >
              Bulk Categorize... ▼
            </button>
            {showBulkCategoryMenu && (
              <div className={styles.bulkCategoryMenu}>
                <div className={styles.bulkMenuHeader}>
                  <span>Select Category & Subcategory</span>
                  <button 
                    className={styles.bulkMenuClose}
                    onClick={closeBulkMenu}
                  >
                    ×
                  </button>
                </div>
                <div className={styles.bulkMenuContent}>
                  <div className={styles.bulkCategoryList}>
                    <div className={styles.bulkMenuSection}>
                      <h4>Categories</h4>
                      {categories.map(cat => (
                        <button
                          key={cat.id}
                          className={`${styles.bulkCategoryItem} ${selectedBulkCategory === cat.id ? styles.bulkCategorySelected : ''}`}
                          onClick={() => handleBulkCategorySelect(cat.id)}
                        >
                          {cat.name}
                        </button>
                      ))}
                    </div>
                    {selectedBulkCategory && (
                      <div className={styles.bulkSubcategoryList}>
                        <div className={styles.bulkMenuSection}>
                          <h4>Subcategories</h4>
                          <button
                            className={styles.bulkSubcategoryItem}
                            onClick={() => handleBulkSubcategorySelect(null)}
                          >
                            None
                          </button>
                          {subcategories
                            .filter(sub => sub.category_id === selectedBulkCategory)
                            .map(sub => (
                              <button
                                key={sub.id}
                                className={styles.bulkSubcategoryItem}
                                onClick={() => handleBulkSubcategorySelect(sub.id)}
                              >
                                {sub.name}
                              </button>
                            ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
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
                  {(['date', 'account', 'payee', 'amount', 'category', 'subcategory', 'note'] as const).map(column => (
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
                          onClick={(e) => e.stopPropagation()}
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
                      <td className={`${styles.tableCell} ${styles.tableCellAmount} ${transaction.amount < 0 ? styles.amountNegative : styles.amountPositive}`}>
                        {formatCurrency(transaction.amount)}
                      </td>
                      <td className={`${styles.tableCell} ${styles.tableCellCategory}`}>
                        {transaction.is_split ? (
                          <span className={`${styles.categorySpan} ${styles.splitIndicator}`}>
                            Split ({transaction.split_count || 0})
                          </span>
                        ) : editingTransaction === transaction.id ? (
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
                        {transaction.is_split ? (
                          <span className={styles.categorySpan}>-</span>
                        ) : editingTransaction === transaction.id && pendingEdit?.categoryId ? (
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
                      <td className={`${styles.tableCell} ${styles.tableCellNote}`}>
                        {editingNote === transaction.id ? (
                          <div className={styles.noteEditContainer} onClick={(e) => e.stopPropagation()}>
                            <input
                              type="text"
                              value={pendingNote}
                              onChange={(e) => setPendingNote(e.target.value)}
                              className={styles.noteInput}
                              placeholder="Add a note..."
                              autoFocus
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  handleNoteApply(transaction.id);
                                } else if (e.key === 'Escape') {
                                  handleNoteCancel();
                                }
                              }}
                            />
                            <div className={styles.noteEditActions}>
                              <button
                                onClick={() => handleNoteApply(transaction.id)}
                                className={`${styles.editButton} ${styles.editButtonApply}`}
                                title="Save note"
                              >
                                ✓
                              </button>
                              <button
                                onClick={handleNoteCancel}
                                className={`${styles.editButton} ${styles.editButtonCancel}`}
                                title="Cancel"
                              >
                                ✕
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div 
                            className={styles.noteDisplay}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleNoteEditStart(transaction.id, transaction.note || '');
                            }}
                            title="Click to edit note"
                          >
                            {transaction.note || <span className={styles.noteEmpty}>Add note...</span>}
                          </div>
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
                            <div className={styles.detailItem}>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleSplitTransaction(transaction);
                                }}
                                className={styles.splitButton}
                              >
                                {transaction.is_split ? 'Edit Splits' : 'Split Transaction'}
                              </button>
                            </div>
                          </div>

                          {transaction.is_split && (
                            <div className={styles.splitBreakdown}>
                              <h4 className={styles.splitTitle}>Split Details:</h4>
                              {(() => {
                                const splits = transactionSplits.get(transaction.id);
                                if (!splits) {
                                  loadSplitsForTransaction(transaction.id);
                                  return <p className={styles.splitLoading}>Loading splits...</p>;
                                }
                                return (
                                  <table className={styles.splitTable}>
                                    <thead>
                                      <tr>
                                        <th>Category</th>
                                        <th>Subcategory</th>
                                        <th>Amount</th>
                                        <th>Note</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {splits.map((split, index) => (
                                        <tr key={split.id || index}>
                                          <td>
                                            <span
                                              className={styles.categorySpan}
                                              style={getCategoryColor(split.category, false)}
                                            >
                                              {split.category}
                                            </span>
                                          </td>
                                          <td>
                                            {split.subcategory ? (
                                              <span
                                                className={styles.categorySpan}
                                                style={getCategoryColor(split.subcategory, true)}
                                              >
                                                {split.subcategory}
                                              </span>
                                            ) : (
                                              '-'
                                            )}
                                          </td>
                                          <td className={split.amount < 0 ? styles.amountNegative : styles.amountPositive}>
                                            {formatCurrency(split.amount)}
                                          </td>
                                          <td>{split.note || '-'}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                );
                              })()}
                            </div>
                          )}
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

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirmation && (
        <div className={styles.modalOverlay}>
          <div className={styles.confirmationModal}>
            <div className={styles.modalHeader}>
              <h3>Confirm Delete</h3>
            </div>
            <div className={styles.modalContent}>
              <p>
                Are you sure you want to delete {selectedTransactions.size} selected transaction{selectedTransactions.size !== 1 ? 's' : ''}?
              </p>
              <p className={styles.warningText}>
                This action cannot be undone.
              </p>
            </div>
            <div className={styles.modalActions}>
              <button
                onClick={() => setShowDeleteConfirmation(false)}
                className={styles.cancelButton}
              >
                Cancel
              </button>
              <button
                onClick={handleBulkDelete}
                className={styles.deleteButton}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Export Modal */}
      {showExportModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.exportModal}>
            <div className={styles.modalHeader}>
              <h3>Export Selected Transactions</h3>
              <button
                onClick={() => setShowExportModal(false)}
                className={styles.modalCloseButton}
                title="Close"
              >
                ×
              </button>
            </div>
            <div className={styles.modalContent}>
              <div className={styles.exportPreview}>
                <div dangerouslySetInnerHTML={{ __html: generateExportHTML() }} />
              </div>
            </div>
            <div className={styles.modalActions}>
              <button
                onClick={() => {
                  const html = generateExportHTML();
                  navigator.clipboard.writeText(html).then(() => {
                    alert('HTML copied to clipboard!');
                  }).catch(() => {
                    // Fallback: select the text
                    const textArea = document.createElement('textarea');
                    textArea.value = html;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    alert('HTML copied to clipboard!');
                  });
                }}
                className={styles.copyButton}
              >
                Copy HTML
              </button>
              <button
                onClick={() => setShowExportModal(false)}
                className={styles.cancelButton}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Split Transaction Dialog */}
      {selectedTransactionForSplit && (
        <SplitTransactionDialog
          isOpen={splitDialogOpen}
          onClose={() => {
            setSplitDialogOpen(false);
            setSelectedTransactionForSplit(null);
          }}
          transaction={selectedTransactionForSplit}
          categories={categories}
          subcategories={subcategories}
          existingSplits={transactionSplits.get(selectedTransactionForSplit.id)}
          onSplitCreated={handleSplitCreated}
        />
      )}
    </div>
  );
};

export default TransactionsList;