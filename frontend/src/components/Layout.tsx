import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import Navigation from './Navigation';
import DisplayPreferences from './DisplayPreferences';
import { TimeRangeSelector } from './TimeRangeSelector';
import { usePreferences } from '../contexts/PreferencesContext';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [apiStatus, setApiStatus] = useState<'loading' | 'connected' | 'failed'>('loading');
  const [stats, setStats] = useState<any>(null);
  const [showPreferences, setShowPreferences] = useState(false);
  const location = useLocation();

  // Determine current page from route
  const getCurrentPage = (): 'home' | 'transactions' | 'treemap' | 'budget' | 'patterns' | 'payees' | 'visualization' => {
    const path = location.pathname;
    if (path.startsWith('/transactions')) return 'transactions';
    if (path.startsWith('/treemap')) return 'treemap';
    if (path.startsWith('/budget')) return 'budget';
    if (path.startsWith('/patterns')) return 'patterns';
    if (path.startsWith('/payees')) return 'payees';
    if (path.startsWith('/visualization')) return 'visualization';
    return 'home';
  };

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

  const currentPage = getCurrentPage();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-dark-bg transition-colors duration-300">
      <Navigation 
        currentPage={currentPage}
        stats={stats}
        onShowPreferences={() => setShowPreferences(true)}
      />

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Global time range selector - only show on relevant pages */}
        {(currentPage === 'home' || currentPage === 'transactions' || currentPage === 'visualization') && (
          <div className="mb-6">
            <TimeRangeSelector />
          </div>
        )}

        {/* Main content */}
        {children}
      </div>

      {/* Display Preferences Modal */}
      <DisplayPreferences
        isOpen={showPreferences}
        onClose={() => setShowPreferences(false)}
        currentPage={currentPage}
      />
    </div>
  );
};

export default Layout;