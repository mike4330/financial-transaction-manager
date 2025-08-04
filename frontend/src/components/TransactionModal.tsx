import React, { useState, useEffect } from 'react';
import styles from './TransactionModal.module.css';

interface Transaction {
  id: number;
  date: string;
  account: string;
  amount: number;
  payee: string;
  description: string;
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

interface TransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  category?: string;
  subcategory?: string;
  startDate?: string;
  endDate?: string;
  title?: string;
}

export const TransactionModal: React.FC<TransactionModalProps> = ({
  isOpen,
  onClose,
  category,
  subcategory,
  startDate,
  endDate,
  title
}) => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [subcategories, setSubcategories] = useState<Subcategory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTransactions, setSelectedTransactions] = useState<Set<number>>(new Set());
  const [editingTransaction, setEditingTransaction] = useState<number | null>(null);
  const [sortColumn, setSortColumn] = useState<keyof Transaction>('date');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // Fetch data when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchData();
    }
  }, [isOpen, category, subcategory, startDate, endDate]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch transactions with filters
      const params = new URLSearchParams({
        limit: '1000'
      });
      
      if (category) params.append('category', category);
      if (subcategory) params.append('subcategory', subcategory);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);

      const [transactionsResponse, categoriesResponse] = await Promise.all([
        fetch(`/api/transactions?${params.toString()}`),
        fetch('/api/categories')
      ]);

      if (!transactionsResponse.ok || !categoriesResponse.ok) {
        throw new Error('Failed to fetch data');
      }

      const transactionsResult = await transactionsResponse.json();
      const categoriesResult = await categoriesResponse.json();

      setTransactions(transactionsResult.transactions || []);
      setCategories(categoriesResult.categories || []);
      setSubcategories(categoriesResult.subcategories || []);
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
  };

  const sortedTransactions = [...transactions].sort((a, b) => {
    const aVal = a[sortColumn];
    const bVal = b[sortColumn];
    
    if (sortColumn === 'amount') {
      return sortDirection === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
    }
    
    if (sortColumn === 'date') {
      const aDate = new Date(aVal as string);
      const bDate = new Date(bVal as string);
      return sortDirection === 'asc' ? aDate.getTime() - bDate.getTime() : bDate.getTime() - aDate.getTime();
    }
    
    const aStr = String(aVal).toLowerCase();
    const bStr = String(bVal).toLowerCase();
    return sortDirection === 'asc' ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
  });

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

      // Update local state
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update transaction');
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

      // Update local state
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

  if (!isOpen) return null;

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        {/* Header */}
        <div className={styles.header}>
          <div>
            <h2 className={styles.title}>
              {title || 'Transaction Details'}
            </h2>
            {(category || startDate) && (
              <p className={styles.subtitle}>
                {category && subcategory ? `${category}/${subcategory}` : category}
                {startDate && endDate && ` • ${formatDate(startDate)} - ${formatDate(endDate)}`}
                {` • ${transactions.length} transactions`}
              </p>
            )}
          </div>
          <button onClick={onClose} className={styles.closeButton}>
            ×
          </button>
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
                const subcategoryId = null; // Reset subcategory when changing category
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

        {/* Content */}
        <div className={styles.content}>
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
                    {(['date', 'payee', 'description', 'amount', 'category', 'subcategory'] as const).map(column => (
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
                  {sortedTransactions.map((transaction, index) => (
                    <tr 
                      key={transaction.id}
                      className={`${styles.tableRow} ${index % 2 === 0 ? styles.tableRowEven : styles.tableRowOdd}`}
                    >
                      <td className={styles.tableCell}>
                        <input
                          type="checkbox"
                          checked={selectedTransactions.has(transaction.id)}
                          onChange={() => toggleTransactionSelection(transaction.id)}
                        />
                      </td>
                      <td className={styles.tableCell}>
                        {formatDate(transaction.date)}
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
                          <select
                            value={transaction.category_id || ''}
                            onChange={(e) => {
                              const categoryId = parseInt(e.target.value) || null;
                              handleTransactionUpdate(transaction.id, categoryId, null);
                            }}
                            className={styles.categorySelect}
                          >
                            <option value="">Uncategorized</option>
                            {categories.map(cat => (
                              <option key={cat.id} value={cat.id}>{cat.name}</option>
                            ))}
                          </select>
                        ) : (
                          <span
                            onClick={() => setEditingTransaction(transaction.id)}
                            className={`${styles.categorySpan} ${transaction.category ? styles.categorized : styles.uncategorized}`}
                          >
                            {transaction.category || 'Uncategorized'}
                          </span>
                        )}
                      </td>
                      <td className={`${styles.tableCell} ${styles.tableCellCategory}`}>
                        {editingTransaction === transaction.id && transaction.category_id ? (
                          <select
                            value={transaction.subcategory_id || ''}
                            onChange={(e) => {
                              const subcategoryId = parseInt(e.target.value) || null;
                              handleTransactionUpdate(transaction.id, transaction.category_id, subcategoryId);
                            }}
                            className={styles.categorySelect}
                          >
                            <option value="">None</option>
                            {subcategories
                              .filter(sub => sub.category_id === transaction.category_id)
                              .map(sub => (
                                <option key={sub.id} value={sub.id}>{sub.name}</option>
                              ))}
                          </select>
                        ) : (
                          <span
                            onClick={() => transaction.category_id && setEditingTransaction(transaction.id)}
                            className={`${styles.categorySpan} ${transaction.subcategory ? styles.categorized : ''} ${!transaction.category_id ? styles.subcategorySpanDisabled : ''}`}
                          >
                            {transaction.subcategory || (transaction.category_id ? 'None' : '-')}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};