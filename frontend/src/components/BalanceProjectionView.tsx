import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts';
import { useTheme } from '../contexts/ThemeContext';
import { getGridProps, getAxisProps, getTooltipProps } from '../styles/chartTheme';
import styles from './RecurringPatterns.module.css';

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

interface BalanceProjectionViewProps {
  onError?: (error: string) => void;
}

const BalanceProjectionView: React.FC<BalanceProjectionViewProps> = ({ onError }) => {
  const [balanceProjection, setBalanceProjection] = useState<BalanceProjection | null>(null);
  const [startingBalance, setStartingBalance] = useState(15000);
  const [projectionDays, setProjectionDays] = useState(90);
  const [loading, setLoading] = useState(false);

  // Theme support for charts
  const { isDarkMode } = useTheme();
  const gridProps = getGridProps(isDarkMode);
  const axisProps = getAxisProps(isDarkMode);
  const tooltipProps = getTooltipProps(isDarkMode);

  const calculateProjection = async () => {
    setLoading(true);

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
      const errorMessage = err instanceof Error ? err.message : 'Failed to calculate balance projection';
      if (onError) {
        onError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
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
          <div className={styles['projection-summary-table']}>
            <table>
              <thead>
                <tr>
                  <th>Starting Balance</th>
                  <th>Final Balance ({projectionDays} days)</th>
                  <th>Projected Income</th>
                  <th>Projected Expenses</th>
                  <th>Net Cash Flow</th>
                  <th>Active Patterns</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className={styles['metric-value']}>
                    ${balanceProjection.starting_balance.toLocaleString()}
                  </td>
                  <td className={`${styles['metric-value']} ${balanceProjection.total_change >= 0 ? styles.positive : styles.negative}`}>
                    ${balanceProjection.final_balance.toLocaleString()}
                  </td>
                  <td className={`${styles['metric-value']} ${styles.positive}`}>
                    +${balanceProjection.projected_income.toLocaleString()}
                  </td>
                  <td className={`${styles['metric-value']} ${styles.negative}`}>
                    -${balanceProjection.projected_expenses.toLocaleString()}
                  </td>
                  <td className={`${styles['metric-value']} ${(balanceProjection.projected_income - balanceProjection.projected_expenses) >= 0 ? styles.positive : styles.negative}`}>
                    {(balanceProjection.projected_income - balanceProjection.projected_expenses) >= 0 ? '+' : ''}${(balanceProjection.projected_income - balanceProjection.projected_expenses).toLocaleString()}
                  </td>
                  <td className={styles['metric-value']}>
                    {balanceProjection.patterns_used} patterns
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className={styles['balance-chart']}>
            <h3>Balance Over Time</h3>
            <div className={styles['chart-container']}>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart
                  data={balanceProjection.daily_projections.filter((_, i) => i % Math.max(1, Math.ceil(balanceProjection.daily_projections.length / 100)) === 0)}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid {...gridProps} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(date) => {
                      // Parse YYYY-MM-DD string explicitly to avoid timezone conversion
                      const [year, month, day] = date.split('-').map(Number);
                      const parsedDate = new Date(year, month - 1, day);
                      return parsedDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                    }}
                    fontSize={12}
                    {...axisProps}
                  />
                  <YAxis
                    tickFormatter={(value) => `$${value.toLocaleString()}`}
                    fontSize={12}
                    {...axisProps}
                  />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload as DailyProjection;
                        return (
                          <div className={styles['recharts-tooltip']}>
                            <div className={styles['tooltip-content']}>
                              <div className={styles['tooltip-date']}>
                                {(() => {
                                  // Parse YYYY-MM-DD string explicitly to avoid timezone conversion
                                  const [year, month, day] = String(label).split('-').map(Number);
                                  const date = new Date(year, month - 1, day);
                                  return date.toLocaleDateString('en-US', {
                                    weekday: 'short',
                                    month: 'short',
                                    day: 'numeric'
                                  });
                                })()}
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

                  {/* Add markers for days with transactions */}
                  {balanceProjection.daily_projections
                    .filter(d => d.projected_transactions.length > 0)
                    .filter((_, i) => i % Math.max(1, Math.ceil(balanceProjection.daily_projections.filter(d => d.projected_transactions.length > 0).length / 50)) === 0)
                    .map((day, i) => {
                      const netAmount = day.projected_transactions.reduce((sum, tx) => sum + tx.amount, 0);
                      const isIncome = netAmount > 0;
                      const hasEstimatedPattern = day.projected_transactions.some(tx =>
                        tx.pattern_name && tx.pattern_name.includes('(Estimated)')
                      );

                      if (hasEstimatedPattern) {
                        // Blue triangle for estimated patterns
                        return (
                          <ReferenceDot
                            key={`${day.date}-${i}`}
                            x={day.date}
                            y={day.balance}
                            r={6}
                            fill="#3b82f6"
                            stroke="white"
                            strokeWidth={2}
                            shape={(props: any) => {
                              const { cx, cy } = props;
                              return (
                                <polygon
                                  points={`${cx},${cy-6} ${cx+5},${cy+4} ${cx-5},${cy+4}`}
                                  fill="#3b82f6"
                                  stroke="white"
                                  strokeWidth={2}
                                />
                              );
                            }}
                          />
                        );
                      } else {
                        // Regular colored dots for detected patterns
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
                      }
                    })
                  }
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={styles['upcoming-transactions']}>
            <h3>Upcoming Projected Transactions</h3>
            <div className={styles['transactions-table']}>
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Pattern Name</th>
                    <th>Payee</th>
                    <th>Amount</th>
                    <th>Type</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {balanceProjection.daily_projections
                    .filter(day => day.projected_transactions.length > 0)
                    .slice(0, 15)
                    .flatMap(day =>
                      day.projected_transactions.map(tx => ({
                        date: day.date,
                        ...tx
                      }))
                    )
                    .map((tx, index) => (
                      <tr key={index}>
                        <td className={styles['transaction-date-cell']}>
                          {(() => {
                            // Parse YYYY-MM-DD string explicitly to avoid timezone conversion
                            const [year, month, day] = tx.date.split('-').map(Number);
                            const date = new Date(year, month - 1, day);
                            return date.toLocaleDateString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
                            });
                          })()}
                        </td>
                        <td className={styles['pattern-name-cell']}>
                          <div className={styles['pattern-name-main']}>{tx.pattern_name}</div>
                          {tx.pattern_name?.includes('(Estimated)') && (
                            <span className={styles['estimated-badge']}>Estimated</span>
                          )}
                        </td>
                        <td className={styles['payee-cell']}>{tx.payee}</td>
                        <td className={`${styles['amount-cell']} ${tx.amount >= 0 ? styles.positive : styles.negative}`}>
                          {tx.amount >= 0 ? '+' : ''}${Math.abs(tx.amount).toFixed(2)}
                        </td>
                        <td className={styles['type-cell']}>
                          <span className={`${styles['type-badge']} ${tx.amount >= 0 ? styles.income : styles.expense}`}>
                            {tx.amount >= 0 ? 'Income' : 'Expense'}
                          </span>
                        </td>
                        <td className={styles['confidence-cell']}>
                          <span className={styles['confidence-badge']}>{tx.confidence}%</span>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

BalanceProjectionView.displayName = 'BalanceProjectionView';

export default BalanceProjectionView;
