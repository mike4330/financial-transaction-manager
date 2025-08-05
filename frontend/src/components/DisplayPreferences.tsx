import React, { useState, useEffect } from 'react';
import { usePreferences } from '../contexts/PreferencesContext';
import styles from './DisplayPreferences.module.css';

interface DisplayPreferencesProps {
  isOpen: boolean;
  onClose: () => void;
  currentPage: 'home' | 'transactions';
}

const DisplayPreferences: React.FC<DisplayPreferencesProps> = ({ isOpen, onClose, currentPage }) => {
  const { 
    homePreferences, 
    transactionsPreferences, 
    globalPreferences,
    updateHomePreferences,
    updateTransactionsPreferences,
    updateGlobalPreferences,
    resetToDefaults
  } = usePreferences();
  
  const [availableAccounts, setAvailableAccounts] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  // Fetch available accounts when modal opens
  useEffect(() => {
    if (isOpen && currentPage === 'home') {
      fetchAccounts();
    }
  }, [isOpen, currentPage]);

  const fetchAccounts = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/filters');
      if (response.ok) {
        const data = await response.json();
        setAvailableAccounts(data.accounts || []);
      }
    } catch (error) {
      console.error('Error fetching accounts:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleSave = () => {
    onClose();
  };

  const handleReset = () => {
    if (currentPage === 'home') {
      resetToDefaults('home');
    } else if (currentPage === 'transactions') {
      resetToDefaults('transactions');
    }
    resetToDefaults('global');
  };

  const toggleAccountSelection = (account: string) => {
    const currentSelected = homePreferences.selectedAccounts;
    const newSelected = currentSelected.includes(account)
      ? currentSelected.filter(a => a !== account)
      : [...currentSelected, account];
    updateHomePreferences({ selectedAccounts: newSelected });
  };

  const getPageTitle = () => {
    switch (currentPage) {
      case 'home': return 'Dashboard Preferences';
      case 'transactions': return 'Transactions Preferences';
      default: return 'Display Preferences';
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>{getPageTitle()}</h2>
          <button className={styles.closeButton} onClick={onClose}>
            ×
          </button>
        </div>

        <div className={styles.content}>
          {/* Home Page Preferences */}
          {currentPage === 'home' && (
            <>
              {/* Account Filter Section */}
              <div className={styles.section}>
                <h3>Account Filter</h3>
                <p className={styles.sectionDescription}>
                  Select which accounts to display in the dashboard. Leave all unchecked to show all accounts.
                </p>
                {loading ? (
                  <div className={styles.loading}>Loading accounts...</div>
                ) : (
                  <div className={styles.accountGrid}>
                    {availableAccounts.map(account => (
                      <div key={account} className={styles.checkboxGroup}>
                        <label>
                          <input
                            type="checkbox"
                            checked={homePreferences.selectedAccounts.includes(account)}
                            onChange={() => toggleAccountSelection(account)}
                          />
                          {account}
                        </label>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Dashboard Layout Section */}
              <div className={styles.section}>
                <h3>Dashboard Layout</h3>
                <div className={styles.formGroup}>
                  <label>Grid Layout</label>
                  <select 
                    value={homePreferences.dashboardLayout}
                    onChange={(e) => updateHomePreferences({ dashboardLayout: e.target.value as any })}
                  >
                    <option value="2x2">2×2 Grid</option>
                    <option value="3x2">3×2 Grid</option>
                    <option value="4x2">4×2 Grid</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
                <div className={styles.checkboxGroup}>
                  <label>
                    <input
                      type="checkbox"
                      checked={homePreferences.compactView}
                      onChange={(e) => updateHomePreferences({ compactView: e.target.checked })}
                    />
                    Compact view
                  </label>
                </div>
                <div className={styles.checkboxGroup}>
                  <label>
                    <input
                      type="checkbox"
                      checked={homePreferences.autoRefresh}
                      onChange={(e) => updateHomePreferences({ autoRefresh: e.target.checked })}
                    />
                    Auto-refresh data
                  </label>
                </div>
                {homePreferences.autoRefresh && (
                  <div className={styles.formGroup}>
                    <label>Refresh Interval (seconds)</label>
                    <select 
                      value={homePreferences.refreshInterval}
                      onChange={(e) => updateHomePreferences({ refreshInterval: parseInt(e.target.value) })}
                    >
                      <option value={15}>15 seconds</option>
                      <option value={30}>30 seconds</option>
                      <option value={60}>1 minute</option>
                      <option value={300}>5 minutes</option>
                    </select>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Transactions Page Preferences */}
          {currentPage === 'transactions' && (
            <>
              {/* Table Display Section */}
              <div className={styles.section}>
                <h3>Table Display</h3>
                <div className={styles.formGroup}>
                  <label>Default Page Size</label>
                  <select 
                    value={transactionsPreferences.defaultPageSize}
                    onChange={(e) => updateTransactionsPreferences({ defaultPageSize: parseInt(e.target.value) })}
                  >
                    <option value={25}>25 transactions</option>
                    <option value={50}>50 transactions</option>
                    <option value={100}>100 transactions</option>
                    <option value={200}>200 transactions</option>
                  </select>
                </div>
                <div className={styles.formGroup}>
                  <label>Default Sort Column</label>
                  <select 
                    value={transactionsPreferences.defaultSortColumn}
                    onChange={(e) => updateTransactionsPreferences({ defaultSortColumn: e.target.value })}
                  >
                    <option value="date">Date</option>
                    <option value="amount">Amount</option>
                    <option value="payee">Payee</option>
                    <option value="category">Category</option>
                  </select>
                </div>
                <div className={styles.formGroup}>
                  <label>Default Sort Direction</label>
                  <select 
                    value={transactionsPreferences.defaultSortDirection}
                    onChange={(e) => updateTransactionsPreferences({ defaultSortDirection: e.target.value as any })}
                  >
                    <option value="desc">Newest First</option>
                    <option value="asc">Oldest First</option>
                  </select>
                </div>
                <div className={styles.checkboxGroup}>
                  <label>
                    <input
                      type="checkbox"
                      checked={transactionsPreferences.compactRows}
                      onChange={(e) => updateTransactionsPreferences({ compactRows: e.target.checked })}
                    />
                    Compact rows
                  </label>
                </div>
                <div className={styles.checkboxGroup}>
                  <label>
                    <input
                      type="checkbox"
                      checked={transactionsPreferences.highlightUncategorized}
                      onChange={(e) => updateTransactionsPreferences({ highlightUncategorized: e.target.checked })}
                    />
                    Highlight uncategorized transactions
                  </label>
                </div>
                <div className={styles.checkboxGroup}>
                  <label>
                    <input
                      type="checkbox"
                      checked={transactionsPreferences.hideInvestments}
                      onChange={(e) => updateTransactionsPreferences({ hideInvestments: e.target.checked })}
                    />
                    Hide investment transactions
                  </label>
                </div>
              </div>
            </>
          )}

          {/* Global Preferences - shown on both pages */}
          <div className={styles.section}>
            <h3>Global Settings</h3>
            <div className={styles.formGroup}>
              <label>Theme</label>
              <select 
                value={homePreferences.theme}
                onChange={(e) => updateHomePreferences({ theme: e.target.value as any })}
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="auto">Auto (System)</option>
              </select>
            </div>
            <div className={styles.formGroup}>
              <label>Currency</label>
              <select 
                value={globalPreferences.currency}
                onChange={(e) => updateGlobalPreferences({ currency: e.target.value as any })}
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="CAD">CAD (C$)</option>
              </select>
            </div>
            <div className={styles.formGroup}>
              <label>Date Format</label>
              <select 
                value={globalPreferences.dateFormat}
                onChange={(e) => updateGlobalPreferences({ dateFormat: e.target.value as any })}
              >
                <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                <option value="MMM DD, YYYY">MMM DD, YYYY</option>
              </select>
            </div>
            <div className={styles.formGroup}>
              <label>Default Time Range</label>
              <select 
                value={globalPreferences.defaultTimeRange}
                onChange={(e) => updateGlobalPreferences({ defaultTimeRange: e.target.value as any })}
              >
                <option value="1-week">1 Week</option>
                <option value="1-month">1 Month</option>
                <option value="3-months">3 Months</option>
                <option value="6-months">6 Months</option>
                <option value="1-year">1 Year</option>
                <option value="all-time">All Time</option>
              </select>
            </div>
            <div className={styles.checkboxGroup}>
              <label>
                <input
                  type="checkbox"
                  checked={homePreferences.animationsEnabled}
                  onChange={(e) => updateHomePreferences({ animationsEnabled: e.target.checked })}
                />
                Enable animations
              </label>
            </div>
            <div className={styles.checkboxGroup}>
              <label>
                <input
                  type="checkbox"
                  checked={globalPreferences.showTooltips}
                  onChange={(e) => updateGlobalPreferences({ showTooltips: e.target.checked })}
                />
                Show tooltips
              </label>
            </div>
          </div>
        </div>

        <div className={styles.footer}>
          <button className={styles.resetButton} onClick={handleReset}>
            Reset to Defaults
          </button>
          <div className={styles.buttonGroup}>
            <button className={styles.cancelButton} onClick={onClose}>
              Cancel
            </button>
            <button className={styles.saveButton} onClick={handleSave}>
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DisplayPreferences;