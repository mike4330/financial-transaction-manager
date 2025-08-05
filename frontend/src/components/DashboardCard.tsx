import React from 'react';
import { DashboardCard as DashboardCardType } from '../types/dashboard';
import { useTimeRange } from '../contexts/TimeRangeContext';
import { MemoizedGenericChart as GenericChart } from './GenericChart';
import { PercentageChart } from './PercentageChart';
import StackedChart from './StackedChart';
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
          enabled: true,
          endpoint: card.data.endpoint // Pass through custom endpoint if provided
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
      
      case 'stacked':
        return (
          <StackedChart
            category={card.data.category}
            title={card.title}
            color={card.config?.color}
            currency={card.config?.currency}
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