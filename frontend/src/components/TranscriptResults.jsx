import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  FileText,
  Users,
  Clock,
  TrendingUp,
  Download,
  RefreshCw,
  Play,
  Pause,
  Sparkles,
  Brain,
  BarChart3,
  Loader,
} from 'lucide-react';
import axios from 'axios';
import './TranscriptResults.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function TranscriptResults({ data, onReset }) {
  const [aiInsights, setAiInsights] = useState(null);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [insightsError, setInsightsError] = useState('');
  const [playingIndex, setPlayingIndex] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);

  const { result, session_id } = data;
  const { text, utterances, confidence, audio_duration } = result;

  const speakers = utterances ? [...new Set(utterances.map((u) => u.speaker))].length : 0;
  const duration = audio_duration ? Math.floor(audio_duration / 1000) : 0;
  const minutes = Math.floor(duration / 60);
  const seconds = duration % 60;

  const handleGenerateInsights = async () => {
    setLoadingInsights(true);
    setInsightsError('');

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API_URL}/api/analyze/${session_id}`, {}, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.data.status === 'success') {
        setAiInsights(response.data.analysis);
      } else {
        setInsightsError(response.data.error || 'Failed to generate insights');
      }
    } catch (err) {
      setInsightsError(err.response?.data?.error || 'Failed to generate insights');
    } finally {
      setLoadingInsights(false);
    }
  };

  const handleDownload = () => {
    let content = `Transcript\n${'='.repeat(50)}\n\n`;
    content += `Duration: ${minutes}:${seconds.toString().padStart(2, '0')}\n`;
    content += `Speakers: ${speakers}\n`;
    content += `Confidence: ${Math.round((confidence || 0) * 100)}%\n\n`;
    content += `Full Transcript:\n${'-'.repeat(50)}\n${text}\n\n`;

    if (utterances && utterances.length > 0) {
      content += `\nSpeaker Breakdown:\n${'-'.repeat(50)}\n`;
      utterances.forEach((utterance) => {
        const start = formatTime(utterance.start);
        const end = formatTime(utterance.end);
        content += `\n[${start} - ${end}] ${utterance.speaker}:\n${utterance.text}\n`;
      });
    }

    if (aiInsights) {
      content += `\n\nAI Insights:\n${'='.repeat(50)}\n`;
      content += `\n${aiInsights.summary || ''}\n`;
      if (aiInsights.key_points) {
        content += `\nKey Points:\n`;
        aiInsights.key_points.forEach((point, i) => {
          content += `${i + 1}. ${point}\n`;
        });
      }
      if (aiInsights.sentiment) {
        content += `\nSentiment: ${aiInsights.sentiment}\n`;
      }
      if (aiInsights.action_items) {
        content += `\nAction Items:\n`;
        aiInsights.action_items.forEach((item, i) => {
          content += `${i + 1}. ${item}\n`;
        });
      }
    }

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcript_${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const formatTime = (ms) => {
    const totalSeconds = Math.floor(ms / 1000);
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const playSegment = async (index, start, end) => {
    try {
      if (playingIndex === index && audioRef.current) {
        if (isPlaying) {
          audioRef.current.pause();
          setIsPlaying(false);
        } else {
          await audioRef.current.play();
          setIsPlaying(true);
        }
        return;
      }

      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }

      const audio = new Audio(`${API_URL}/audio_segment/${session_id}/${start}/${end}`);
      audioRef.current = audio;
      
      audio.onended = () => {
        setPlayingIndex(null);
        setIsPlaying(false);
        audioRef.current = null;
      };

      audio.onerror = () => {
        setPlayingIndex(null);
        setIsPlaying(false);
        audioRef.current = null;
        console.error('Failed to play audio segment');
      };

      setPlayingIndex(index);
      setIsPlaying(true);
      await audio.play();
    } catch (err) {
      console.error('Failed to play audio segment:', err);
      setPlayingIndex(null);
      setIsPlaying(false);
    }
  };

  return (
    <div className="transcript-results">
      <motion.div
        className="results-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h2>Transcription Results</h2>
        <div className="header-actions">
          <button className="action-button secondary" onClick={handleDownload}>
            <Download size={18} />
            Download
          </button>
          <button className="action-button" onClick={onReset}>
            <RefreshCw size={18} />
            New Upload
          </button>
        </div>
      </motion.div>

      <div className="stats-grid">
        <motion.div
          className="stat-card"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
        >
          <TrendingUp className="stat-icon" />
          <div className="stat-content">
            <div className="stat-value">{Math.round((confidence || 0) * 100)}%</div>
            <div className="stat-label">Confidence</div>
          </div>
        </motion.div>

        <motion.div
          className="stat-card"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <Clock className="stat-icon" />
          <div className="stat-content">
            <div className="stat-value">
              {minutes}:{seconds.toString().padStart(2, '0')}
            </div>
            <div className="stat-label">Duration</div>
          </div>
        </motion.div>

        <motion.div
          className="stat-card"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
        >
          <Users className="stat-icon" />
          <div className="stat-content">
            <div className="stat-value">{speakers}</div>
            <div className="stat-label">Speakers</div>
          </div>
        </motion.div>
      </div>

      <motion.div
        className="transcript-section"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <div className="section-header">
          <FileText size={24} />
          <h3>Full Transcript</h3>
        </div>
        <div className="transcript-text">{text}</div>
      </motion.div>

      {utterances && utterances.length > 0 && (
        <motion.div
          className="utterances-section"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <div className="section-header">
            <Users size={24} />
            <h3>Speaker Breakdown</h3>
          </div>
          <div className="utterances-list">
            {utterances.map((utterance, index) => {
              const isCurrentlyPlaying = playingIndex === index && isPlaying;
              const isPaused = playingIndex === index && !isPlaying;
              
              return (
                <motion.div
                  key={index}
                  className={`utterance-card ${isCurrentlyPlaying || isPaused ? 'playing' : ''}`}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 * index }}
                  onClick={() => playSegment(index, utterance.start, utterance.end)}
                >
                  <div className="utterance-header">
                    <span className="speaker-label">{utterance.speaker}</span>
                    <span className="time-range">
                      {formatTime(utterance.start)} - {formatTime(utterance.end)}
                    </span>
                    {isCurrentlyPlaying ? (
                      <Pause size={16} className="play-icon active" />
                    ) : (
                      <Play size={16} className={`play-icon ${isPaused ? 'paused' : ''}`} />
                    )}
                  </div>
                  <p className="utterance-text">{utterance.text}</p>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      )}

      <motion.div
        className="ai-insights-section"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
      >
        <div className="section-header">
          <Sparkles size={24} />
          <h3>AI-Powered Insights</h3>
          {!aiInsights && (
            <button
              className="generate-button"
              onClick={handleGenerateInsights}
              disabled={loadingInsights}
            >
              {loadingInsights ? (
                <>
                  <Loader className="spinner" size={18} />
                  Generating...
                </>
              ) : (
                <>
                  <Brain size={18} />
                  Generate Insights
                </>
              )}
            </button>
          )}
        </div>

        {insightsError && <div className="error-message">{insightsError}</div>}

        {aiInsights && (
          <motion.div
            className="insights-content"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {aiInsights.summary && (
              <div className="insight-block">
                <h4>Summary</h4>
                <p>{aiInsights.summary}</p>
              </div>
            )}

            {aiInsights.key_points && aiInsights.key_points.length > 0 && (
              <div className="insight-block">
                <h4>Key Points</h4>
                <ul>
                  {aiInsights.key_points.map((point, i) => (
                    <li key={i}>{point}</li>
                  ))}
                </ul>
              </div>
            )}

            {aiInsights.sentiment && (
              <div className="insight-block">
                <h4>Overall Sentiment</h4>
                <p className="sentiment-badge">{aiInsights.sentiment}</p>
              </div>
            )}

            {aiInsights.action_items && aiInsights.action_items.length > 0 && (
              <div className="insight-block">
                <h4>Action Items</h4>
                <ul>
                  {aiInsights.action_items.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

export default TranscriptResults;

