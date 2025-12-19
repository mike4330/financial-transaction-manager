import React, { useState, useEffect } from 'react';
import { Transaction, Split, Category, Subcategory } from '../types';
import { transactionApi } from '../utils/api';
import styles from './SplitTransactionDialog.module.css';

interface SplitTransactionDialogProps {
  isOpen: boolean;
  onClose: () => void;
  transaction: Transaction;
  categories: Category[];
  subcategories: Subcategory[];
  existingSplits?: Split[];
  onSplitCreated: () => void;
}

interface SplitFormData {
  category_id: number | null;
  subcategory_id: number | null;
  amount: number;
  note: string;
  split_order: number;
}

const SplitTransactionDialog: React.FC<SplitTransactionDialogProps> = ({
  isOpen,
  onClose,
  transaction,
  categories,
  subcategories,
  existingSplits,
  onSplitCreated,
}) => {
  const [splits, setSplits] = useState<SplitFormData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize splits from existing or create two empty splits
  useEffect(() => {
    if (isOpen) {
      if (existingSplits && existingSplits.length > 0) {
        setSplits(
          existingSplits.map((split, index) => ({
            category_id: split.category_id,
            subcategory_id: split.subcategory_id,
            amount: split.amount,
            note: split.note || '',
            split_order: index,
          }))
        );
      } else {
        // Create two empty splits with default amounts
        const half = transaction.amount / 2;
        setSplits([
          {
            category_id: null,
            subcategory_id: null,
            amount: half,
            note: '',
            split_order: 0,
          },
          {
            category_id: null,
            subcategory_id: null,
            amount: half,
            note: '',
            split_order: 1,
          },
        ]);
      }
      setError(null);
    }
  }, [isOpen, transaction, existingSplits]);

  const addSplit = () => {
    const newSplit: SplitFormData = {
      category_id: null,
      subcategory_id: null,
      amount: 0,
      note: '',
      split_order: splits.length,
    };
    setSplits([...splits, newSplit]);
  };

  const removeSplit = (index: number) => {
    if (splits.length <= 2) {
      setError('At least 2 splits required');
      return;
    }
    setSplits(splits.filter((_, i) => i !== index));
  };

  const updateSplit = (index: number, field: keyof SplitFormData, value: any) => {
    const newSplits = [...splits];

    // If changing category, reset subcategory
    if (field === 'category_id') {
      newSplits[index].subcategory_id = null;
    }

    newSplits[index][field] = value;
    setSplits(newSplits);
  };

  const getFilteredSubcategories = (categoryId: number | null) => {
    if (!categoryId) return [];
    return subcategories.filter((sub) => sub.category_id === categoryId);
  };

  const calculateTotal = () => {
    return splits.reduce((sum, split) => sum + (split.amount || 0), 0);
  };

  const calculateDifference = () => {
    return Math.abs(transaction.amount - calculateTotal());
  };

  const isValid = () => {
    // Check all splits have categories
    const allHaveCategories = splits.every((split) => split.category_id !== null);

    // Check amounts sum correctly (with 0.01 tolerance)
    const difference = calculateDifference();
    const amountsMatch = difference < 0.01;

    // Check minimum 2 splits
    const enoughSplits = splits.length >= 2;

    return allHaveCategories && amountsMatch && enoughSplits;
  };

  const distributeEvenly = () => {
    if (splits.length === 0) return;

    const amountPerSplit = transaction.amount / splits.length;
    const newSplits = splits.map((split, index) => ({
      ...split,
      amount: amountPerSplit,
    }));
    setSplits(newSplits);
  };

  const handleSave = async () => {
    if (!isValid()) {
      setError('Please fill all fields and ensure amounts sum correctly');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const splitData = splits.map((split, index) => ({
        category_id: split.category_id!,
        subcategory_id: split.subcategory_id,
        amount: split.amount,
        note: split.note || null,
        split_order: index,
      }));

      if (existingSplits && existingSplits.length > 0) {
        await transactionApi.updateSplits(transaction.id, splitData);
      } else {
        await transactionApi.createSplits(transaction.id, splitData);
      }

      onSplitCreated();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to save splits');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const totalAllocated = calculateTotal();
  const difference = calculateDifference();
  const valid = isValid();

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h3 className={styles.title}>
            {existingSplits ? 'Edit' : 'Split'} Transaction
          </h3>
          <button className={styles.closeButton} onClick={onClose}>
            ×
          </button>
        </div>

        <div className={styles.transactionInfo}>
          <div className={styles.infoRow}>
            <strong>Amount:</strong> ${Math.abs(transaction.amount).toFixed(2)}
          </div>
          <div className={styles.infoRow}>
            <strong>Payee:</strong> {transaction.payee || 'N/A'}
          </div>
          <div className={styles.infoRow}>
            <strong>Date:</strong> {transaction.date}
          </div>
        </div>

        <div className={styles.content}>
          {splits.map((split, index) => (
            <div key={index} className={styles.splitRow}>
              <div className={styles.splitHeader}>
                <span className={styles.splitNumber}>Split {index + 1}</span>
                {splits.length > 2 && (
                  <button
                    className={styles.removeButton}
                    onClick={() => removeSplit(index)}
                    type="button"
                  >
                    Delete
                  </button>
                )}
              </div>

              <div className={styles.formGroup}>
                <label>Category *</label>
                <select
                  value={split.category_id || ''}
                  onChange={(e) =>
                    updateSplit(index, 'category_id', e.target.value ? parseInt(e.target.value) : null)
                  }
                  className={styles.select}
                >
                  <option value="">Select category...</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>Subcategory</label>
                <select
                  value={split.subcategory_id || ''}
                  onChange={(e) =>
                    updateSplit(index, 'subcategory_id', e.target.value ? parseInt(e.target.value) : null)
                  }
                  className={styles.select}
                  disabled={!split.category_id}
                >
                  <option value="">Select subcategory...</option>
                  {getFilteredSubcategories(split.category_id).map((sub) => (
                    <option key={sub.id} value={sub.id}>
                      {sub.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.formGroup}>
                <label>Amount *</label>
                <input
                  type="number"
                  step="0.01"
                  value={split.amount}
                  onChange={(e) => updateSplit(index, 'amount', parseFloat(e.target.value) || 0)}
                  className={styles.input}
                />
              </div>

              <div className={styles.formGroup}>
                <label>Note</label>
                <input
                  type="text"
                  value={split.note}
                  onChange={(e) => updateSplit(index, 'note', e.target.value)}
                  className={styles.input}
                  placeholder="Optional note..."
                />
              </div>
            </div>
          ))}

          <button className={styles.addButton} onClick={addSplit} type="button">
            + Add Split
          </button>

          <button
            className={styles.distributeButton}
            onClick={distributeEvenly}
            type="button"
          >
            Distribute Evenly
          </button>

          <div className={styles.validation}>
            <div className={styles.totalRow}>
              <span>Total Allocated:</span>
              <span className={valid ? styles.valid : styles.invalid}>
                ${Math.abs(totalAllocated).toFixed(2)} / ${Math.abs(transaction.amount).toFixed(2)}
              </span>
            </div>
            {difference >= 0.01 && (
              <div className={styles.errorText}>
                Difference: ${difference.toFixed(2)}
              </div>
            )}
            {!valid && splits.every(s => s.category_id !== null) && (
              <div className={styles.errorText}>
                Split amounts must equal transaction amount
              </div>
            )}
            {splits.some(s => s.category_id === null) && (
              <div className={styles.errorText}>
                All splits must have a category
              </div>
            )}
          </div>

          {error && <div className={styles.error}>{error}</div>}
        </div>

        <div className={styles.actions}>
          <button className={styles.cancelButton} onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button
            className={styles.saveButton}
            onClick={handleSave}
            disabled={!valid || loading}
          >
            {loading ? 'Saving...' : 'Save Splits'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SplitTransactionDialog;
