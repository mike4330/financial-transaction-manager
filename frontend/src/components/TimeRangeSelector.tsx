import React from 'react';
import { useTimeRange, TimeRange } from '../contexts/TimeRangeContext';
import styles from './TimeRangeSelector.module.css';

const timeRangeOptions: { value: TimeRange; label: string }[] = [
  { value: '1M', label: '1 Month' },
  { value: '3M', label: '3 Months' },
  { value: '6M', label: '6 Months' },
  { value: '1Y', label: '1 Year' },
  { value: '2Y', label: '2 Years' },
  { value: 'ALL', label: 'All Time' },
];

export const TimeRangeSelector: React.FC = () => {
  const { timeRange, setTimeRange, startFromZero, setStartFromZero } = useTimeRange();

  return (
    <div className={styles.container}>
      {/* Time Range Selector */}
      <div className={styles.selectorGroup}>
        <span className={styles.label}>
          Time Range:
        </span>
        <div className={styles.buttonGroup}>
          {timeRangeOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => setTimeRange(option.value)}
              className={`${styles.button} ${timeRange === option.value ? styles.buttonActive : ''}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Y-Axis Control Toggle */}
      <div className={styles.selectorGroup}>
        <label className={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={startFromZero}
            onChange={(e) => setStartFromZero(e.target.checked)}
            className={styles.checkbox}
          />
          Start Y-axis from zero
        </label>
      </div>
    </div>
  );
};