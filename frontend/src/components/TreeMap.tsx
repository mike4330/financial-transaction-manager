import React, { useState, useEffect } from 'react';
import styles from './TreeMap.module.css';
import Dialog from './Dialog';

interface TreeMapData {
  name: string;
  value: number;
  amount: number;
  children?: TreeMapChildData[];
}

interface TreeMapChildData {
  name: string;
  value: number;
  amount: number;
  category: string;
}

interface TreeMapResponse {
  data: TreeMapData[];
  total_categories: number;
  total_transactions: number;
}

interface Category {
  id: number;
  name: string;
}

interface Subcategory {
  id: number;
  name: string;
  category_id: number;
  category_name: string;
}

interface TreeMapProps {
  onNavigateToTransactions?: (category?: string, subcategory?: string) => void;
}

const TreeMap: React.FC<TreeMapProps> = ({ onNavigateToTransactions }) => {
  const [data, setData] = useState<TreeMapData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCategories, setTotalCategories] = useState(0);
  const [totalTransactions, setTotalTransactions] = useState(0);

  // Category management state
  const [categories, setCategories] = useState<Category[]>([]);
  const [subcategories, setSubcategories] = useState<Subcategory[]>([]);
  const [isAddCategoryDialogOpen, setIsAddCategoryDialogOpen] = useState(false);
  const [isAddSubcategoryDialogOpen, setIsAddSubcategoryDialogOpen] = useState(false);
  const [isEditCategoryDialogOpen, setIsEditCategoryDialogOpen] = useState(false);
  const [isEditSubcategoryDialogOpen, setIsEditSubcategoryDialogOpen] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newSubcategoryName, setNewSubcategoryName] = useState('');
  const [selectedCategoryForSub, setSelectedCategoryForSub] = useState<Category | null>(null);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [editingSubcategory, setEditingSubcategory] = useState<Subcategory | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchTreeMapData();
    fetchCategories();
  }, []);

  const fetchTreeMapData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/treemap');

      if (!response.ok) {
        throw new Error('Failed to fetch tree map data');
      }

      const result: TreeMapResponse = await response.json();
      setData(result.data);
      setTotalCategories(result.total_categories);
      setTotalTransactions(result.total_transactions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tree map data');
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch('/api/categories');
      if (!response.ok) {
        throw new Error('Failed to fetch categories');
      }

      const result = await response.json();
      setCategories(result.categories || []);
      setSubcategories(result.subcategories || []);
    } catch (err) {
      console.error('Error fetching categories:', err);
    }
  };

  const handleAddCategory = async () => {
    if (!newCategoryName.trim()) {
      setError('Category name cannot be empty');
      return;
    }

    try {
      const response = await fetch('/api/categories', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: newCategoryName.trim() }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Failed to create category');
      }

      setSuccessMessage(`Category "${newCategoryName}" created successfully!`);
      setNewCategoryName('');
      setIsAddCategoryDialogOpen(false);
      await fetchCategories();
      await fetchTreeMapData();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create category');
    }
  };

  const handleEditCategory = async () => {
    if (!editingCategory || !newCategoryName.trim()) {
      setError('Category name cannot be empty');
      return;
    }

    try {
      const response = await fetch(`/api/categories/${editingCategory.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: newCategoryName.trim() }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Failed to update category');
      }

      setSuccessMessage(`Category updated successfully!`);
      setNewCategoryName('');
      setEditingCategory(null);
      setIsEditCategoryDialogOpen(false);
      await fetchCategories();
      await fetchTreeMapData();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update category');
    }
  };

  const handleDeleteCategory = async (category: Category) => {
    if (!window.confirm(`Are you sure you want to delete the category "${category.name}"? This will also delete all its subcategories.`)) {
      return;
    }

    try {
      const response = await fetch(`/api/categories/${category.id}`, {
        method: 'DELETE',
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Failed to delete category');
      }

      setSuccessMessage(`Category "${category.name}" deleted successfully!`);
      await fetchCategories();
      await fetchTreeMapData();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete category');
    }
  };

  const handleAddSubcategory = async () => {
    if (!selectedCategoryForSub || !newSubcategoryName.trim()) {
      setError('Subcategory name cannot be empty');
      return;
    }

    try {
      const response = await fetch(`/api/categories/${selectedCategoryForSub.id}/subcategories`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: newSubcategoryName.trim() }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Failed to create subcategory');
      }

      setSuccessMessage(`Subcategory "${newSubcategoryName}" created successfully!`);
      setNewSubcategoryName('');
      setSelectedCategoryForSub(null);
      setIsAddSubcategoryDialogOpen(false);
      await fetchCategories();
      await fetchTreeMapData();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create subcategory');
    }
  };

  const handleEditSubcategory = async () => {
    if (!editingSubcategory || !newSubcategoryName.trim()) {
      setError('Subcategory name cannot be empty');
      return;
    }

    try {
      const response = await fetch(`/api/subcategories/${editingSubcategory.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: newSubcategoryName.trim() }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Failed to update subcategory');
      }

      setSuccessMessage(`Subcategory updated successfully!`);
      setNewSubcategoryName('');
      setEditingSubcategory(null);
      setIsEditSubcategoryDialogOpen(false);
      await fetchCategories();
      await fetchTreeMapData();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update subcategory');
    }
  };

  const handleDeleteSubcategory = async (subcategory: Subcategory) => {
    if (!window.confirm(`Are you sure you want to delete the subcategory "${subcategory.name}"?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/subcategories/${subcategory.id}`, {
        method: 'DELETE',
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Failed to delete subcategory');
      }

      setSuccessMessage(`Subcategory "${subcategory.name}" deleted successfully!`);
      await fetchCategories();
      await fetchTreeMapData();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete subcategory');
    }
  };

  const openEditCategoryDialog = (category: Category) => {
    setEditingCategory(category);
    setNewCategoryName(category.name);
    setIsEditCategoryDialogOpen(true);
  };

  const openEditSubcategoryDialog = (subcategory: Subcategory) => {
    setEditingSubcategory(subcategory);
    setNewSubcategoryName(subcategory.name);
    setIsEditSubcategoryDialogOpen(true);
  };

  const openAddSubcategoryDialog = (category: Category) => {
    setSelectedCategoryForSub(category);
    setNewSubcategoryName('');
    setIsAddSubcategoryDialogOpen(true);
  };

  // Sort categories by name
  const sortedData = [...data].sort((a, b) => a.name.localeCompare(b.name));

  const handleSubcategoryClick = (category: string, subcategory: string) => {
    if (onNavigateToTransactions) {
      onNavigateToTransactions(category, subcategory);
    }
  };

  // Get category ID by name
  const getCategoryByName = (name: string): Category | undefined => {
    return categories.find(c => c.name === name);
  };

  // Get subcategories for a category
  const getSubcategoriesForCategory = (categoryName: string): Subcategory[] => {
    return subcategories.filter(s => s.category_name === categoryName);
  };

  if (loading) {
    return (
      <div className="container">
        <h1 className="text-3xl mb-6">Category Tree Map</h1>
        <div className={styles.loading}>
          <p>Loading tree map data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <h1 className="text-3xl mb-6">Category Tree Map</h1>
        <div className={styles.error}>
          <p>Error: {error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className={styles.header}>
        <h1 className="text-3xl mb-6">Categories</h1>
        <button
          className={styles.addButton}
          onClick={() => setIsAddCategoryDialogOpen(true)}
        >
          + Add Category
        </button>
      </div>

      {successMessage && (
        <div style={{
          padding: '1rem',
          marginBottom: '1rem',
          background: '#d4edda',
          color: '#155724',
          borderRadius: '6px',
          border: '1px solid #c3e6cb'
        }}>
          {successMessage}
          <button
            onClick={() => setSuccessMessage(null)}
            style={{
              float: 'right',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '1.2rem',
              color: '#155724'
            }}
          >
            ×
          </button>
        </div>
      )}

      {error && (
        <div className={styles.error} style={{ marginBottom: '1rem' }}>
          <p>{error}</p>
          <button
            onClick={() => setError(null)}
            style={{
              float: 'right',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '1.2rem'
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* Summary Stats */}
      <div className={styles.summaryContainer}>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{totalCategories}</div>
          <div className={styles.statLabel}>Categories</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{totalTransactions.toLocaleString()}</div>
          <div className={styles.statLabel}>Total Transactions</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>
            ${data.reduce((sum, cat) => sum + cat.amount, 0).toLocaleString()}
          </div>
          <div className={styles.statLabel}>Total Amount</div>
        </div>
      </div>

      {/* Simple Tree View */}
      <div className="card">
        <h3 className="text-xl mb-4">Category Hierarchy</h3>

        <div className={styles.treeContainer}>
          {sortedData.map((category) => {
            const categoryData = getCategoryByName(category.name);
            return (
              <div key={category.name} className={styles.categoryGroup}>
                {/* Category */}
                <div className={styles.categoryItem}>
                  <span className={styles.categoryName}>{category.name}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className={styles.categoryStats}>
                      ({category.value} transactions, ${category.amount.toLocaleString()})
                    </span>
                    {categoryData && (
                      <div className={styles.categoryActions}>
                        <button
                          className={`${styles.iconButton} ${styles.editButton}`}
                          onClick={() => openEditCategoryDialog(categoryData)}
                          title="Edit category"
                        >
                          ✏️
                        </button>
                        <button
                          className={`${styles.iconButton}`}
                          onClick={() => openAddSubcategoryDialog(categoryData)}
                          title="Add subcategory"
                        >
                          ➕
                        </button>
                        <button
                          className={`${styles.iconButton} ${styles.deleteButton}`}
                          onClick={() => handleDeleteCategory(categoryData)}
                          title="Delete category"
                        >
                          🗑️
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Subcategories */}
                {category.children && category.children.length > 0 && (
                  <div className={styles.subcategoryList}>
                    {category.children
                      .sort((a, b) => a.name.localeCompare(b.name))
                      .map((subcategory) => {
                        const subcategoryData = getSubcategoriesForCategory(category.name)
                          .find(s => s.name === subcategory.name);
                        return (
                          <div key={`${category.name}-${subcategory.name}`} className={styles.subcategoryItem}>
                            <span className={styles.subcategoryPrefix}>└─</span>
                            <button
                              className={styles.subcategoryButton}
                              onClick={() => handleSubcategoryClick(category.name, subcategory.name)}
                              title={`View ${subcategory.name} transactions`}
                            >
                              {subcategory.name}
                            </button>
                            <span className={styles.subcategoryStats}>
                              ({subcategory.value} transactions, ${subcategory.amount.toLocaleString()})
                            </span>
                            {subcategoryData && (
                              <div className={styles.subcategoryActions}>
                                <button
                                  className={`${styles.iconButton} ${styles.editButton}`}
                                  onClick={() => openEditSubcategoryDialog(subcategoryData)}
                                  title="Edit subcategory"
                                >
                                  ✏️
                                </button>
                                <button
                                  className={`${styles.iconButton} ${styles.deleteButton}`}
                                  onClick={() => handleDeleteSubcategory(subcategoryData)}
                                  title="Delete subcategory"
                                >
                                  🗑️
                                </button>
                              </div>
                            )}
                          </div>
                        );
                      })
                    }
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Add Category Dialog */}
      <Dialog
        isOpen={isAddCategoryDialogOpen}
        onClose={() => {
          setIsAddCategoryDialogOpen(false);
          setNewCategoryName('');
          setError(null);
        }}
        title="Add New Category"
      >
        <div style={{ padding: '1rem 0' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
            Category Name:
          </label>
          <input
            type="text"
            value={newCategoryName}
            onChange={(e) => setNewCategoryName(e.target.value)}
            placeholder="e.g., Shopping"
            style={{
              width: '100%',
              padding: '0.75rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.5rem',
              fontSize: '1rem',
            }}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleAddCategory();
              }
            }}
            autoFocus
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
            <button
              onClick={() => {
                setIsAddCategoryDialogOpen(false);
                setNewCategoryName('');
                setError(null);
              }}
              style={{
                padding: '0.75rem 1.5rem',
                background: 'white',
                border: '1px solid #d1d5db',
                borderRadius: '0.5rem',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleAddCategory}
              style={{
                padding: '0.75rem 1.5rem',
                background: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontWeight: '600',
              }}
            >
              Add Category
            </button>
          </div>
        </div>
      </Dialog>

      {/* Edit Category Dialog */}
      <Dialog
        isOpen={isEditCategoryDialogOpen}
        onClose={() => {
          setIsEditCategoryDialogOpen(false);
          setNewCategoryName('');
          setEditingCategory(null);
          setError(null);
        }}
        title="Edit Category"
      >
        <div style={{ padding: '1rem 0' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
            Category Name:
          </label>
          <input
            type="text"
            value={newCategoryName}
            onChange={(e) => setNewCategoryName(e.target.value)}
            style={{
              width: '100%',
              padding: '0.75rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.5rem',
              fontSize: '1rem',
            }}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleEditCategory();
              }
            }}
            autoFocus
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
            <button
              onClick={() => {
                setIsEditCategoryDialogOpen(false);
                setNewCategoryName('');
                setEditingCategory(null);
                setError(null);
              }}
              style={{
                padding: '0.75rem 1.5rem',
                background: 'white',
                border: '1px solid #d1d5db',
                borderRadius: '0.5rem',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleEditCategory}
              style={{
                padding: '0.75rem 1.5rem',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontWeight: '600',
              }}
            >
              Save Changes
            </button>
          </div>
        </div>
      </Dialog>

      {/* Add Subcategory Dialog */}
      <Dialog
        isOpen={isAddSubcategoryDialogOpen}
        onClose={() => {
          setIsAddSubcategoryDialogOpen(false);
          setNewSubcategoryName('');
          setSelectedCategoryForSub(null);
          setError(null);
        }}
        title={`Add Subcategory to ${selectedCategoryForSub?.name || ''}`}
      >
        <div style={{ padding: '1rem 0' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
            Subcategory Name:
          </label>
          <input
            type="text"
            value={newSubcategoryName}
            onChange={(e) => setNewSubcategoryName(e.target.value)}
            placeholder="e.g., Online"
            style={{
              width: '100%',
              padding: '0.75rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.5rem',
              fontSize: '1rem',
            }}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleAddSubcategory();
              }
            }}
            autoFocus
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
            <button
              onClick={() => {
                setIsAddSubcategoryDialogOpen(false);
                setNewSubcategoryName('');
                setSelectedCategoryForSub(null);
                setError(null);
              }}
              style={{
                padding: '0.75rem 1.5rem',
                background: 'white',
                border: '1px solid #d1d5db',
                borderRadius: '0.5rem',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleAddSubcategory}
              style={{
                padding: '0.75rem 1.5rem',
                background: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontWeight: '600',
              }}
            >
              Add Subcategory
            </button>
          </div>
        </div>
      </Dialog>

      {/* Edit Subcategory Dialog */}
      <Dialog
        isOpen={isEditSubcategoryDialogOpen}
        onClose={() => {
          setIsEditSubcategoryDialogOpen(false);
          setNewSubcategoryName('');
          setEditingSubcategory(null);
          setError(null);
        }}
        title="Edit Subcategory"
      >
        <div style={{ padding: '1rem 0' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
            Subcategory Name:
          </label>
          <input
            type="text"
            value={newSubcategoryName}
            onChange={(e) => setNewSubcategoryName(e.target.value)}
            style={{
              width: '100%',
              padding: '0.75rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.5rem',
              fontSize: '1rem',
            }}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleEditSubcategory();
              }
            }}
            autoFocus
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
            <button
              onClick={() => {
                setIsEditSubcategoryDialogOpen(false);
                setNewSubcategoryName('');
                setEditingSubcategory(null);
                setError(null);
              }}
              style={{
                padding: '0.75rem 1.5rem',
                background: 'white',
                border: '1px solid #d1d5db',
                borderRadius: '0.5rem',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleEditSubcategory}
              style={{
                padding: '0.75rem 1.5rem',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontWeight: '600',
              }}
            >
              Save Changes
            </button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};

export default TreeMap;
