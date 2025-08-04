import React from 'react';
import { DashboardConfig } from '../types/dashboard';
import DashboardCard from './DashboardCard';
import styles from './Dashboard.module.css';

interface DashboardProps {
  config: DashboardConfig;
}

const Dashboard: React.FC<DashboardProps> = ({ config }) => {
  const gridStyle: React.CSSProperties = {
    gridTemplateColumns: `repeat(${config.grid.columns}, 1fr)`,
    gridTemplateRows: `repeat(${config.grid.rows}, minmax(200px, auto))`,
    gap: config.grid.gap
  };

  return (
    <div className={styles.grid} style={gridStyle}>
      {config.cards.map(card => (
        <DashboardCard key={card.id} card={card} />
      ))}
    </div>
  );
};

export default Dashboard;