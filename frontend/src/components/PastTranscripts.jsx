import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FileText, Clock, TrendingUp, Trash2, Download, Search, Loader, ArrowLeft } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import TranscriptResults from './TranscriptResults';
import './PastTranscripts.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function PastTranscripts() {
  const { token } = useAuth();
  const [transcripts, setTranscripts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState('');
  const [selectedTranscript, setSelectedTranscript] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  useEffect(() => {
    if (token) {
      fetchTranscripts();
    }
  }, [token]);

  const fetchTranscripts = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`${API_URL}/api/transcripts`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.data.status === 'success') {
        setTranscripts(response.data.transcripts);
      } else {
        setError(response.data.error || 'Failed to load transcripts');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load transcripts');
    } finally {
      setLoading(false);
    }
  };

  const handleTranscriptClick = async (sessionId) => {
    setLoadingDetails(true);
    try {
      const response = await axios.get(`${API_URL}/api/transcript/${sessionId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.data.status === 'success') {
        const { transcript, utterances } = response.data;
        
        const formattedUtterances = utterances.map(u => ({
          speaker: u.speaker,
          text: u.text,
          confidence: u.confidence,
          start: u.start_time,
          end: u.end_time
        }));
        
        const transcriptData = {
          session_id: sessionId,
          result: {
            text: transcript.text,
            confidence: transcript.confidence,
            audio_duration: transcript.audio_duration,
            utterances: formattedUtterances
          }
        };
        
        setSelectedTranscript(transcriptData);
      }
    } catch (err) {
      alert('Failed to load transcript details');
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleBackToList = () => {
    setSelectedTranscript(null);
  };

  const handleDelete = async (sessionId) => {
    if (!confirm('Are you sure you want to delete this transcript?')) return;

    try {
      await axios.delete(`${API_URL}/api/transcript/${sessionId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setTranscripts(transcripts.filter((t) => t.session_id !== sessionId));
    } catch (err) {
      alert('Failed to delete transcript');
    }
  };

  const handleDownload = async (sessionId, filename) => {
    try {
      const response = await axios.get(`${API_URL}/api/transcript/${sessionId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const { transcript, utterances } = response.data;

      let content = `Transcript: ${filename}\n${'='.repeat(50)}\n\n`;
      content += `Created: ${new Date(transcript.created_at).toLocaleString()}\n`;
      content += `Duration: ${formatDuration(transcript.audio_duration)}\n`;
      content += `Confidence: ${Math.round((transcript.confidence || 0) * 100)}%\n\n`;
      content += `${transcript.text}\n\n`;

      if (utterances && utterances.length > 0) {
        content += `Speaker Breakdown:\n${'-'.repeat(50)}\n`;
        utterances.forEach((u) => {
          content += `\n${u.speaker}: ${u.text}\n`;
        });
      }

      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `transcript_${filename.replace(/\.[^/.]+$/, '')}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download transcript');
    }
  };

  const formatDuration = (ms) => {
    const seconds = Math.floor(ms / 1000);
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const filteredTranscripts = transcripts.filter(
    (t) =>
      t.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.text.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (selectedTranscript) {
    return (
      <div className="transcript-detail-view">
        <button className="back-button" onClick={handleBackToList}>
          <ArrowLeft size={20} />
          <span>Back to History</span>
        </button>
        <TranscriptResults data={selectedTranscript} onReset={handleBackToList} />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="past-transcripts loading-state">
        <Loader className="spinner" size={48} />
        <p>Loading transcripts...</p>
      </div>
    );
  }

  if (loadingDetails) {
    return (
      <div className="past-transcripts loading-state">
        <Loader className="spinner" size={48} />
        <p>Loading transcript details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="past-transcripts error-state">
        <p>{error}</p>
        <button onClick={fetchTranscripts}>Retry</button>
      </div>
    );
  }

  return (
    <div className="past-transcripts">
      <motion.div
        className="transcripts-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h2>Past Transcripts</h2>
        <div className="search-bar">
          <Search size={20} />
          <input
            type="text"
            placeholder="Search transcripts..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </motion.div>

      {filteredTranscripts.length === 0 ? (
        <motion.div
          className="empty-state"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <FileText size={64} className="empty-icon" />
          <h3>No Transcripts Found</h3>
          <p>
            {searchTerm
              ? 'Try adjusting your search'
              : 'Upload an audio file to get started'}
          </p>
        </motion.div>
      ) : (
        <div className="transcripts-grid">
          {filteredTranscripts.map((transcript, index) => (
            <motion.div
              key={transcript.session_id}
              className="transcript-card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <div 
                className="card-content" 
                onClick={() => handleTranscriptClick(transcript.session_id)}
              >
                <div className="card-header">
                  <FileText className="card-icon" />
                  <h3 className="card-title">{transcript.filename}</h3>
                </div>

                <p className="card-preview">
                  {transcript.text.substring(0, 150)}
                  {transcript.text.length > 150 ? '...' : ''}
                </p>

                <div className="card-stats">
                  <div className="stat">
                    <Clock size={16} />
                    <span>{formatDuration(transcript.audio_duration || 0)}</span>
                  </div>
                  <div className="stat">
                    <TrendingUp size={16} />
                    <span>{Math.round((transcript.confidence || 0) * 100)}%</span>
                  </div>
                </div>

                <div className="card-date">{formatDate(transcript.created_at)}</div>
              </div>

              <div className="card-footer">
                <div className="card-actions">
                  <button
                    className="icon-button download"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDownload(transcript.session_id, transcript.filename);
                    }}
                    title="Download"
                  >
                    <Download size={18} />
                  </button>
                  <button
                    className="icon-button delete"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(transcript.session_id);
                    }}
                    title="Delete"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}

export default PastTranscripts;

