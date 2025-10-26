import { useState, useRef } from 'react';
import { Upload, FileAudio, X, Loader, Crown } from 'lucide-react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import './AudioUpload.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function AudioUpload({ onTranscriptionComplete }) {
  const { token, user } = useAuth();
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [limitReached, setLimitReached] = useState(false);
  const fileInputRef = useRef(null);

  const allowedFormats = ['.mp3', '.wav', '.m4a', '.flac', '.ogg'];
  const maxFileSize = 16 * 1024 * 1024;

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    validateAndSetFile(file);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    validateAndSetFile(file);
  };

  const validateAndSetFile = (file) => {
    if (!file) return;

    setError('');

    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedFormats.includes(fileExt)) {
      setError(`Invalid file type. Allowed formats: ${allowedFormats.join(', ')}`);
      return;
    }

    if (file.size > maxFileSize) {
      setError('File size exceeds 16MB limit');
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setProgress(0);
    setError('');
    setLimitReached(false);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setProgress(percentCompleted);
        },
      });

      if (response.data.status === 'success') {
        onTranscriptionComplete(response.data);
      } else {
        setError(response.data.error || 'Upload failed');
      }
    } catch (err) {
      const errorData = err.response?.data;
      if (errorData?.limit_reached) {
        setLimitReached(true);
        setError(errorData.message);
      } else {
        setError(errorData?.error || 'Upload failed. Please try again.');
      }
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setError('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="audio-upload-container">
      <motion.div
        className="upload-card"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <h2 className="upload-title">Upload Audio File</h2>
        <p className="upload-subtitle">
          Transcribe audio with speaker identification and AI-powered insights
        </p>

        <div
          className={`drop-zone ${isDragging ? 'dragging' : ''} ${selectedFile ? 'has-file' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !selectedFile && fileInputRef.current?.click()}
        >
          {!selectedFile ? (
            <>
              <FileAudio className="drop-icon" size={64} />
              <p className="drop-text">Drag and drop your audio file here</p>
              <p className="drop-subtext">or click to browse</p>
              <p className="drop-formats">
                Supported formats: MP3, WAV, M4A, FLAC, OGG (Max 16MB)
              </p>
            </>
          ) : (
            <div className="selected-file">
              <FileAudio size={48} className="file-icon" />
              <div className="file-info">
                <p className="file-name">{selectedFile.name}</p>
                <p className="file-size">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                </p>
              </div>
              <button className="remove-file" onClick={handleRemoveFile}>
                <X size={20} />
              </button>
            </div>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept={allowedFormats.join(',')}
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />

        {error && (
          <motion.div
            className="error-message"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {error}
          </motion.div>
        )}

        {uploading && (
          <div className="upload-progress">
            <div className="progress-bar">
              <motion.div
                className="progress-fill"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
            <div className="progress-info">
              <Loader className="spinner" size={20} />
              <span>
                {progress < 100
                  ? `Uploading... ${progress}%`
                  : 'Processing transcription...'}
              </span>
            </div>
          </div>
        )}

        <button
          className="upload-button"
          onClick={handleUpload}
          disabled={!selectedFile || uploading}
        >
          {uploading ? (
            <>
              <Loader className="button-icon spinner" size={20} />
              Processing...
            </>
          ) : (
            <>
              <Upload className="button-icon" size={20} />
              Start Transcription
            </>
          )}
        </button>
      </motion.div>
    </div>
  );
}

export default AudioUpload;

