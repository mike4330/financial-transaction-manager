import React, { useState } from 'react';
import { Users, Tag } from 'lucide-react';
import type { Category, Subcategory } from '../types';

interface BulkCategorizationProps {
  selectedCount: number;
  categories: Category[];
  subcategories: Subcategory[];
  onCategorize: (categoryId: number, subcategoryId: number) => Promise<void>;
  isLoading: boolean;
}

const BulkCategorization: React.FC<BulkCategorizationProps> = ({
  selectedCount,
  categories,
  subcategories,
  onCategorize,
  isLoading,
}) => {
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | ''>('');
  const [selectedSubcategoryId, setSelectedSubcategoryId] = useState<number | ''>('');

  // Filter subcategories based on selected category
  const availableSubcategories = selectedCategoryId
    ? subcategories.filter(sub => sub.category_id === selectedCategoryId)
    : [];

  const handleCategoryChange = (categoryId: string) => {
    const id = categoryId === '' ? '' : parseInt(categoryId);
    setSelectedCategoryId(id);
    setSelectedSubcategoryId(''); // Reset subcategory when category changes
  };

  const handleSubcategoryChange = (subcategoryId: string) => {
    const id = subcategoryId === '' ? '' : parseInt(subcategoryId);
    setSelectedSubcategoryId(id);
  };

  const handleApply = async () => {
    if (selectedCategoryId && selectedSubcategoryId) {
      await onCategorize(selectedCategoryId as number, selectedSubcategoryId as number);
      // Reset selections after successful categorization
      setSelectedCategoryId('');
      setSelectedSubcategoryId('');
    }
  };

  const canApply = selectedCategoryId !== '' && selectedSubcategoryId !== '' && !isLoading;

  return (
    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
      <div className="flex items-center space-x-2 mb-4">
        <Users size={18} className="text-blue-600" />
        <h3 className="text-sm font-medium text-blue-900">
          Bulk Categorization
        </h3>
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          {selectedCount} selected
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
        {/* Category Selection */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Category
          </label>
          <select
            value={selectedCategoryId}
            onChange={(e) => handleCategoryChange(e.target.value)}
            disabled={isLoading}
            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
          >
            <option value="">Select Category</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </div>

        {/* Subcategory Selection */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Subcategory
          </label>
          <select
            value={selectedSubcategoryId}
            onChange={(e) => handleSubcategoryChange(e.target.value)}
            disabled={!selectedCategoryId || isLoading}
            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
          >
            <option value="">Select Subcategory</option>
            {availableSubcategories.map((subcategory) => (
              <option key={subcategory.id} value={subcategory.id}>
                {subcategory.name}
              </option>
            ))}
          </select>
        </div>

        {/* Apply Button */}
        <div>
          <button
            onClick={handleApply}
            disabled={!canApply}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Applying...</span>
              </>
            ) : (
              <>
                <Tag size={16} />
                <span>Apply to {selectedCount} transactions</span>
              </>
            )}
          </button>
        </div>
      </div>

      {selectedCategoryId && availableSubcategories.length === 0 && (
        <div className="mt-3 text-sm text-amber-600">
          No subcategories available for the selected category.
        </div>
      )}
    </div>
  );
};

export default BulkCategorization;