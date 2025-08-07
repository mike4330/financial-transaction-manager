import React, { useState, useEffect } from 'react';
import styles from './RecurringPatterns.module.css';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceDot } from 'recharts';

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

interface DetectedPatternsResponse {
  patterns: Pattern[];
  total_detected: number;
  lookback_days: number;
}

interface SavedPatternsResponse {
  patterns: Pattern[];
  total_count: number;
}

interface BalanceProjection {
  account_name: string;
  account_number: string;
  starting_balance: number;
  final_balance: number;
  total_change: number;
  projection_days: number;
  projected_income: number;
  projected_expenses: number;
  patterns_used: number;
  daily_projections: DailyProjection[];
  generated_at: string;
}

interface DailyProjection {
  date: string;
  balance: number;
  daily_change: number;
  projected_transactions: ProjectedTransaction[];
}

interface ProjectedTransaction {
  pattern_name: string;
  payee: string;
  amount: number;
  confidence: number;
  category?: string;
  subcategory?: string;
}

const RecurringPatterns: React.FC = () => {
  const [view, setView] = useState<'saved' | 'detect' | 'projection'>('saved');
  const [detectedPatterns, setDetectedPatterns] = useState<Pattern[]>([]);
  const [savedPatterns, setSavedPatterns] = useState<Pattern[]>([]);
  const [selectedPatterns, setSelectedPatterns] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lookbackDays, setLookbackDays] = useState(365);
  const [balanceProjection, setBalanceProjection] = useState<BalanceProjection | null>(null);
  const [startingBalance, setStartingBalance] = useState(15000);
  const [projectionDays, setProjectionDays] = useState(90);
  
  // Table sorting state
  const [sortColumn, setSortColumn] = useState<'pattern' | 'account' | 'amount' | 'frequency' | 'confidence' | 'next_due'>('amount');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  
  // Edit pattern state
  const [editingPattern, setEditingPattern] = useState<Pattern | null>(null);
  const [editForm, setEditForm] = useState<Partial<Pattern>>({});

  // Load saved patterns on component mount
  useEffect(() => {
    if (view === 'saved') {
      loadSavedPatterns();
    }
  }, [view]);

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

  const detectPatterns = async () => {
    setLoading(true);
    setError(null);
    setSelectedPatterns(new Set()); // Clear selections
    
    try {
      const response = await fetch('/api/recurring-patterns/detect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          lookback_days: lookbackDays,
        }),
      });

      if (!response.ok) throw new Error('Failed to detect patterns');
      
      const data: DetectedPatternsResponse = await response.json();
      setDetectedPatterns(data.patterns);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to detect patterns');
    } finally {
      setLoading(false);
    }
  };

  const saveSelectedPatterns = async () => {
    const patternsToSave = detectedPatterns.filter((_, index) => selectedPatterns.has(index));
    
    if (patternsToSave.length === 0) {
      setError('No patterns selected');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      let saved = 0;
      let failed = 0;

      for (const pattern of patternsToSave) {
        const response = await fetch('/api/recurring-patterns/save', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(pattern),
        });

        if (response.ok) {
          saved++;
        } else {
          failed++;
        }
      }

      if (saved > 0) {
        alert(`Successfully saved ${saved} patterns${failed > 0 ? `, ${failed} failed` : ''}`);
        setSelectedPatterns(new Set()); // Clear selections
        
        // Switch to saved patterns view and reload
        setView('saved');
        loadSavedPatterns();
      } else {
        throw new Error(`Failed to save any patterns (${failed} failures)`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save patterns');
    } finally {
      setLoading(false);
    }
  };

  const togglePatternSelection = (index: number) => {
    const newSelection = new Set(selectedPatterns);
    if (newSelection.has(index)) {
      newSelection.delete(index);
    } else {
      newSelection.add(index);
    }
    setSelectedPatterns(newSelection);
  };

  const selectAll = () => {
    const highConfidencePatterns = new Set<number>();
    detectedPatterns.forEach((pattern, index) => {
      if (pattern.confidence_level === 'high') {
        highConfidencePatterns.add(index);
      }
    });
    setSelectedPatterns(highConfidencePatterns);
  };

  const clearSelection = () => {
    setSelectedPatterns(new Set());
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

  const calculateProjection = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/balance-projection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          starting_balance: startingBalance,
          projection_days: projectionDays,
        }),
      });

      if (!response.ok) throw new Error('Failed to calculate balance projection');
      
      const data: BalanceProjection = await response.json();
      setBalanceProjection(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to calculate balance projection');
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
      </div>

      {error && (
        <div className={styles['error-message']}>
          {error}
        </div>
      )}

      {view === 'detect' && (
        <div className={styles['detect-section']}>
          <div className={styles['detect-controls']}>
            <label>
              Look back days:
              <input 
                type="number" 
                value={lookbackDays} 
                onChange={(e) => setLookbackDays(Number(e.target.value))}
                min="30" 
                max="1095"
                step="30"
              />
            </label>
            <button onClick={detectPatterns} disabled={loading}>
              {loading ? 'Detecting...' : 'Detect Patterns'}
            </button>
          </div>

          {detectedPatterns.length > 0 && (
            <div className={styles['selection-controls']}>
              <div className={styles['selection-info']}>
                {selectedPatterns.size} of {detectedPatterns.length} patterns selected
              </div>
              <div className={styles['selection-buttons']}>
                <button onClick={selectAll}>Select High Confidence</button>
                <button onClick={clearSelection}>Clear Selection</button>
                <button 
                  onClick={saveSelectedPatterns} 
                  disabled={selectedPatterns.size === 0 || loading}
                  className={styles['save-button']}
                >
                  Save Selected ({selectedPatterns.size})
                </button>
              </div>
            </div>
          )}

          <div className={styles['patterns-grid']}>
            {detectedPatterns.map((pattern, index) => (
              <div 
                key={index} 
                className={`${styles['pattern-card']} ${selectedPatterns.has(index) ? styles.selected : ''}`}
                onClick={() => togglePatternSelection(index)}
              >
                <div className={styles['pattern-header']}>
                  <div className={styles['pattern-name']}>{pattern.pattern_name}</div>
                  <div 
                    className={styles['confidence-badge']}
                    style={{ backgroundColor: getConfidenceColor(pattern.confidence_level) }}
                  >
                    {pattern.confidence.toFixed(1)}%
                  </div>
                </div>
                
                <div className={styles['pattern-details']}>
                  <div className={styles.detail}>
                    <span className={styles.label}>Account:</span>
                    <span>{pattern.account_number}</span>
                  </div>
                  <div className={styles.detail}>
                    <span className={styles.label}>Amount:</span>
                    <span>{formatCurrency(pattern.typical_amount, pattern.amount_variance)}</span>
                  </div>
                  <div className={styles.detail}>
                    <span className={styles.label}>Frequency:</span>
                    <span>{formatFrequency(pattern.frequency_type, pattern.frequency_interval)}</span>
                  </div>
                  <div className={styles.detail}>
                    <span className={styles.label}>Occurrences:</span>
                    <span>{pattern.occurrence_count}</span>
                  </div>
                  <div className={styles.detail}>
                    <span className={styles.label}>Next Expected:</span>
                    <span>{pattern.next_expected_date}</span>
                  </div>
                  <div className={styles.detail}>
                    <span className={styles.label}>Type:</span>
                    <span className={styles['pattern-type']}>{pattern.pattern_type}</span>
                  </div>
                  {(pattern.category || pattern.subcategory) && (
                    <div className={styles.detail}>
                      <span className={styles.label}>Category:</span>
                      <span>
                        {pattern.category}
                        {pattern.subcategory && ` / ${pattern.subcategory}`}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
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
        <div className={styles['projection-section']}>
          <div className={styles['projection-header']}>
            <h2>Balance Projection - Individual TOD Account</h2>
            <p>Project future balance using active recurring patterns</p>
          </div>

          <div className={styles['projection-controls']}>
            <label>
              Starting Balance:
              <input 
                type="number" 
                value={startingBalance} 
                onChange={(e) => setStartingBalance(Number(e.target.value))}
                min="0"
                step="100"
              />
            </label>
            <label>
              Projection Days:
              <input 
                type="number" 
                value={projectionDays} 
                onChange={(e) => setProjectionDays(Number(e.target.value))}
                min="30"
                max="365"
                step="30"
              />
            </label>
            <button onClick={calculateProjection} disabled={loading}>
              {loading ? 'Calculating...' : 'Calculate Projection'}
            </button>
          </div>

          {balanceProjection && (
            <div className={styles['projection-results']}>
              <div className={styles['projection-summary']}>
                <div className={styles['summary-card']}>
                  <h3>Starting Balance</h3>
                  <div className={styles['amount']}>${balanceProjection.starting_balance.toLocaleString()}</div>
                </div>
                <div className={styles['summary-card']}>
                  <h3>Final Balance ({projectionDays} days)</h3>
                  <div className={`${styles['amount']} ${balanceProjection.total_change >= 0 ? styles.positive : styles.negative}`}>
                    ${balanceProjection.final_balance.toLocaleString()}
                  </div>
                </div>
                <div className={styles['summary-card']}>
                  <h3>Total Change</h3>
                  <div className={`${styles['amount']} ${balanceProjection.total_change >= 0 ? styles.positive : styles.negative}`}>
                    {balanceProjection.total_change >= 0 ? '+' : ''}${balanceProjection.total_change.toLocaleString()}
                  </div>
                </div>
                <div className={styles['summary-card']}>
                  <h3>Projected Income</h3>
                  <div className={`${styles['amount']} ${styles.positive}`}>
                    +${balanceProjection.projected_income.toLocaleString()}
                  </div>
                </div>
                <div className={styles['summary-card']}>
                  <h3>Projected Expenses</h3>
                  <div className={`${styles['amount']} ${styles.negative}`}>
                    -${balanceProjection.projected_expenses.toLocaleString()}
                  </div>
                </div>
                <div className={styles['summary-card']}>
                  <h3>Patterns Used</h3>
                  <div className={styles['count']}>{balanceProjection.patterns_used} patterns</div>
                </div>
              </div>

              <div className={styles['balance-chart']}>
                <h3>Balance Over Time</h3>
                <div className={styles['chart-container']}>
                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart
                      data={balanceProjection.daily_projections.filter((_, i) => i % Math.max(1, Math.ceil(balanceProjection.daily_projections.length / 100)) === 0)}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis 
                        dataKey="date" 
                        tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        stroke="#6b7280"
                        fontSize={12}
                      />
                      <YAxis 
                        tickFormatter={(value) => `$${value.toLocaleString()}`}
                        stroke="#6b7280"
                        fontSize={12}
                      />
                      <Tooltip
                        content={({ active, payload, label }) => {
                          if (active && payload && payload.length) {
                            const data = payload[0].payload as DailyProjection;
                            return (
                              <div className={styles['recharts-tooltip']}>
                                <div className={styles['tooltip-content']}>
                                  <div className={styles['tooltip-date']}>
                                    {new Date(label).toLocaleDateString('en-US', { 
                                      weekday: 'short', 
                                      month: 'short', 
                                      day: 'numeric' 
                                    })}
                                  </div>
                                  <div className={styles['tooltip-balance']}>
                                    Balance: ${data.balance.toLocaleString()}
                                  </div>
                                  {data.daily_change !== 0 && (
                                    <div className={`${styles['tooltip-change']} ${data.daily_change >= 0 ? styles.positive : styles.negative}`}>
                                      {data.daily_change >= 0 ? '+' : ''}${data.daily_change.toFixed(2)}
                                    </div>
                                  )}
                                  {data.projected_transactions.length > 0 && (
                                    <div className={styles['tooltip-transactions']}>
                                      {data.projected_transactions.map((tx, i) => (
                                        <div key={i} className={styles['tooltip-transaction']}>
                                          <span className={styles['tooltip-transaction-name']}>{tx.pattern_name}</span>
                                          <span className={`${styles['tooltip-transaction-amount']} ${tx.amount >= 0 ? styles.positive : styles.negative}`}>
                                            {tx.amount >= 0 ? '+' : ''}${Math.abs(tx.amount).toFixed(2)}
                                          </span>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="balance" 
                        stroke="#3b82f6" 
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4, stroke: '#3b82f6', strokeWidth: 2, fill: 'white' }}
                      />
                      
                      {/* Add dots for days with transactions */}
                      {balanceProjection.daily_projections
                        .filter(d => d.projected_transactions.length > 0)
                        .filter((_, i) => i % Math.max(1, Math.ceil(balanceProjection.daily_projections.filter(d => d.projected_transactions.length > 0).length / 50)) === 0)
                        .map((day, i) => {
                          const netAmount = day.projected_transactions.reduce((sum, tx) => sum + tx.amount, 0);
                          const isIncome = netAmount > 0;
                          const markerColor = isIncome ? '#10b981' : '#ef4444';
                          
                          return (
                            <ReferenceDot
                              key={`${day.date}-${i}`}
                              x={day.date}
                              y={day.balance}
                              r={4}
                              fill={markerColor}
                              stroke="white"
                              strokeWidth={2}
                            />
                          );
                        })
                      }
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className={styles['upcoming-transactions']}>
                <h3>Upcoming Projected Transactions</h3>
                <div className={styles['transactions-list']}>
                  {balanceProjection.daily_projections
                    .filter(day => day.projected_transactions.length > 0)
                    .slice(0, 10)
                    .map((day, dayIndex) => (
                      <div key={dayIndex} className={styles['transaction-day']}>
                        <div className={styles['transaction-date']}>{new Date(day.date).toLocaleDateString()}</div>
                        <div className={styles['day-transactions']}>
                          {day.projected_transactions.map((tx, txIndex) => (
                            <div key={txIndex} className={styles['projected-transaction']}>
                              <div className={styles['transaction-info']}>
                                <div className={styles['transaction-name']}>{tx.pattern_name}</div>
                                <div className={styles['transaction-payee']}>{tx.payee}</div>
                              </div>
                              <div className={styles['transaction-details']}>
                                <div className={`${styles['transaction-amount']} ${tx.amount >= 0 ? styles.positive : styles.negative}`}>
                                  {tx.amount >= 0 ? '+' : ''}${Math.abs(tx.amount).toFixed(2)}
                                </div>
                                <div className={styles['transaction-confidence']}>{tx.confidence}%</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          )}
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