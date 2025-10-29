import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
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
import TransactionVisualization from './components/TransactionVisualization';

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <Router>
        <PreferencesProvider>
          <TimeRangeProvider>
            <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/transactions" element={<TransactionsList />} />
              <Route path="/transactions/:category" element={<TransactionsList />} />
              <Route path="/transactions/:category/:subcategory" element={<TransactionsList />} />
              <Route path="/treemap" element={<TreeMap />} />
              <Route path="/budget" element={<Budget />} />
              <Route path="/budget/:year/:month" element={<Budget />} />
              <Route path="/patterns" element={<RecurringPatterns />} />
              <Route path="/payees" element={<PayeeManager />} />
              <Route path="/visualization" element={<TransactionVisualization />} />
              {/* Fallback route */}
              <Route path="*" element={<Dashboard />} />
            </Routes>
          </Layout>
        </TimeRangeProvider>
      </PreferencesProvider>
    </Router>
    </ThemeProvider>
  );
};

export default App;