import React, { useState, useEffect } from 'react';
import styles from './TreeMap.module.css';

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

interface TreeMapProps {
  onNavigateToTransactions?: (category?: string, subcategory?: string) => void;
}

const TreeMap: React.FC<TreeMapProps> = ({ onNavigateToTransactions }) => {
  const [data, setData] = useState<TreeMapData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCategories, setTotalCategories] = useState(0);
  const [totalTransactions, setTotalTransactions] = useState(0);

  useEffect(() => {
    fetchTreeMapData();
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

  // Sort categories by name
  const sortedData = [...data].sort((a, b) => a.name.localeCompare(b.name));

  const handleSubcategoryClick = (category: string, subcategory: string) => {
    if (onNavigateToTransactions) {
      onNavigateToTransactions(category, subcategory);
    }
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
      <h1 className="text-3xl mb-6">Categories</h1>
      
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
          {sortedData.map((category) => (
            <div key={category.name} className={styles.categoryGroup}>
              {/* Category */}
              <div className={styles.categoryItem}>
                <span className={styles.categoryName}>{category.name}</span>
                <span className={styles.categoryStats}>
                  ({category.value} transactions, ${category.amount.toLocaleString()})
                </span>
              </div>
              
              {/* Subcategories */}
              {category.children && category.children.length > 0 && (
                <div className={styles.subcategoryList}>
                  {category.children
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .map((subcategory) => (
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
                      </div>
                    ))
                  }
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TreeMap;