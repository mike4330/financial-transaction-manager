import React from 'react';
import styles from './Dialog.module.css';

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  details?: string[];
  confirmText?: string;
  cancelText?: string;
  type?: 'success' | 'error' | 'warning' | 'info';
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  details,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  type = 'info'
}) => {
  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const getIcon = () => {
    switch (type) {
      case 'success':
        return '✅';
      case 'error':
        return '❌';
      case 'warning':
        return '⚠️';
      default:
        return '❓';
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div className={styles.titleSection}>
            <span className={styles.icon}>{getIcon()}</span>
            <h3 className={styles.title}>{title}</h3>
          </div>
          <button className={styles.closeButton} onClick={onClose}>
            ×
          </button>
        </div>
        
        <div className={styles.content}>
          <p className={styles.message}>{message}</p>
          {details && details.length > 0 && (
            <div className={styles.details}>
              {details.map((detail, index) => (
                <p key={index} className={styles.detail}>{detail}</p>
              ))}
            </div>
          )}
        </div>
        
        <div className={styles.actions}>
          <button className={styles.cancelButton} onClick={onClose}>
            {cancelText}
          </button>
          <button 
            className={`${styles.confirmButton} ${styles[type]}`} 
            onClick={handleConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;