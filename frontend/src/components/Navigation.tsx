import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BarChart3, CreditCard, Users, TreePine, DollarSign, RotateCcw, Settings } from 'lucide-react';
import ThemeToggle from './ThemeToggle';

interface NavigationProps {
  currentPage?: 'home' | 'transactions' | 'treemap' | 'budget' | 'patterns' | 'payees';
  stats?: any;
  onShowPreferences?: () => void;
}

const Navigation: React.FC<NavigationProps> = ({ stats, onShowPreferences }) => {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: BarChart3 },
    { path: '/transactions', label: 'Transactions', icon: CreditCard },
    { path: '/treemap', label: 'Categories', icon: TreePine },
    { path: '/budget', label: 'Budget', icon: DollarSign },
    { path: '/patterns', label: 'Patterns', icon: RotateCcw },
    { path: '/payees', label: 'Payees', icon: Users },
  ];

  return (
    <nav className="bg-white dark:bg-dark-surface border-b border-gray-200 dark:border-dark-border shadow-sm dark:shadow-dark-elevated transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <h1 className="text-xl font-bold text-gray-900 dark:text-ember-100 transition-colors duration-300">
              <span className="mr-2">🔥</span>
              Transaction Manager
            </h1>
            
            <div className="flex gap-2">
              {navItems.map(({ path, label, icon: Icon }) => (
                <Link
                  key={path}
                  to={path}
                  className={`
                    flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium
                    transition-all duration-200 hover:scale-105 active:scale-95
                    ${location.pathname === path 
                      ? 'bg-ember-500 text-white shadow-ember-glow dark:bg-ember-600' 
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-warm-400 dark:hover:text-ember-300 dark:hover:bg-dark-card'
                    }
                  `}
                >
                  <Icon size={18} />
                  <span>{label}</span>
                </Link>
              ))}
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Stats Display */}
            {stats && (
              <div className="text-sm text-gray-600 dark:text-warm-400 transition-colors duration-300">
                <span className="mr-2">📈</span>
                {stats.total_transactions?.toLocaleString() || 0} transactions
                {stats.uncategorized_count > 0 && (
                  <span className="ml-2 px-2 py-1 bg-amber-100 text-amber-800 dark:bg-ember-900/30 dark:text-ember-300 rounded-full text-xs font-medium">
                    {stats.uncategorized_count} uncategorized
                  </span>
                )}
              </div>
            )}
            
            {/* Theme Toggle */}
            <ThemeToggle />
            
            {/* Preferences Button */}
            {onShowPreferences && (
              <button
                onClick={onShowPreferences}
                className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-warm-400 dark:hover:text-ember-300 dark:hover:bg-dark-card rounded-lg transition-all duration-200 hover:scale-105 active:scale-95"
                title="Display Preferences"
              >
                <Settings size={18} />
              </button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;