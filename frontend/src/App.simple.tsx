import React, { useState, useEffect } from 'react';
import { TimeRangeProvider } from './contexts/TimeRangeContext';
import { PreferencesProvider, usePreferences } from './contexts/PreferencesContext';
import { TimeRangeSelector } from './components/TimeRangeSelector';
import Dashboard from './components/Dashboard';
import TransactionsList from './components/TransactionsList';
import TreeMap from './components/TreeMap';
import Budget from './components/Budget';
import RecurringPatterns from './components/RecurringPatterns';
import PayeeManager from './components/PayeeManager';
import DisplayPreferences from './components/DisplayPreferences';
import { defaultDashboardConfig } from './config/dashboardConfig';
import styles from './components/App.module.css';

const AppContent: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<'loading' | 'connected' | 'failed'>('loading');
  const [stats, setStats] = useState<any>(null);
  const [currentPage, setCurrentPage] = useState<'home' | 'transactions' | 'treemap' | 'budget' | 'patterns' | 'payees'>('home');
  const [showPreferences, setShowPreferences] = useState(false);
  const [transactionFilters, setTransactionFilters] = useState<{category?: string, subcategory?: string}>({});
  const { homePreferences } = usePreferences();

  useEffect(() => {
    // Test API connection
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        setApiStatus('connected');
        // Get basic stats
        return fetch('/api/stats');
      })
      .then(res => res.json())
      .then(data => {
        setStats(data);
      })
      .catch(err => {
        console.error('API connection failed:', err);
        setApiStatus('failed');
      });
  }, []);

  const handleNavigateToTransactions = (category?: string, subcategory?: string) => {
    setTransactionFilters({ category, subcategory });
    setCurrentPage('transactions');
  };

  return (
    <TimeRangeProvider>
      <div className="container">
        <h1 className="text-3xl mb-6 text-center">
          💰 Transaction Manager
        </h1>
        
        {/* Navigation */}
        <nav className={styles.nav}>
          <div className={styles.navLeft}>
            <button
              onClick={() => setCurrentPage('home')}
              className={`${styles.navButton} ${currentPage === 'home' ? styles.navButtonActive : ''}`}
            >
              Home
            </button>
            <button
              onClick={() => setCurrentPage('transactions')}
              className={`${styles.navButton} ${currentPage === 'transactions' ? styles.navButtonActive : ''}`}
            >
              Transactions
            </button>
            <button
              onClick={() => setCurrentPage('treemap')}
              className={`${styles.navButton} ${currentPage === 'treemap' ? styles.navButtonActive : ''}`}
            >
              Categories
            </button>
            <button
              onClick={() => setCurrentPage('budget')}
              className={`${styles.navButton} ${currentPage === 'budget' ? styles.navButtonActive : ''}`}
            >
              Budget
            </button>
            <button
              onClick={() => setCurrentPage('patterns')}
              className={`${styles.navButton} ${currentPage === 'patterns' ? styles.navButtonActive : ''}`}
            >
              Patterns
            </button>
            <button
              onClick={() => setCurrentPage('payees')}
              className={`${styles.navButton} ${currentPage === 'payees' ? styles.navButtonActive : ''}`}
            >
              Payees
            </button>
          </div>
          
          <div className={styles.navRight}>
            {/* Account Filter Indicator */}
            {currentPage === 'home' && homePreferences.selectedAccounts.length > 0 && (
              <div 
                className={styles.filterIndicator}
                title={`Filtered to ${homePreferences.selectedAccounts.length} account${homePreferences.selectedAccounts.length === 1 ? '' : 's'}: ${homePreferences.selectedAccounts.join(', ')}`}
              >
                <span className={styles.filterIcon}>🔍</span>
                <span className={styles.filterCount}>{homePreferences.selectedAccounts.length}</span>
              </div>
            )}
            
            {/* Preferences Gear Icon */}
            <button
              onClick={() => setShowPreferences(true)}
              className={styles.gearButton}
              title="Display Preferences"
            >
              ⚙️
            </button>
            
            {/* Backend Status Pill */}
            <div className={`${styles.backendStatus} ${
              apiStatus === 'connected' ? styles.backendStatusConnected :
              apiStatus === 'failed' ? styles.backendStatusFailed :
              styles.backendStatusLoading
            }`}>
              {apiStatus === 'loading' && 'Backend Connecting...'}
              {apiStatus === 'connected' && 'Backend OK'}
              {apiStatus === 'failed' && 'Backend Error'}
            </div>
          </div>
        </nav>

        {/* Page Content */}
        {currentPage === 'home' && apiStatus === 'connected' && (
          <>
            {/* Time Range Control */}
            <div className={styles.timeRangeContainer}>
              <TimeRangeSelector />
              {homePreferences.selectedAccounts.length > 0 && (
                <div className={styles.filterNote}>
                  <span className={styles.filterNoteIcon}>ℹ️</span>
                  Dashboard filtered to {homePreferences.selectedAccounts.length} account{homePreferences.selectedAccounts.length === 1 ? '' : 's'}
                </div>
              )}
            </div>
            
            {/* Dashboard Grid */}
            <Dashboard config={defaultDashboardConfig} />
          </>
        )}
        
        {currentPage === 'transactions' && <TransactionsList initialFilters={transactionFilters} />}
        
        {currentPage === 'treemap' && <TreeMap onNavigateToTransactions={handleNavigateToTransactions} />}
        
        {currentPage === 'budget' && <Budget />}
        
        {currentPage === 'patterns' && <RecurringPatterns />}
        
        {currentPage === 'payees' && <PayeeManager />}
        
        {/* Display Preferences Modal */}
        <DisplayPreferences 
          isOpen={showPreferences}
          onClose={() => setShowPreferences(false)}
          currentPage={currentPage}
        />
        </div>
    </TimeRangeProvider>
  );
};

function App() {
  return (
    <PreferencesProvider>
      <AppContent />
    </PreferencesProvider>
  );
}

export default App;