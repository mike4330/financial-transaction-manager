import React, { useState, useEffect } from 'react';
import styles from './RecurringPatterns.module.css';
import BalanceProjectionView from './BalanceProjectionView';
import DetectPatternsView from './DetectPatternsView';

interface Pattern {
  id?: number;
  pattern_name: string;
  account_number: string;
  payee: string;
  typical_amount: number;
  amount_variance: number;
  frequency_type: string;
  frequency_interval: number;
  next_expected_date: string;
  last_occurrence_date: string;
  confidence: number;
  confidence_level: string;
  occurrence_count: number;
  pattern_type?: string;
  is_active?: boolean;
  category?: string;
  subcategory?: string;
}

interface SavedPatternsResponse {
  patterns: Pattern[];
  total_count: number;
}

const RecurringPatterns: React.FC = () => {
  const [view, setView] = useState<'saved' | 'detect' | 'projection'>('saved');
  const [savedPatterns, setSavedPatterns] = useState<Pattern[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Table sorting state
  const [sortColumn, setSortColumn] = useState<'pattern' | 'account' | 'amount' | 'frequency' | 'confidence' | 'next_due'>('amount');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  
  // Edit pattern state
  const [editingPattern, setEditingPattern] = useState<Pattern | null>(null);
  const [editForm, setEditForm] = useState<Partial<Pattern>>({});

  // Estimated pattern creation state
  const [showEstimatedModal, setShowEstimatedModal] = useState(false);
  const [availableCategories, setAvailableCategories] = useState<string[]>([]);
  const [estimatedForm, setEstimatedForm] = useState({
    category: '',
    subcategory: '',
    frequency: 'biweekly',
    lookbackDays: 120
  });
  const [categoryStats, setCategoryStats] = useState<any>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  // Load saved patterns on component mount
  useEffect(() => {
    if (view === 'saved') {
      loadSavedPatterns();
    }
  }, [view]);
  
  // Load available categories when modal opens
  useEffect(() => {
    if (showEstimatedModal) {
      loadAvailableCategories();
    }
  }, [showEstimatedModal]);

  const loadSavedPatterns = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/recurring-patterns');
      if (!response.ok) throw new Error('Failed to load saved patterns');
      
      const data: SavedPatternsResponse = await response.json();
      setSavedPatterns(data.patterns);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load saved patterns');
    } finally {
      setLoading(false);
    }
  };

  const handleDetectSaveSuccess = () => {
    setView('saved');
    loadSavedPatterns();
  };

  const deactivatePattern = async (patternId: number) => {
    if (!confirm('Are you sure you want to deactivate this pattern?')) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/recurring-patterns/${patternId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        loadSavedPatterns(); // Reload patterns
      } else {
        throw new Error('Failed to deactivate pattern');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deactivate pattern');
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (column: typeof sortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  const sortedPatterns = [...savedPatterns].sort((a, b) => {
    let aValue: any, bValue: any;
    
    switch (sortColumn) {
      case 'pattern':
        aValue = a.pattern_name.toLowerCase();
        bValue = b.pattern_name.toLowerCase();
        break;
      case 'account':
        aValue = a.account_number;
        bValue = b.account_number;
        break;
      case 'amount':
        aValue = a.typical_amount;
        bValue = b.typical_amount;
        break;
      case 'frequency':
        aValue = a.frequency_type;
        bValue = b.frequency_type;
        break;
      case 'confidence':
        aValue = a.confidence;
        bValue = b.confidence;
        break;
      case 'next_due':
        aValue = new Date(a.next_expected_date).getTime();
        bValue = new Date(b.next_expected_date).getTime();
        break;
      default:
        return 0;
    }
    
    if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  const startEdit = (pattern: Pattern) => {
    setEditingPattern(pattern);
    setEditForm({
      pattern_name: pattern.pattern_name,
      typical_amount: pattern.typical_amount,
      frequency_type: pattern.frequency_type,
      next_expected_date: pattern.next_expected_date
    });
  };

  const cancelEdit = () => {
    setEditingPattern(null);
    setEditForm({});
  };

  const saveEdit = async () => {
    if (!editingPattern || !editingPattern.id) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/recurring-patterns/${editingPattern.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editForm),
      });

      if (response.ok) {
        setEditingPattern(null);
        setEditForm({});
        loadSavedPatterns(); // Reload patterns
      } else {
        throw new Error('Failed to update pattern');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update pattern');
    } finally {
      setLoading(false);
    }
  };
  
  const loadAvailableCategories = async () => {
    try {
      const response = await fetch('/api/categories');
      if (response.ok) {
        const data = await response.json();
        // API returns categories as objects with id and name, extract just the names
        const categoryNames = data.categories.map((cat: any) => cat.name);
        setAvailableCategories(categoryNames);
      }
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  };
  
  const computeCategoryStats = async () => {
    if (!estimatedForm.category) {
      setError('Please select a category first');
      return;
    }
    
    setStatsLoading(true);
    setCategoryStats(null);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        category: estimatedForm.category,
        subcategory: estimatedForm.subcategory || '',
        frequency: estimatedForm.frequency,
        lookback_days: estimatedForm.lookbackDays.toString()
      });
      
      const url = `/api/category-spending-analysis?${params}`;
      console.log('Calling API:', url);
      const response = await fetch(url);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`Failed to compute category statistics: ${response.status} ${response.statusText}. ${errorData.error || ''}`);
      }
      
      const data = await response.json();
      setCategoryStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compute statistics');
    } finally {
      setStatsLoading(false);
    }
  };
  
  const createEstimatedPattern = async () => {
    if (!categoryStats) {
      setError('Please compute statistics first');
      return;
    }
    
    setLoading(true);
    try {
      // Calculate dates based on frequency
      const frequencyDays = {
        'weekly': 7,
        'biweekly': 14,
        'monthly': 30
      };
      const daysToNext = frequencyDays[estimatedForm.frequency as keyof typeof frequencyDays] || 14;
      
      const nextDate = new Date(Date.now() + daysToNext * 24 * 60 * 60 * 1000);
      const lastDate = new Date(Date.now() - daysToNext * 24 * 60 * 60 * 1000);
      
      const patternData = {
        pattern_name: `${estimatedForm.category} (Estimated)`,
        account_number: 'Z06431462', // Primary account for estimated patterns
        payee: `${estimatedForm.category} Spending Estimate`,
        typical_amount: categoryStats.mean,
        amount_variance: categoryStats.std_dev,
        frequency_type: estimatedForm.frequency,
        frequency_interval: 1,
        next_expected_date: nextDate.toISOString().split('T')[0],
        last_occurrence_date: lastDate.toISOString().split('T')[0],
        confidence: Math.max(30, Math.min(80, 100 - categoryStats.cv * 100)) / 100, // Convert to 0-1 range
        occurrence_count: categoryStats.periods.filter((p: any) => p.total > 0).length,
        pattern_type: 'estimated'
      };
      
      const response = await fetch('/api/recurring-patterns/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(patternData),
      });
      
      if (!response.ok) throw new Error('Failed to create estimated pattern');
      
      // Close modal and refresh patterns
      setShowEstimatedModal(false);
      setEstimatedForm({ category: '', subcategory: '', frequency: 'biweekly', lookbackDays: 120 });
      setCategoryStats(null);
      loadSavedPatterns();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create estimated pattern');
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (level: string) => {
    switch (level) {
      case 'high': return '#10b981'; // green
      case 'medium': return '#f59e0b'; // yellow
      case 'low': return '#ef4444'; // red
      default: return '#6b7280'; // gray
    }
  };

  const formatCurrency = (amount: number, variance: number = 0) => {
    const formatted = `$${Math.abs(amount).toFixed(2)}`;
    return variance > 0 ? `${formatted} ±$${variance.toFixed(0)}` : formatted;
  };

  const formatFrequency = (type: string, interval: number = 1) => {
    const freq = interval > 1 ? `${type} (every ${interval})` : type;
    return freq.charAt(0).toUpperCase() + freq.slice(1);
  };

  return (
    <div className={styles['recurring-patterns']}>
      <div className={styles.header}>
        <h1>Recurring Patterns</h1>
        <p>Manage recurring transactions for accurate balance projections</p>
        
        <div className={styles['header-controls']}>
          <div className={styles['view-toggle']}>
            <button 
              className={view === 'saved' ? styles.active : ''} 
              onClick={() => setView('saved')}
            >
              Saved Patterns ({savedPatterns.length})
            </button>
            <button 
              className={view === 'detect' ? styles.active : ''} 
              onClick={() => setView('detect')}
            >
              Detect New Patterns
            </button>
            <button 
              className={view === 'projection' ? styles.active : ''} 
              onClick={() => setView('projection')}
            >
              Balance Projection
            </button>
          </div>
          
          <div className={styles['header-actions']}>
            <button 
              onClick={() => setShowEstimatedModal(true)}
              className={styles['create-estimated-button']}
            >
              Insert Placeholder Pattern
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className={styles['error-message']}>
          {error}
        </div>
      )}

      {view === 'detect' && (
        <DetectPatternsView
          onError={setError}
          onSaveSuccess={handleDetectSaveSuccess}
        />
      )}

      {view === 'saved' && (
        <div className={styles['saved-section']}>
          <div className={styles['saved-header']}>
            <h2>Active Recurring Patterns</h2>
            <p>These patterns are used for balance projections</p>
          </div>

          <div className={styles['saved-patterns-table']}>
            <table>
              <thead>
                <tr>
                  <th onClick={() => handleSort('pattern')} className={styles['sortable-header']}>
                    Pattern {sortColumn === 'pattern' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('account')} className={styles['sortable-header']}>
                    Account {sortColumn === 'account' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('amount')} className={styles['sortable-header']}>
                    Amount {sortColumn === 'amount' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('frequency')} className={styles['sortable-header']}>
                    Frequency {sortColumn === 'frequency' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('confidence')} className={styles['sortable-header']}>
                    Confidence {sortColumn === 'confidence' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => handleSort('next_due')} className={styles['sortable-header']}>
                    Next Due {sortColumn === 'next_due' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sortedPatterns.map((pattern) => (
                  <tr key={pattern.id}>
                    <td>
                      {editingPattern?.id === pattern.id ? (
                        <input 
                          type="text" 
                          value={editForm.pattern_name || ''}
                          onChange={(e) => setEditForm({...editForm, pattern_name: e.target.value})}
                          className={styles['edit-input']}
                          placeholder="Pattern name"
                        />
                      ) : (
                        <>
                          <div className={styles['pattern-name']}>{pattern.pattern_name}</div>
                          {pattern.payee && (
                            <div className={styles['pattern-payee']}>{pattern.payee}</div>
                          )}
                        </>
                      )}
                    </td>
                    <td>{pattern.account_number}</td>
                    <td>
                      {editingPattern?.id === pattern.id ? (
                        <input 
                          type="number" 
                          value={editForm.typical_amount || ''}
                          onChange={(e) => setEditForm({...editForm, typical_amount: parseFloat(e.target.value)})}
                          className={styles['edit-input-small']}
                          placeholder="Amount"
                          step="0.01"
                        />
                      ) : (
                        formatCurrency(pattern.typical_amount, pattern.amount_variance)
                      )}
                    </td>
                    <td>
                      {editingPattern?.id === pattern.id ? (
                        <select 
                          value={editForm.frequency_type || ''}
                          onChange={(e) => setEditForm({...editForm, frequency_type: e.target.value})}
                          className={styles['edit-select']}
                        >
                          <option value="weekly">Weekly</option>
                          <option value="biweekly">Biweekly</option>
                          <option value="monthly">Monthly</option>
                          <option value="quarterly">Quarterly</option>
                          <option value="annual">Annual</option>
                        </select>
                      ) : (
                        formatFrequency(pattern.frequency_type, pattern.frequency_interval)
                      )}
                    </td>
                    <td>
                      <div 
                        className={styles['confidence-indicator']}
                        style={{ backgroundColor: getConfidenceColor(pattern.confidence_level) }}
                      >
                        {pattern.confidence.toFixed(1)}%
                      </div>
                    </td>
                    <td>
                      {editingPattern?.id === pattern.id ? (
                        <input 
                          type="date" 
                          value={editForm.next_expected_date || ''}
                          onChange={(e) => setEditForm({...editForm, next_expected_date: e.target.value})}
                          className={styles['edit-input']}
                        />
                      ) : (
                        pattern.next_expected_date
                      )}
                    </td>
                    <td>
                      <div className={styles['action-buttons']}>
                        {editingPattern?.id === pattern.id ? (
                          <>
                            <button 
                              onClick={saveEdit}
                              className={styles['save-edit-button']}
                              disabled={loading}
                            >
                              ✓
                            </button>
                            <button 
                              onClick={cancelEdit}
                              className={styles['cancel-edit-button']}
                            >
                              ✕
                            </button>
                          </>
                        ) : (
                          <>
                            <button 
                              onClick={() => startEdit(pattern)}
                              className={styles['edit-button']}
                            >
                              Edit
                            </button>
                            <button 
                              onClick={() => pattern.id && deactivatePattern(pattern.id)}
                              className={styles['deactivate-button']}
                            >
                              Deactivate
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {savedPatterns.length === 0 && !loading && (
              <div className={styles['empty-state']}>
                No saved patterns yet. Switch to "Detect New Patterns" to find and save recurring transactions.
              </div>
            )}
          </div>
        </div>
      )}

      {view === 'projection' && (
        <BalanceProjectionView onError={setError} />
      )}

      {/* Estimated Pattern Creation Modal */}
      {showEstimatedModal && (
        <div className={styles['modal-overlay']}>
          <div className={styles['modal-content']}>
            <div className={styles['modal-header']}>
              <h2>Create Estimated Pattern</h2>
              <button 
                onClick={() => {
                  setShowEstimatedModal(false);
                  setCategoryStats(null);
                  setEstimatedForm({ category: '', subcategory: '', frequency: 'biweekly', lookbackDays: 120 });
                }}
                className={styles['modal-close']}
              >
                ×
              </button>
            </div>
            
            <div className={styles['modal-body']}>
              <div className={styles['form-section']}>
                <h3>Pattern Configuration</h3>
                
                <div className={styles['form-row']}>
                  <div className={styles['form-group']}>
                    <label>Category:</label>
                    <select 
                      value={estimatedForm.category}
                      onChange={(e) => {
                        setEstimatedForm({...estimatedForm, category: e.target.value});
                        setCategoryStats(null); // Clear stats when category changes
                      }}
                      className={styles['form-select']}
                    >
                      <option value="">Select Category</option>
                      {availableCategories.map(cat => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div className={styles['form-group']}>
                    <label>Subcategory (Optional):</label>
                    <input 
                      type="text"
                      value={estimatedForm.subcategory}
                      onChange={(e) => {
                        setEstimatedForm({...estimatedForm, subcategory: e.target.value});
                        setCategoryStats(null);
                      }}
                      className={styles['form-input']}
                      placeholder="Leave blank for all subcategories"
                    />
                  </div>
                </div>
                
                <div className={styles['form-row']}>
                  <div className={styles['form-group']}>
                    <label>Frequency:</label>
                    <select 
                      value={estimatedForm.frequency}
                      onChange={(e) => {
                        setEstimatedForm({...estimatedForm, frequency: e.target.value});
                        setCategoryStats(null);
                      }}
                      className={styles['form-select']}
                    >
                      <option value="weekly">Weekly</option>
                      <option value="biweekly">Biweekly</option>
                      <option value="monthly">Monthly</option>
                    </select>
                  </div>
                  
                  <div className={styles['form-group']}>
                    <label>Lookback Days:</label>
                    <input 
                      type="number"
                      value={estimatedForm.lookbackDays}
                      onChange={(e) => {
                        setEstimatedForm({...estimatedForm, lookbackDays: parseInt(e.target.value)});
                        setCategoryStats(null);
                      }}
                      className={styles['form-input']}
                      min="30"
                      max="365"
                      step="30"
                    />
                  </div>
                </div>
                
                <div className={styles['compute-section']}>
                  <button 
                    onClick={computeCategoryStats}
                    disabled={!estimatedForm.category || statsLoading}
                    className={styles['compute-button']}
                  >
                    {statsLoading ? 'Computing...' : 'Compute Statistics'}
                  </button>
                </div>
              </div>
              
              {categoryStats && (
                <div className={styles['stats-section']}>
                  <h3>Statistical Analysis</h3>
                  
                  <div className={styles['stats-grid']}>
                    <div className={styles['stat-card']}>
                      <div className={styles['stat-label']}>Average per {estimatedForm.frequency}</div>
                      <div className={styles['stat-value']}>${categoryStats.mean.toFixed(2)}</div>
                    </div>
                    
                    <div className={styles['stat-card']}>
                      <div className={styles['stat-label']}>Standard Deviation</div>
                      <div className={styles['stat-value']}>${categoryStats.std_dev.toFixed(2)}</div>
                    </div>
                    
                    <div className={styles['stat-card']}>
                      <div className={styles['stat-label']}>Coefficient of Variation</div>
                      <div className={styles['stat-value']}>{(categoryStats.cv * 100).toFixed(1)}%</div>
                    </div>
                    
                    <div className={styles['stat-card']}>
                      <div className={styles['stat-label']}>Range</div>
                      <div className={styles['stat-value']}>${categoryStats.min.toFixed(2)} - ${categoryStats.max.toFixed(2)}</div>
                    </div>
                  </div>
                  
                  <div className={styles['predictability-section']}>
                    <div className={styles['predictability-rating']}>
                      <strong>Predictability: {categoryStats.predictability_rating}</strong>
                    </div>
                    <div className={styles['confidence-info']}>
                      Suggested confidence: {Math.max(30, Math.min(80, 100 - categoryStats.cv * 100)).toFixed(0)}%
                    </div>
                  </div>
                  
                  <div className={styles['period-breakdown']}>
                    <h4>Period Breakdown:</h4>
                    <div className={styles['periods-list']}>
                      {categoryStats.periods.map((period: any, index: number) => (
                        <div key={index} className={styles['period-item']}>
                          <span className={styles['period-dates']}>
                            {period.start} - {period.end}
                          </span>
                          <span className={styles['period-amount']}>
                            ${period.total.toFixed(2)}
                          </span>
                          <span className={`${styles['period-deviation']} ${period.deviation >= 0 ? styles.positive : styles.negative}`}>
                            {period.deviation >= 0 ? '+' : ''}{period.deviation.toFixed(1)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            <div className={styles['modal-footer']}>
              <button 
                onClick={() => {
                  setShowEstimatedModal(false);
                  setCategoryStats(null);
                  setEstimatedForm({ category: '', subcategory: '', frequency: 'biweekly', lookbackDays: 120 });
                }}
                className={styles['cancel-button']}
              >
                Cancel
              </button>
              <button 
                onClick={createEstimatedPattern}
                disabled={!categoryStats || loading}
                className={styles['create-button']}
              >
                {loading ? 'Creating...' : 'Create Pattern'}
              </button>
            </div>
          </div>
        </div>
      )}

      {loading && (
        <div className={styles['loading-overlay']}>
          <div className={styles['loading-spinner']}>Loading...</div>
        </div>
      )}
    </div>
  );
};

export default RecurringPatterns;