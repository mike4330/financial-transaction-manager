import React from 'react';
import { DashboardCard as DashboardCardType } from '../types/dashboard';
import { useIntersectionObserver } from '../hooks/useIntersectionObserver';
import DashboardCard from './DashboardCard';

interface LazyDashboardCardProps {
  card: DashboardCardType;
}

const LazyDashboardCard: React.FC<LazyDashboardCardProps> = ({ card }) => {
  const { elementRef, hasBeenVisible } = useIntersectionObserver({
    threshold: 0.1,
    rootMargin: '100px', // Start loading when card is 100px from viewport
    triggerOnce: true
  });

  const cardStyle: React.CSSProperties = {
    gridColumn: `${card.layout.col} / span ${card.layout.width}`,
    gridRow: `${card.layout.row} / span ${card.layout.height}`,
    minHeight: '200px' // Prevent layout shift
  };

  return (
    <div ref={elementRef} style={cardStyle}>
      {hasBeenVisible ? (
        <DashboardCard card={card} />
      ) : (
        <div 
          style={{
            background: '#f8f9fa',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            minHeight: '180px',
            color: '#6b7280',
            fontSize: '0.875rem'
          }}
        >
          Loading {card.title}...
        </div>
      )}
    </div>
  );
};

export default React.memo(LazyDashboardCard);