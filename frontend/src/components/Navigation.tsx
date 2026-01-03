import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BarChart3, CreditCard, Users, TreePine, DollarSign, RotateCcw, Settings, TrendingUp, ChevronDown, FileText } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import { FileUpload } from './FileUpload';

interface NavigationProps {
  currentPage?: 'home' | 'transactions' | 'treemap' | 'budget' | 'patterns' | 'payees' | 'visualization';
  stats?: any;
  onShowPreferences?: () => void;
}

const Navigation: React.FC<NavigationProps> = ({ stats, onShowPreferences }) => {
  const location = useLocation();
  const [isSetupOpen, setIsSetupOpen] = useState(false);
  const setupRef = useRef<HTMLDivElement>(null);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: BarChart3 },
    { path: '/transactions', label: 'Transactions', icon: CreditCard },
    { path: '/budget', label: 'Budget', icon: DollarSign },
    { path: '/reports', label: 'Reports', icon: FileText },
    { path: '/visualization', label: 'Visualize', icon: TrendingUp },
  ];

  const setupItems = [
    { path: '/treemap', label: 'Categories', icon: TreePine },
    { path: '/payees', label: 'Payees', icon: Users },
    { path: '/patterns', label: 'Patterns', icon: RotateCcw },
  ];

  // Check if any setup item is active
  const isSetupActive = setupItems.some(item => location.pathname === item.path);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (setupRef.current && !setupRef.current.contains(event.target as Node)) {
        setIsSetupOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

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

              {/* Setup Dropdown */}
              <div className="relative" ref={setupRef}>
                <button
                  onClick={() => setIsSetupOpen(!isSetupOpen)}
                  className={`
                    flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium
                    transition-all duration-200 hover:scale-105 active:scale-95
                    ${isSetupActive
                      ? 'bg-ember-500 text-white shadow-ember-glow dark:bg-ember-600'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-warm-400 dark:hover:text-ember-300 dark:hover:bg-dark-card'
                    }
                  `}
                >
                  <Settings size={18} />
                  <span>Setup</span>
                  <ChevronDown
                    size={16}
                    className={`transition-transform duration-200 ${isSetupOpen ? 'rotate-180' : ''}`}
                  />
                </button>

                {/* Dropdown Menu */}
                {isSetupOpen && (
                  <div className="absolute top-full left-0 mt-1 w-48 bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border rounded-lg shadow-lg dark:shadow-dark-elevated overflow-hidden z-50">
                    {setupItems.map(({ path, label, icon: Icon }) => (
                      <Link
                        key={path}
                        to={path}
                        onClick={() => setIsSetupOpen(false)}
                        className={`
                          flex items-center gap-3 px-4 py-2.5 text-sm font-medium
                          transition-colors duration-150
                          ${location.pathname === path
                            ? 'bg-ember-50 text-ember-600 dark:bg-ember-900/30 dark:text-ember-300'
                            : 'text-gray-700 hover:bg-gray-50 dark:text-warm-300 dark:hover:bg-dark-surface'
                          }
                        `}
                      >
                        <Icon size={18} />
                        <span>{label}</span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Stats Display */}
            {stats && stats.uncategorized_count > 0 && (
              <div className="text-sm text-gray-600 dark:text-warm-400 transition-colors duration-300">
                <span className="px-2 py-1 bg-amber-100 text-amber-800 dark:bg-ember-900/30 dark:text-ember-300 rounded-full text-xs font-medium">
                  {stats.uncategorized_count} uncategorized
                </span>
              </div>
            )}

            {/* File Upload */}
            <FileUpload />

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