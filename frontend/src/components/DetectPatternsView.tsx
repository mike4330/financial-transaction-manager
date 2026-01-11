import React, { useState } from 'react';
import styles from './RecurringPatterns.module.css';

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

interface DetectPatternsViewProps {
  onError?: (error: string) => void;
  onSaveSuccess?: () => void;
}

const DetectPatternsView: React.FC<DetectPatternsViewProps> = ({ onError, onSaveSuccess }) => {
  const [detectedPatterns, setDetectedPatterns] = useState<Pattern[]>([]);
  const [selectedPatterns, setSelectedPatterns] = useState<Set<number>>(new Set());
  const [lookbackDays, setLookbackDays] = useState(365);
  const [loading, setLoading] = useState(false);

  const detectPatterns = async () => {
    setLoading(true);
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
      const errorMessage = err instanceof Error ? err.message : 'Failed to detect patterns';
      if (onError) {
        onError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const saveSelectedPatterns = async () => {
    const patternsToSave = detectedPatterns.filter((_, index) => selectedPatterns.has(index));

    if (patternsToSave.length === 0) {
      if (onError) {
        onError('No patterns selected');
      }
      return;
    }

    setLoading(true);

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
        setDetectedPatterns([]); // Clear detected patterns

        // Notify parent to switch view and reload
        if (onSaveSuccess) {
          onSaveSuccess();
        }
      } else {
        throw new Error(`Failed to save any patterns (${failed} failures)`);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save patterns';
      if (onError) {
        onError(errorMessage);
      }
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
  );
};

DetectPatternsView.displayName = 'DetectPatternsView';

export default DetectPatternsView;
