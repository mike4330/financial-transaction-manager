import React from 'react';
import { Filter, X } from 'lucide-react';
import type { TransactionFilters, FilterOptions } from '../types';

interface TransactionFiltersProps {
  filters: TransactionFilters;
  onFiltersChange: (filters: TransactionFilters) => void;
  filterOptions?: FilterOptions;
  isLoading: boolean;
}

const TransactionFilters: React.FC<TransactionFiltersProps> = ({
  filters,
  onFiltersChange,
  filterOptions,
  isLoading,
}) => {
  const updateFilter = (key: keyof TransactionFilters, value: any) => {
    onFiltersChange({
      ...filters,
      [key]: value,
      page: 1, // Reset to first page when filters change
    });
  };

  const clearFilters = () => {
    onFiltersChange({
      page: 1,
      limit: filters.limit,
    });
  };

  const hasActiveFilters = filters.account || filters.category || filters.type || 
                          filters.start_date || filters.end_date || filters.uncategorized;

  return (
    <div className="mb-6 p-4 border border-gray-200 rounded-lg bg-gray-50">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Filter size={18} className="text-gray-600" />
          <h3 className="text-sm font-medium text-gray-900">Filters</h3>
        </div>
        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-900"
          >
            <X size={16} />
            <span>Clear all</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {/* Account Filter */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Account
          </label>
          <select
            value={filters.account || ''}
            onChange={(e) => updateFilter('account', e.target.value || undefined)}
            disabled={isLoading}
            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
          >
            <option value="">All Accounts</option>
            {filterOptions?.accounts.map((account) => (
              <option key={account} value={account}>
                {account}
              </option>
            ))}
          </select>
        </div>

        {/* Category Filter */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Category
          </label>
          <select
            value={filters.category || ''}
            onChange={(e) => updateFilter('category', e.target.value || undefined)}
            disabled={isLoading}
            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
          >
            <option value="">All Categories</option>
            {filterOptions?.categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </div>

        {/* Transaction Type Filter */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Type
          </label>
          <select
            value={filters.type || ''}
            onChange={(e) => updateFilter('type', e.target.value || undefined)}
            disabled={isLoading}
            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
          >
            <option value="">All Types</option>
            {filterOptions?.transaction_types.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>

        {/* Start Date Filter */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Start Date
          </label>
          <input
            type="date"
            value={filters.start_date || ''}
            onChange={(e) => updateFilter('start_date', e.target.value || undefined)}
            disabled={isLoading}
            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
          />
        </div>

        {/* End Date Filter */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            End Date
          </label>
          <input
            type="date"
            value={filters.end_date || ''}
            onChange={(e) => updateFilter('end_date', e.target.value || undefined)}
            disabled={isLoading}
            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
          />
        </div>

        {/* Uncategorized Only Filter */}
        <div className="flex items-center">
          <div className="flex items-center h-full">
            <label className="flex items-center space-x-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={filters.uncategorized || false}
                onChange={(e) => updateFilter('uncategorized', e.target.checked || undefined)}
                disabled={isLoading}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
              />
              <span>Uncategorized only</span>
            </label>
          </div>
        </div>
      </div>

      {/* Results per page */}
      <div className="mt-4 flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <label className="text-xs font-medium text-gray-700">
            Results per page:
          </label>
          <select
            value={filters.limit}
            onChange={(e) => updateFilter('limit', parseInt(e.target.value))}
            disabled={isLoading}
            className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
          >
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
          </select>
        </div>
      </div>
    </div>
  );
};

export default TransactionFilters;