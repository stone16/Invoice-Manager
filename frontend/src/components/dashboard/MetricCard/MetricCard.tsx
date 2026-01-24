import React from 'react';
import styles from './MetricCard.module.css';

interface MetricCardProps {
  label: string;
  value: string | number;
  prefix?: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, prefix = '' }) => {
  return (
    <div className={styles.metricCard}>
      <div className={styles.label}>{label}</div>
      <div className={styles.value}>
        {prefix}{value}
      </div>
    </div>
  );
};

export default MetricCard;
