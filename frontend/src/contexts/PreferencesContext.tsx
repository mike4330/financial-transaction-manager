import React, { createContext, useContext, useState, useEffect } from 'react';

export interface HomePreferences {
  selectedAccounts: string[];
  theme: 'light' | 'dark' | 'auto';
  dashboardLayout: '2x2' | '3x2' | '4x2' | 'custom';
  compactView: boolean;
  animationsEnabled: boolean;
  autoRefresh: boolean;
  refreshInterval: number;
}

export interface TransactionsPreferences {
  defaultPageSize: number;
  defaultSortColumn: string;
  defaultSortDirection: 'asc' | 'desc';
  showAllColumns: boolean;
  compactRows: boolean;
  highlightUncategorized: boolean;
}

export interface GlobalPreferences {
  currency: 'USD' | 'EUR' | 'GBP' | 'CAD';
  dateFormat: 'MM/DD/YYYY' | 'DD/MM/YYYY' | 'YYYY-MM-DD' | 'MMM DD, YYYY';
  timeZone: string;
  defaultTimeRange: '1-week' | '1-month' | '3-months' | '6-months' | '1-year' | 'all-time';
  showTooltips: boolean;
}

interface PreferencesContextType {
  homePreferences: HomePreferences;
  transactionsPreferences: TransactionsPreferences;
  globalPreferences: GlobalPreferences;
  updateHomePreferences: (prefs: Partial<HomePreferences>) => void;
  updateTransactionsPreferences: (prefs: Partial<TransactionsPreferences>) => void;
  updateGlobalPreferences: (prefs: Partial<GlobalPreferences>) => void;
  resetToDefaults: (page?: 'home' | 'transactions' | 'global') => void;
}

const defaultHomePreferences: HomePreferences = {
  selectedAccounts: [],
  theme: 'light',
  dashboardLayout: '2x2',
  compactView: false,
  animationsEnabled: true,
  autoRefresh: false,
  refreshInterval: 30
};

const defaultTransactionsPreferences: TransactionsPreferences = {
  defaultPageSize: 50,
  defaultSortColumn: 'date',
  defaultSortDirection: 'desc',
  showAllColumns: true,
  compactRows: false,
  highlightUncategorized: true
};

const defaultGlobalPreferences: GlobalPreferences = {
  currency: 'USD',
  dateFormat: 'MM/DD/YYYY',
  timeZone: 'America/New_York',
  defaultTimeRange: '1-month',
  showTooltips: true
};

const PreferencesContext = createContext<PreferencesContextType | undefined>(undefined);

export const PreferencesProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [homePreferences, setHomePreferences] = useState<HomePreferences>(defaultHomePreferences);
  const [transactionsPreferences, setTransactionsPreferences] = useState<TransactionsPreferences>(defaultTransactionsPreferences);
  const [globalPreferences, setGlobalPreferences] = useState<GlobalPreferences>(defaultGlobalPreferences);

  // Load preferences from localStorage on mount
  useEffect(() => {
    try {
      const savedHome = localStorage.getItem('homePreferences');
      const savedTransactions = localStorage.getItem('transactionsPreferences');
      const savedGlobal = localStorage.getItem('globalPreferences');

      if (savedHome) {
        setHomePreferences(prev => ({ ...prev, ...JSON.parse(savedHome) }));
      }
      if (savedTransactions) {
        setTransactionsPreferences(prev => ({ ...prev, ...JSON.parse(savedTransactions) }));
      }
      if (savedGlobal) {
        setGlobalPreferences(prev => ({ ...prev, ...JSON.parse(savedGlobal) }));
      }
    } catch (error) {
      console.error('Error loading preferences from localStorage:', error);
    }
  }, []);

  const updateHomePreferences = (prefs: Partial<HomePreferences>) => {
    setHomePreferences(prev => {
      const updated = { ...prev, ...prefs };
      localStorage.setItem('homePreferences', JSON.stringify(updated));
      return updated;
    });
  };

  const updateTransactionsPreferences = (prefs: Partial<TransactionsPreferences>) => {
    setTransactionsPreferences(prev => {
      const updated = { ...prev, ...prefs };
      localStorage.setItem('transactionsPreferences', JSON.stringify(updated));
      return updated;
    });
  };

  const updateGlobalPreferences = (prefs: Partial<GlobalPreferences>) => {
    setGlobalPreferences(prev => {
      const updated = { ...prev, ...prefs };
      localStorage.setItem('globalPreferences', JSON.stringify(updated));
      return updated;
    });
  };

  const resetToDefaults = (page?: 'home' | 'transactions' | 'global') => {
    if (!page || page === 'home') {
      setHomePreferences(defaultHomePreferences);
      localStorage.setItem('homePreferences', JSON.stringify(defaultHomePreferences));
    }
    if (!page || page === 'transactions') {
      setTransactionsPreferences(defaultTransactionsPreferences);
      localStorage.setItem('transactionsPreferences', JSON.stringify(defaultTransactionsPreferences));
    }
    if (!page || page === 'global') {
      setGlobalPreferences(defaultGlobalPreferences);
      localStorage.setItem('globalPreferences', JSON.stringify(defaultGlobalPreferences));
    }
  };

  return (
    <PreferencesContext.Provider value={{
      homePreferences,
      transactionsPreferences,
      globalPreferences,
      updateHomePreferences,
      updateTransactionsPreferences,
      updateGlobalPreferences,
      resetToDefaults
    }}>
      {children}
    </PreferencesContext.Provider>
  );
};

export const usePreferences = () => {
  const context = useContext(PreferencesContext);
  if (context === undefined) {
    throw new Error('usePreferences must be used within a PreferencesProvider');
  }
  return context;
};