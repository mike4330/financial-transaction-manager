import React, { useRef, useState } from 'react';
import styles from './FileUpload.module.css';

interface FileUploadProps {
  onUploadSuccess?: () => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [messageType, setMessageType] = useState<'success' | 'error'>('success');

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.csv')) {
      setUploadMessage('Please select a CSV file');
      setMessageType('error');
      setTimeout(() => setUploadMessage(null), 3000);
      return;
    }

    setIsUploading(true);
    setUploadMessage(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/upload-csv', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (response.ok) {
        setUploadMessage(`Successfully uploaded: ${file.name}`);
        setMessageType('success');
        onUploadSuccess?.();
      } else {
        setUploadMessage(result.error || 'Upload failed');
        setMessageType('error');
      }
    } catch (error) {
      setUploadMessage('Upload failed: Network error');
      setMessageType('error');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      setTimeout(() => setUploadMessage(null), 3000);
    }
  };

  return (
    <div className={styles.uploadContainer}>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />
      <button
        onClick={handleUploadClick}
        disabled={isUploading}
        className={styles.uploadButton}
        title="Upload CSV file"
      >
        {isUploading ? (
          <span className={styles.spinner}>⟳</span>
        ) : (
          <span>📁</span>
        )}
      </button>
      {uploadMessage && (
        <div className={`${styles.message} ${styles[messageType]}`}>
          {uploadMessage}
        </div>
      )}
    </div>
  );
};