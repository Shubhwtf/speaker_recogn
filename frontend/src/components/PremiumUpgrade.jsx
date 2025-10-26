import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import './PremiumUpgrade.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const PremiumUpgrade = ({ onClose }) => {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [scriptLoaded, setScriptLoaded] = useState(false);

  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onload = () => setScriptLoaded(true);
    script.onerror = () => {
      console.error('Failed to load Razorpay SDK');
      setError('Failed to load payment gateway');
    };
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, []);

  const handleUpgrade = async () => {
    setLoading(true);
    setError('');

    try {
      const orderResponse = await fetch(`${API_URL}/api/auth/create_order`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!orderResponse.ok) {
        throw new Error('Failed to create order');
      }

      const orderData = await orderResponse.json();
      
      const options = {
        key: orderData.key_id,
        amount: orderData.amount,
        currency: orderData.currency,
        name: 'AI Speaker Recognition',
        description: 'Premium Plan - Unlimited Transcripts',
        order_id: orderData.order_id,
        handler: async function (response) {
          try {
            const verifyResponse = await fetch(`${API_URL}/api/auth/verify_payment`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
              },
              body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature
              })
            });

            if (!verifyResponse.ok) {
              throw new Error('Payment verification failed');
            }

            const verifyData = await verifyResponse.json();
            
            if (verifyData.token) {
              localStorage.setItem('token', verifyData.token);
            }
            
            setSuccess(true);
            
            setTimeout(() => {
              window.location.replace(window.location.origin);
            }, 2000);
            
          } catch (err) {
            setError('Payment verification failed. Please contact support.');
            setLoading(false);
          }
        },
        prefill: {
          email: user?.email || '',
          name: user?.full_name || ''
        },
        theme: {
          color: '#00CED1'
        },
        modal: {
          ondismiss: function() {
            setLoading(false);
            setError('Payment cancelled');
          }
        }
      };

      if (!window.Razorpay) {
        throw new Error('Razorpay SDK not loaded');
      }

      const razorpay = new window.Razorpay(options);
      razorpay.open();
      
    } catch (err) {
      setError(err.message || 'Payment failed. Please try again.');
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="premium-overlay">
        <div className="premium-modal success-modal">
          <div className="success-icon">✓</div>
          <h2>Welcome to Premium!</h2>
          <p>You now have unlimited access to all features.</p>
          <p className="redirect-text">Redirecting to home page...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="premium-overlay">
      <div className="premium-modal">
        <button className="close-button" onClick={onClose}>×</button>
        
        <div className="premium-header">
          <div className="premium-badge">Premium</div>
          <h2 className="premium-title">Upgrade to Premium</h2>
          <div className="premium-price">
            <span className="currency">₹</span>
            <span className="amount">99</span>
            <span className="period">one-time</span>
          </div>
        </div>

        <div className="premium-features">
          <div className="feature-item">
            <div className="feature-icon">∞</div>
            <div className="feature-content">
              <h3>Unlimited Transcripts</h3>
              <p>Store as many audio transcriptions as you need</p>
            </div>
          </div>

          <div className="feature-item">
            <div className="feature-icon">🤖</div>
            <div className="feature-content">
              <h3>AI-Powered Analysis</h3>
              <p>Get summaries, sentiment analysis, and key points</p>
            </div>
          </div>

          <div className="feature-item">
            <div className="feature-icon">🎙️</div>
            <div className="feature-content">
              <h3>Advanced Speaker Recognition</h3>
              <p>Identify and separate multiple speakers accurately</p>
            </div>
          </div>

          <div className="feature-item">
            <div className="feature-icon">💾</div>
            <div className="feature-content">
              <h3>Cloud Storage</h3>
              <p>Access your transcripts from anywhere, anytime</p>
            </div>
          </div>
        </div>

        {user && !user.is_premium && (
          <div className="current-usage">
            <p>Current plan: <strong>Free ({user.transcript_count || 0}/3 transcripts)</strong></p>
          </div>
        )}

        {error && <div className="error-message">{error}</div>}

        <button 
          className="upgrade-button"
          onClick={handleUpgrade}
          disabled={loading || !scriptLoaded}
        >
          {loading ? 'Processing...' : !scriptLoaded ? 'Loading...' : 'Pay ₹99 with Razorpay'}
        </button>

        <div className="premium-note">
          <p>🔒 Secure payment powered by Razorpay</p>
          <p className="payment-methods">Accepts UPI, Cards, Net Banking & More</p>
        </div>
      </div>
    </div>
  );
};

export default PremiumUpgrade;

