import styles from './StatusTag.module.css';

interface StatusTagProps {
  status: 'pending' | 'processing' | 'success' | 'warning' | 'error';
  children: React.ReactNode;
}

function StatusTag({ status, children }: StatusTagProps) {
  return (
    <span className={`${styles.statusTag} ${styles[status]}`}>
      {children}
    </span>
  );
}

export default StatusTag;
