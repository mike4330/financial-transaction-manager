import React from 'react';
import { useNavigate } from 'react-router-dom';
import { DashboardConfig } from '../types/dashboard';
import { defaultDashboardConfig } from '../config/dashboardConfig';
import DashboardCard from './DashboardCard';
import styles from './Dashboard.module.css';

interface DashboardProps {
  config?: DashboardConfig;
  onNavigateToTransactions?: (category?: string, subcategory?: string) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ 
  config = defaultDashboardConfig, 
  onNavigateToTransactions 
}) => {
  const navigate = useNavigate();

  const handleNavigateToTransactions = (category?: string, subcategory?: string) => {
    if (onNavigateToTransactions) {
      onNavigateToTransactions(category, subcategory);
    } else {
      // Default router-based navigation
      if (category && subcategory) {
        navigate(`/transactions/${encodeURIComponent(category)}/${encodeURIComponent(subcategory)}`);
      } else if (category) {
        navigate(`/transactions/${encodeURIComponent(category)}`);
      } else {
        navigate('/transactions');
      }
    }
  };

  const gridStyle: React.CSSProperties = {
    gridTemplateColumns: `repeat(${config.grid.columns}, 1fr)`,
    gridTemplateRows: `repeat(${config.grid.rows}, minmax(200px, auto))`,
    gap: config.grid.gap
  };

  return (
    <div className={styles.grid} style={gridStyle}>
      {config.cards.map(card => (
        <DashboardCard 
          key={card.id} 
          card={card} 
          onNavigateToTransactions={handleNavigateToTransactions}
        />
      ))}
    </div>
  );
};

export default Dashboard;