import React from 'react';
import { DashboardCard as DashboardCardType } from '../types/dashboard';
import { useTimeRange } from '../contexts/TimeRangeContext';
import { GenericChart } from './GenericChart';
import { PercentageChart } from './PercentageChart';
import type { ChartConfig } from '../config/chartConfig';
import StatCard from './StatCard';
import SummaryCard from './SummaryCard';
import styles from './DashboardCard.module.css';

interface DashboardCardProps {
  card: DashboardCardType;
}

const DashboardCard: React.FC<DashboardCardProps> = ({ card }) => {
  const { timeRange } = useTimeRange();
  
  const cardStyle: React.CSSProperties = {
    gridColumn: `${card.layout.col} / span ${card.layout.width}`,
    gridRow: `${card.layout.row} / span ${card.layout.height}`
  };

  const renderVisualization = () => {
    switch (card.visualization) {
      case 'timeseries':
        // Convert dashboard card config to ChartConfig format
        const chartConfig = {
          id: card.id,
          title: card.title,
          emoji: '📊', // default emoji
          category: card.data.category,
          subcategory: card.data.subcategory || '',
          color: card.config?.color || '#3b82f6',
          enabled: true
        };
        
        return <GenericChart config={chartConfig} />;
      
      case 'percentage':
        return <PercentageChart card={card} />;
      
      case 'stat':
        return (
          <StatCard
            title={card.title}
            category={card.data.category}
            subcategory={card.data.subcategory}
            currency={card.config?.currency}
            color={card.config?.color}
          />
        );
      
      case 'summary':
        return (
          <SummaryCard
            title={card.title}
            category={card.data.category}
            subcategory={card.data.subcategory}
          />
        );
      
      default:
        return <div>Unknown visualization type: {card.visualization}</div>;
    }
  };

  return (
    <div className={styles.card} style={cardStyle}>
      {renderVisualization()}
    </div>
  );
};

export default DashboardCard;