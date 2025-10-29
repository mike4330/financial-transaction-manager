import React from 'react';
import { useTheme } from '../contexts/ThemeContext';

const ThemeToggle: React.FC = () => {
  // Simple manual dark mode toggle without context as fallback
  const [localDarkMode, setLocalDarkMode] = React.useState(
    () => document.documentElement.classList.contains('dark')
  );

  // Try to use theme context, fall back to manual mode if not available
  let isDarkMode = localDarkMode;
  let toggleDarkMode = () => {
    const newMode = !localDarkMode;
    setLocalDarkMode(newMode);
    if (newMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  };

  try {
    const theme = useTheme();
    isDarkMode = theme.isDarkMode;
    toggleDarkMode = theme.toggleDarkMode;
  } catch (error) {
    console.warn('ThemeToggle: Using fallback mode (theme context not available)');
    // Use the manual fallback defined above
  }

  return (
    <button
      onClick={toggleDarkMode}
      className={`
        relative w-16 h-8 rounded-full transition-all duration-300 ease-in-out
        focus:outline-none focus:ring-2 focus:ring-offset-2
        ${isDarkMode 
          ? 'bg-gradient-to-r from-dark-surface to-dark-elevated focus:ring-ember-500' 
          : 'bg-gradient-to-r from-gray-200 to-gray-300 focus:ring-blue-500'
        }
        shadow-inner border
        ${isDarkMode ? 'border-dark-border' : 'border-gray-400'}
        hover:scale-105 active:scale-95
      `}
      aria-label={`Switch to ${isDarkMode ? 'light' : 'dark'} mode`}
      title={`Currently in ${isDarkMode ? 'dark' : 'light'} mode. Click to switch.`}
    >
      {/* Toggle Switch */}
      <div
        className={`
          absolute top-0.5 w-7 h-7 rounded-full transition-all duration-300 ease-in-out
          flex items-center justify-center text-sm
          ${isDarkMode 
            ? 'translate-x-8 bg-gradient-to-br from-ember-400 to-ember-600 shadow-ember-glow' 
            : 'translate-x-0.5 bg-gradient-to-br from-yellow-300 to-yellow-500'
          }
          shadow-lg transform
        `}
      >
        {/* Icons */}
        <span className="transition-all duration-200">
          {isDarkMode ? (
            // Custom ember/flame icon for dark mode
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-ember-50">
              <path
                d="M12 2C12.8 2.8 13 4 13 5.5C13 7 12 8.5 12 10C12 12 14 13 16 13C18 13 20 11 20 9C20 15 16 19 12 19C8 19 4 15 4 11C4 7 8 4 12 2Z"
                fill="currentColor"
              />
              <path
                d="M10 15C10 16.1 10.9 17 12 17C13.1 17 14 16.1 14 15C14 13.9 13.1 13 12 13C10.9 13 10 13.9 10 15Z"
                fill="currentColor"
                opacity="0.7"
              />
            </svg>
          ) : (
            // Sun icon for light mode
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-yellow-700">
              <circle cx="12" cy="12" r="4" fill="currentColor"/>
              <path
                d="M12 2V4M12 20V22M4.93 4.93L6.34 6.34M17.66 17.66L19.07 19.07M2 12H4M20 12H22M4.93 19.07L6.34 17.66M17.66 6.34L19.07 4.93"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          )}
        </span>
      </div>

      {/* Background Pattern (subtle) */}
      <div className="absolute inset-0 rounded-full opacity-20">
        {isDarkMode && (
          <div className="w-full h-full bg-gradient-to-r from-ember-900/30 to-ember-700/30 rounded-full" />
        )}
      </div>

      {/* Ambient glow effect for dark mode */}
      {isDarkMode && (
        <div className="absolute inset-0 rounded-full bg-ember-500/10 blur-sm animate-ember-pulse" />
      )}
    </button>
  );
};

export default ThemeToggle;