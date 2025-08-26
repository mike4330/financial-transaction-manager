import React, { useState, useEffect } from 'react';
import styles from './PayeeManager.module.css';
import Dialog from './Dialog';

interface PayeePattern {
  id: number;
  name: string;
  pattern: string;
  replacement: string;
  is_regex: boolean;
  is_active: boolean;
  created_by: string;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

interface PatternFormData {
  name: string;
  pattern: string;
  replacement: string;
  is_regex: boolean;
  is_active: boolean;
}

const PayeeManager: React.FC = () => {
  const [patterns, setPatterns] = useState<PayeePattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingPattern, setEditingPattern] = useState<PayeePattern | null>(null);
  const [formData, setFormData] = useState<PatternFormData>({
    name: '',
    pattern: '',
    replacement: '',
    is_regex: false,
    is_active: true
  });
  const [testText, setTestText] = useState('BILL PAYMENT NOVEC (Cash)');
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const [applyingPattern, setApplyingPattern] = useState<number | null>(null);
  const [previewData, setPreviewData] = useState<any>(null);
  const [showPreviewDialog, setShowPreviewDialog] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showSuccessDialog, setShowSuccessDialog] = useState(false);

  // Load patterns on component mount
  useEffect(() => {
    fetchPatterns();
  }, []);

  const fetchPatterns = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/payee-patterns');
      if (!response.ok) {
        throw new Error(`Failed to fetch patterns: ${response.statusText}`);
      }
      const data = await response.json();
      setPatterns(data.patterns || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load patterns');
      console.error('Error fetching patterns:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      const url = editingPattern ? `/api/payee-patterns/${editingPattern.id}` : '/api/payee-patterns';
      const method = editingPattern ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Failed to ${editingPattern ? 'update' : 'create'} pattern`);
      }

      await fetchPatterns(); // Refresh the list
      handleCloseDialog();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save pattern');
      console.error('Error saving pattern:', err);
    }
  };

  const handleEdit = (pattern: PayeePattern) => {
    setEditingPattern(pattern);
    setFormData({
      name: pattern.name,
      pattern: pattern.pattern,
      replacement: pattern.replacement,
      is_regex: pattern.is_regex,
      is_active: pattern.is_active
    });
    setIsDialogOpen(true);
  };

  const handleDelete = async (pattern: PayeePattern) => {
    if (!window.confirm(`Are you sure you want to delete the pattern "${pattern.name}"?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/payee-patterns/${pattern.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete pattern');
      }

      await fetchPatterns(); // Refresh the list
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete pattern');
      console.error('Error deleting pattern:', err);
    }
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setEditingPattern(null);
    setFormData({
      name: '',
      pattern: '',
      replacement: '',
      is_regex: false,
      is_active: true
    });
    setTestResult(null);
    setTestError(null);
  };

  const handleTestPattern = async () => {
    if (!formData.pattern || !formData.replacement || !testText) {
      setTestError('Please fill in pattern, replacement, and test text');
      return;
    }

    try {
      const response = await fetch('/api/payee-patterns/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          pattern: formData.pattern,
          replacement: formData.replacement,
          test_text: testText,
          is_regex: formData.is_regex
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to test pattern');
      }

      const data = await response.json();
      if (data.error) {
        setTestError(data.error);
        setTestResult(null);
      } else {
        setTestResult(data.result);
        setTestError(null);
      }
    } catch (err) {
      setTestError(err instanceof Error ? err.message : 'Failed to test pattern');
      setTestResult(null);
    }
  };

  const handlePreviewPattern = async (pattern: PayeePattern) => {
    try {
      setApplyingPattern(pattern.id);
      setPreviewData(null); // Clear previous data
      setError(null); // Clear any previous errors
      setShowPreviewDialog(true); // Open dialog immediately to show loading
      
      console.log('Previewing pattern:', pattern.id, pattern.name);
      
      const response = await fetch(`/api/payee-patterns/${pattern.id}/apply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ preview: true }),
      });

      console.log('Preview response status:', response.status);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}: Failed to preview pattern`);
      }

      const data = await response.json();
      console.log('Preview data received:', data);
      
      setPreviewData(data);
      setError(null);
    } catch (err) {
      console.error('Preview error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to preview pattern';
      setError(errorMessage);
      // Keep dialog open to show error
    } finally {
      setApplyingPattern(null);
    }
  };

  const handleApplyPattern = async (pattern: PayeePattern, skipPreview = false) => {
    if (!skipPreview) {
      await handlePreviewPattern(pattern);
      return;
    }

    try {
      setApplyingPattern(pattern.id);
      const response = await fetch(`/api/payee-patterns/${pattern.id}/apply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ preview: false }),
      });

      if (!response.ok) {
        throw new Error('Failed to apply pattern');
      }

      const data = await response.json();
      
      // Show success message and refresh patterns to update usage count
      setSuccessMessage(`Successfully applied "${pattern.name}" to ${data.updated_count} transactions!`);
      setShowSuccessDialog(true);
      await fetchPatterns();
      setShowPreviewDialog(false);
      setPreviewData(null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply pattern');
    } finally {
      setApplyingPattern(null);
    }
  };

  const handleClosePreviewDialog = () => {
    setShowPreviewDialog(false);
    setPreviewData(null);
    setApplyingPattern(null); // Clear applying state
  };

  if (loading) {
    return <div className={styles.loading}>Loading payee patterns...</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Payee Pattern Manager</h1>
        <p>Manage extraction patterns for automatic payee detection from transaction actions.</p>
        <button 
          className={styles.addButton}
          onClick={() => setIsDialogOpen(true)}
        >
          + Add New Pattern
        </button>
      </div>

      {error && (
        <div className={styles.error}>
          {error}
        </div>
      )}

      <div className={styles.patternsGrid}>
        <div className={styles.gridHeader}>
          <div>Name</div>
          <div>Pattern</div>
          <div>Replacement</div>
          <div>Type</div>
          <div>Status</div>
          <div>Usage</div>
          <div>Apply</div>
          <div>Actions</div>
        </div>
        
        {patterns.length === 0 ? (
          <div className={styles.emptyState}>
            No patterns found. Create your first pattern to get started!
          </div>
        ) : (
          patterns.map(pattern => (
            <div key={pattern.id} className={styles.gridRow}>
              <div className={styles.patternName}>{pattern.name}</div>
              <div className={styles.patternText}>{pattern.pattern}</div>
              <div className={styles.replacement}>{pattern.replacement}</div>
              <div className={styles.type}>
                <span className={pattern.is_regex ? styles.regexBadge : styles.textBadge}>
                  {pattern.is_regex ? 'Regex' : 'Text'}
                </span>
              </div>
              <div className={styles.status}>
                <span className={pattern.is_active ? styles.activeBadge : styles.inactiveBadge}>
                  {pattern.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <div className={styles.usage}>{pattern.usage_count}</div>
              <div className={styles.apply}>
                <button 
                  className={styles.previewButton}
                  onClick={() => handlePreviewPattern(pattern)}
                  disabled={!pattern.is_active || applyingPattern === pattern.id}
                  title="Preview what transactions would be updated"
                >
                  {applyingPattern === pattern.id ? '⏳' : '▶️'}
                </button>
              </div>
              <div className={styles.actions}>
                <button 
                  className={styles.editButton}
                  onClick={() => handleEdit(pattern)}
                  title="Edit pattern"
                >
                  ✏️
                </button>
                <button 
                  className={styles.deleteButton}
                  onClick={() => handleDelete(pattern)}
                  title="Delete pattern"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <Dialog 
        isOpen={isDialogOpen} 
        onClose={handleCloseDialog}
        title={editingPattern ? 'Edit Payee Pattern' : 'Add New Payee Pattern'}
      >
        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.formGroup}>
            <label htmlFor="name">Pattern Name:</label>
            <input
              type="text"
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., NOVEC Bill Payment"
              required
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="pattern">Pattern:</label>
            <input
              type="text"
              id="pattern"
              value={formData.pattern}
              onChange={(e) => setFormData({ ...formData, pattern: e.target.value })}
              placeholder="e.g., BILL PAYMENT NOVEC"
              required
            />
            <small>
              {formData.is_regex 
                ? 'Enter a regular expression pattern' 
                : 'Enter text that should match in the transaction action'
              }
            </small>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="replacement">Payee Name:</label>
            <input
              type="text"
              id="replacement"
              value={formData.replacement}
              onChange={(e) => setFormData({ ...formData, replacement: e.target.value })}
              placeholder="e.g., NOVEC"
              required
            />
            <small>The payee name that will be assigned to matching transactions</small>
          </div>

          <div className={styles.checkboxGroup}>
            <label>
              <input
                type="checkbox"
                checked={formData.is_regex}
                onChange={(e) => setFormData({ ...formData, is_regex: e.target.checked })}
              />
              Use regular expression pattern
            </label>
            <label>
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              />
              Pattern is active
            </label>
          </div>

          <div className={styles.testSection}>
            <h3>Test Pattern</h3>
            <div className={styles.formGroup}>
              <label htmlFor="testText">Test Text:</label>
              <input
                type="text"
                id="testText"
                value={testText}
                onChange={(e) => setTestText(e.target.value)}
                placeholder="Enter transaction action to test"
              />
              <button type="button" onClick={handleTestPattern} className={styles.testButton}>
                Test Pattern
              </button>
            </div>
            
            {testResult && (
              <div className={styles.testResult}>
                <strong>Result:</strong> {testResult}
              </div>
            )}
            
            {testError && (
              <div className={styles.testError}>
                <strong>Error:</strong> {testError}
              </div>
            )}
          </div>

          <div className={styles.formActions}>
            <button type="button" onClick={handleCloseDialog} className={styles.cancelButton}>
              Cancel
            </button>
            <button type="submit" className={styles.saveButton}>
              {editingPattern ? 'Update Pattern' : 'Create Pattern'}
            </button>
          </div>
        </form>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog 
        isOpen={showPreviewDialog} 
        onClose={handleClosePreviewDialog}
        title={`Preview: ${previewData?.pattern_name || 'Pattern'}`}
      >
        {error ? (
          <div className={styles.error}>
            <p>Error loading preview: {error}</p>
            <button onClick={handleClosePreviewDialog} className={styles.cancelButton}>
              Close
            </button>
          </div>
        ) : !previewData ? (
          <div className={styles.loading}>Loading preview...</div>
        ) : (
          <div className={styles.previewContent}>
            <div className={styles.previewSummary}>
              <h3>Preview Results</h3>
              <p>
                Found <strong>{previewData.matches_found || 0}</strong> transactions that would be updated.
                {previewData.total_matches > 50 && (
                  <span className={styles.truncatedNote}>
                    {' '}(Showing first 50 for preview)
                  </span>
                )}
              </p>
            </div>

            {(previewData.matches_found || 0) > 0 ? (
              <>
                <div className={styles.previewTable}>
                  <div className={styles.previewHeader}>
                    <div>ID</div>
                    <div>Date</div>
                    <div>Action</div>
                    <div>Current</div>
                    <div>New Payee</div>
                    <div>Amount</div>
                  </div>
                  {(previewData.matches || []).slice(0, 10).map((match: any) => (
                    <div key={match.id} className={styles.previewRow}>
                      <div>{match.id}</div>
                      <div>{match.date}</div>
                      <div className={styles.actionColumn}>{match.action}</div>
                      <div className={styles.currentPayee}>{match.current_payee || 'None'}</div>
                      <div className={styles.newPayee}>{match.new_payee}</div>
                      <div>${match.amount?.toFixed(2) || '0.00'}</div>
                    </div>
                  ))}
                  {(previewData.matches || []).length > 10 && (
                    <div className={styles.previewMore}>
                      ... and {(previewData.matches || []).length - 10} more transactions
                    </div>
                  )}
                </div>

                <div className={styles.previewActions}>
                  <button 
                    onClick={handleClosePreviewDialog} 
                    className={styles.cancelButton}
                  >
                    Cancel
                  </button>
                  <button 
                    onClick={() => {
                      const targetPattern = patterns.find(p => p.name === previewData.pattern_name);
                      if (targetPattern) {
                        handleApplyPattern(targetPattern, true);
                      }
                    }}
                    className={styles.applyButton}
                    disabled={applyingPattern !== null}
                  >
                    {applyingPattern ? 'Applying...' : `Apply to ${previewData.matches_found || 0} Transactions`}
                  </button>
                </div>
              </>
            ) : (
              <div className={styles.noMatches}>
                <p>No transactions found that match this pattern.</p>
                <button onClick={handleClosePreviewDialog} className={styles.cancelButton}>
                  Close
                </button>
              </div>
            )}
          </div>
        )}
      </Dialog>

      {/* Success Dialog */}
      <Dialog 
        isOpen={showSuccessDialog} 
        onClose={() => setShowSuccessDialog(false)}
        title="Success"
        message={successMessage || ''}
        type="success"
        confirmText="OK"
      />
    </div>
  );
};

export default PayeeManager;