import { useState } from 'react';
import { Upload, Mic, FileText, Crown, LogOut, User } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from './context/AuthContext';
import Auth from './components/Auth';
import AudioUpload from './components/AudioUpload';
import TranscriptResults from './components/TranscriptResults';
import PastTranscripts from './components/PastTranscripts';
import PremiumUpgrade from './components/PremiumUpgrade';
import './App.css';

function App() {
  const { user, logout, loading, isAuthenticated, isPremium } = useAuth();
  const [currentView, setCurrentView] = useState('upload');
  const [transcriptData, setTranscriptData] = useState(null);
  const [showPremiumModal, setShowPremiumModal] = useState(false);

  const handleTranscriptionComplete = (data) => {
    setTranscriptData(data);
    setCurrentView('results');
  };

  const handleReset = () => {
    setTranscriptData(null);
    setCurrentView('upload');
  };

  const handleUpgradeClick = () => {
    setShowPremiumModal(true);
  };

  if (loading) {
    return (
      <div className="app loading-state">
        <div className="loader"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Auth />;
  }

  return (
    <div className="app">
      <header className="app-header">
        <motion.div 
          className="logo"
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Mic className="logo-icon" />
          <h1>AI Speaker Recognition</h1>
        </motion.div>
        
        <nav className="nav-tabs">
          <button 
            className={`nav-tab ${currentView === 'upload' ? 'active' : ''}`}
            onClick={() => setCurrentView('upload')}
          >
            <Upload size={20} />
            <span>Upload</span>
          </button>
          <button 
            className={`nav-tab ${currentView === 'history' ? 'active' : ''}`}
            onClick={() => setCurrentView('history')}
          >
            <FileText size={20} />
            <span>History</span>
          </button>
        </nav>

        <div className="user-menu">
          {!isPremium && (
            <button className="premium-cta" onClick={handleUpgradeClick}>
              <Crown size={16} />
              <span>Upgrade</span>
            </button>
          )}
          {isPremium && (
            <span className="premium-badge-header">
              <Crown size={16} />
              Premium
            </span>
          )}
          <div className="user-info">
            <User size={18} />
            <span>{user?.email}</span>
          </div>
          <button className="logout-btn" onClick={logout} title="Logout">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <main className="app-main">
        <AnimatePresence mode="wait">
          {currentView === 'upload' && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <AudioUpload onTranscriptionComplete={handleTranscriptionComplete} />
            </motion.div>
          )}
          
          {currentView === 'results' && transcriptData && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <TranscriptResults data={transcriptData} onReset={handleReset} />
            </motion.div>
          )}
          
          {currentView === 'history' && (
            <motion.div
              key="history"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <PastTranscripts />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="app-footer">
        <p>@Made by Shubh</p>
      </footer>

      {showPremiumModal && (
        <PremiumUpgrade onClose={() => setShowPremiumModal(false)} />
      )}
    </div>
  );
}

export default App;
