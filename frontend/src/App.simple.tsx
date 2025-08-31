import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import { TimeRangeProvider } from './contexts/TimeRangeContext';
import { PreferencesProvider } from './contexts/PreferencesContext';
import { ThemeProvider } from './contexts/ThemeContext';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import TransactionsList from './components/TransactionsList';
import TreeMap from './components/TreeMap';
import Budget from './components/Budget';
import RecurringPatterns from './components/RecurringPatterns';
import PayeeManager from './components/PayeeManager';
import { defaultDashboardConfig } from './config/dashboardConfig';

// Home page component with navigation callback
const HomePage: React.FC = () => {
  const navigate = useNavigate();
  
  const handleNavigateToTransactions = (category?: string, subcategory?: string) => {
    // Store filters in sessionStorage for TransactionsList to pick up
    if (category || subcategory) {
      sessionStorage.setItem('transactionFilters', JSON.stringify({ category, subcategory }));
    }
    navigate('/transactions');
  };

  return <Dashboard config={defaultDashboardConfig} onNavigateToTransactions={handleNavigateToTransactions} />;
};

// Transactions page component that picks up filters from sessionStorage
const TransactionsPage: React.FC = () => {
  const [initialFilters] = useState(() => {
    try {
      const saved = sessionStorage.getItem('transactionFilters');
      if (saved) {
        sessionStorage.removeItem('transactionFilters'); // Clear after use
        return JSON.parse(saved);
      }
    } catch (e) {
      console.warn('Failed to parse transaction filters from sessionStorage');
    }
    return {};
  });

  return <TransactionsList initialFilters={initialFilters} />;
};

// TreeMap page component with navigation callback
const TreeMapPage: React.FC = () => {
  const navigate = useNavigate();
  
  const handleNavigateToTransactions = (category?: string, subcategory?: string) => {
    // Store filters in sessionStorage for TransactionsList to pick up
    if (category || subcategory) {
      sessionStorage.setItem('transactionFilters', JSON.stringify({ category, subcategory }));
    }
    navigate('/transactions');
  };

  return <TreeMap onNavigateToTransactions={handleNavigateToTransactions} />;
};

const AppContent: React.FC = () => {
  return (
    <TimeRangeProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/treemap" element={<TreeMapPage />} />
          <Route path="/budget" element={<Budget />} />
          <Route path="/patterns" element={<RecurringPatterns />} />
          <Route path="/payees" element={<PayeeManager />} />
        </Routes>
      </Layout>
    </TimeRangeProvider>
  );
};

function App() {
  return (
    <ThemeProvider>
      <PreferencesProvider>
        <Router>
          <AppContent />
        </Router>
      </PreferencesProvider>
    </ThemeProvider>
  );
}

export default App;