import React from 'react';
import { useTheme } from '../contexts/ThemeContext';

const DarkModeShowcase: React.FC = () => {
  const { isDarkMode, theme } = useTheme();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-dark-bg transition-colors duration-300 p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-ember-100 animate-fade-in">
            🔥 Midnight Ember Theme
          </h1>
          <p className="text-xl text-gray-600 dark:text-warm-400">
            Currently in <span className="font-semibold text-ember-600 dark:text-ember-400">{theme}</span> mode
          </p>
        </div>

        {/* Color Palette Showcase */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Primary Colors */}
          <div className="bg-white dark:bg-dark-surface rounded-xl p-6 shadow-lg dark:shadow-dark-elevated border dark:border-dark-border transition-all duration-300 hover:scale-105">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-ember-100">Ember Palette</h3>
            <div className="space-y-2">
              {[
                { shade: 500, name: 'Primary', color: 'bg-ember-500' },
                { shade: 400, name: 'Light', color: 'bg-ember-400' },
                { shade: 600, name: 'Dark', color: 'bg-ember-600' },
              ].map(({ shade, name, color }) => (
                <div key={shade} className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg ${color} shadow-sm`} />
                  <span className="text-sm font-medium text-gray-700 dark:text-warm-300">{name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Surface Colors */}
          <div className="bg-white dark:bg-dark-card rounded-xl p-6 shadow-lg dark:shadow-dark-elevated border dark:border-dark-border transition-all duration-300 hover:scale-105">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-ember-100">Surfaces</h3>
            <div className="space-y-2">
              <div className="p-3 bg-gray-50 dark:bg-dark-surface rounded-lg">
                <span className="text-sm text-gray-600 dark:text-warm-400">Surface</span>
              </div>
              <div className="p-3 bg-gray-100 dark:bg-dark-card rounded-lg">
                <span className="text-sm text-gray-600 dark:text-warm-400">Card</span>
              </div>
              <div className="p-3 bg-gray-200 dark:bg-dark-elevated rounded-lg">
                <span className="text-sm text-gray-600 dark:text-warm-400">Elevated</span>
              </div>
            </div>
          </div>

          {/* Interactive Elements */}
          <div className="bg-white dark:bg-dark-surface rounded-xl p-6 shadow-lg dark:shadow-dark-elevated border dark:border-dark-border transition-all duration-300 hover:scale-105">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-ember-100">Elements</h3>
            <div className="space-y-3">
              <button className="w-full px-4 py-2 bg-ember-500 hover:bg-ember-600 text-white rounded-lg font-medium transition-all duration-200 hover:scale-105 active:scale-95 shadow-ember-glow">
                Primary Button
              </button>
              <button className="w-full px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-dark-elevated dark:hover:bg-warm-800 text-gray-800 dark:text-warm-200 rounded-lg font-medium transition-all duration-200 hover:scale-105 active:scale-95">
                Secondary Button
              </button>
              <div className="w-full px-4 py-2 border border-gray-300 dark:border-dark-border bg-gray-50 dark:bg-dark-card rounded-lg">
                <span className="text-sm text-gray-600 dark:text-warm-400">Input Field</span>
              </div>
            </div>
          </div>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-white dark:bg-dark-surface rounded-xl p-8 shadow-lg dark:shadow-dark-elevated border dark:border-dark-border">
            <h3 className="text-2xl font-bold text-gray-900 dark:text-ember-100 mb-4">
              ✨ What Makes This Different
            </h3>
            <ul className="space-y-3 text-gray-600 dark:text-warm-400">
              <li className="flex items-start gap-3">
                <span className="text-ember-500 dark:text-ember-400">🔥</span>
                <span>Warm amber/copper accents instead of cold blues</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-ember-500 dark:text-ember-400">🌙</span>
                <span>Rich coffee and espresso backgrounds</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-ember-500 dark:text-ember-400">✨</span>
                <span>Subtle glow effects and warm shadows</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-ember-500 dark:text-ember-400">🎨</span>
                <span>Professional yet cozy aesthetic</span>
              </li>
            </ul>
          </div>

          <div className="bg-white dark:bg-dark-card rounded-xl p-8 shadow-lg dark:shadow-dark-elevated border dark:border-dark-border">
            <h3 className="text-2xl font-bold text-gray-900 dark:text-ember-100 mb-4">
              🎯 Key Features
            </h3>
            <ul className="space-y-3 text-gray-600 dark:text-warm-400">
              <li className="flex items-start gap-3">
                <span className="text-ember-500 dark:text-ember-400">⚡</span>
                <span>Automatic system theme detection</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-ember-500 dark:text-ember-400">💾</span>
                <span>Persistent preference storage</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-ember-500 dark:text-ember-400">🔄</span>
                <span>Smooth transitions between modes</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-ember-500 dark:text-ember-400">🎛️</span>
                <span>Beautiful custom toggle component</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Stats */}
        <div className="bg-gradient-to-r from-ember-500 to-ember-600 rounded-xl p-8 text-white">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
            <div>
              <div className="text-3xl font-bold mb-2">🎨</div>
              <div className="text-2xl font-bold">50+</div>
              <div className="text-ember-100">Custom Colors</div>
            </div>
            <div>
              <div className="text-3xl font-bold mb-2">⚡</div>
              <div className="text-2xl font-bold">300ms</div>
              <div className="text-ember-100">Transition Speed</div>
            </div>
            <div>
              <div className="text-3xl font-bold mb-2">🔥</div>
              <div className="text-2xl font-bold">Unique</div>
              <div className="text-ember-100">Midnight Ember</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DarkModeShowcase;