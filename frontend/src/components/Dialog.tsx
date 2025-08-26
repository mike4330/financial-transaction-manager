import React from 'react';
import styles from './Dialog.module.css';

interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message?: string;
  children?: React.ReactNode;
  type?: 'success' | 'error' | 'warning' | 'info';
  showCancel?: boolean;
  onConfirm?: () => void;
  confirmText?: string;
  cancelText?: string;
}

const Dialog: React.FC<DialogProps> = ({
  isOpen,
  onClose,
  title,
  message,
  children,
  type = 'info',
  showCancel = false,
  onConfirm,
  confirmText = 'OK',
  cancelText = 'Cancel'
}) => {
  if (!isOpen) return null;

  const handleConfirm = () => {
    if (onConfirm) {
      onConfirm();
    }
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
        return 'ℹ️';
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
          {children ? children : <p className={styles.message}>{message}</p>}
        </div>
        
        {!children && (
          <div className={styles.actions}>
            {showCancel && (
              <button className={styles.cancelButton} onClick={onClose}>
                {cancelText}
              </button>
            )}
            <button 
              className={`${styles.confirmButton} ${styles[type]}`} 
              onClick={handleConfirm}
            >
              {confirmText}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dialog;