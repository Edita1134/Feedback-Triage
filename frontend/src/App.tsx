import React, { useState } from 'react';
import axios from 'axios';
import Dashboard from './Dashboard';
import './App.css';

interface FeedbackResponse {
  feedback_text: string;
  category: string;
  urgency_score: number;
}

function App() {
  const [currentView, setCurrentView] = useState<'form' | 'dashboard'>('form');
  const [feedbackText, setFeedbackText] = useState('');
  const [userRating, setUserRating] = useState(0);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [manualCategoryEnabled, setManualCategoryEnabled] = useState(false);
  const [result, setResult] = useState<FeedbackResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showRatingPopup, setShowRatingPopup] = useState(false);

  const categories = [
    'Bug Report',
    'Feature Request', 
    'Praise/Positive Feedback',
    'General Inquiry'
  ];

  const ratingDescriptions = [
    '',
    'Poor - Significant issues',
    'Fair - Some concerns', 
    'Good - Generally satisfied',
    'Very Good - Mostly excellent',
    'Excellent - Outstanding experience'
  ];

  const resetForm = () => {
    setFeedbackText('');
    setUserRating(0);
    setSelectedCategory('');
    setManualCategoryEnabled(false);
    setResult(null);
    setError('');
    setShowRatingPopup(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedbackText.trim()) return;
    
    // Validate manual category selection
    if (manualCategoryEnabled && !selectedCategory) {
      setError('Please select a category or disable manual category selection');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const requestData: any = { text: feedbackText };
      
      // If manual category is enabled and selected, include it in the request
      if (manualCategoryEnabled && selectedCategory) {
        requestData.category = selectedCategory;
      }
      
      const response = await axios.post<FeedbackResponse>(
        `${apiUrl}/api/triage`,
        requestData
      );
      setResult(response.data);
      setShowRatingPopup(true); // Show rating popup after successful analysis
    } catch (err: any) {
      setError(err.response?.data?.detail || 'An error occurred while analyzing your feedback');
    } finally {
      setLoading(false);
    }
  };

  const getUrgencyColor = (score: number) => {
    switch (score) {
      case 1: return '#10b981'; // green-500 - safe/good
      case 2: return '#22d3ee'; // cyan-400 - info  
      case 3: return '#f59e0b'; // amber-500 - warning
      case 4: return '#f97316'; // orange-500 - concerning
      case 5: return '#ef4444'; // red-500 - critical
      default: return '#6b7280'; // gray-500
    }
  };

  const getUrgencyLabel = (score: number) => {
    switch (score) {
      case 1: return 'Not Urgent';
      case 2: return 'Low';
      case 3: return 'Medium';
      case 4: return 'High';
      case 5: return 'Critical';
      default: return 'Unknown';
    }
  };

  const renderStars = () => {
    return (
      <div className="star-rating">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            className={`star ${star <= userRating ? 'filled' : ''}`}
            onClick={() => setUserRating(star)}
            onMouseEnter={() => setUserRating(star)}
            aria-label={`Rate ${star} stars`}
          >
            ★
          </button>
        ))}
      </div>
    );
  };

  const renderRatingPopup = () => {
    if (!showRatingPopup || !result) return null;

    return (
      <div className="modal-overlay" onClick={() => setShowRatingPopup(false)}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h3>✅ Analysis Complete!</h3>
            <button 
              className="modal-close"
              onClick={() => setShowRatingPopup(false)}
            >
              ×
            </button>
          </div>
          
          <div className="modal-body">
            <div className="analysis-results">
              <div className="result-item">
                <strong>Category:</strong> {result.category}
              </div>
              <div className="result-item">
                <strong>Urgency:</strong> 
                <span 
                  className="urgency-badge"
                  style={{ backgroundColor: getUrgencyColor(result.urgency_score) }}
                >
                  {getUrgencyLabel(result.urgency_score)} ({result.urgency_score}/5)
                </span>
              </div>
            </div>

            <div className="rating-section">
              <h4>How would you rate your overall experience?</h4>
              {renderStars()}
              <div className="rating-description">
                {ratingDescriptions[userRating]}
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button 
              className="btn btn-secondary"
              onClick={() => setShowRatingPopup(false)}
            >
              Skip Rating
            </button>
            <button 
              className="btn btn-primary"
              onClick={() => {
                setShowRatingPopup(false);
                // Here you could send the rating to the backend if needed
                console.log('Rating submitted:', userRating);
              }}
              disabled={userRating === 0}
            >
              Submit Rating
            </button>
          </div>
        </div>
      </div>
    );
  };

  const getCharacterProgress = () => {
    return Math.min((feedbackText.length / 1000) * 100, 100);
  };

  return (
    <div className="App">
      {currentView === 'dashboard' ? (
        <Dashboard onBack={() => setCurrentView('form')} />
      ) : (
        <div className="container">
          <header className="header">
            <div className="header-content">
              <h1>🚀 Feedback Triage</h1>
              <p>AI-powered feedback classification and urgency ranking system</p>
              <div className="header-nav">
                <button 
                  onClick={() => setCurrentView('dashboard')}
                  className="nav-btn"
                >
                  📊 View Dashboard
                </button>
              </div>
            </div>
          </header>

        <main className="main">
          <form onSubmit={handleSubmit}>
            <div className="form-section">
              <h2>
                📝 Your Feedback
              </h2>
              <p className="form-section-subtitle">
                Help us understand your experience better by providing detailed feedback.
              </p>

              {/* Manual Category Selection Toggle */}
              <div className="toggle-section">
                <div className="toggle-container">
                  <label className="toggle-label">
                    <input
                      type="checkbox"
                      checked={manualCategoryEnabled}
                      onChange={(e) => {
                        setManualCategoryEnabled(e.target.checked);
                        if (!e.target.checked) {
                          setSelectedCategory('');
                        }
                      }}
                      className="toggle-checkbox"
                    />
                    <span className="toggle-slider"></span>
                  </label>
                  <div className="toggle-content">
                    <span className="toggle-text">
                     Wish to select category manually?
                    </span>
                  </div>
                </div>
              </div>

              {/* Category Selection (only shown when toggle is enabled) */}
              {manualCategoryEnabled && (
                <div className="category-section">
                  <label className="label">
                    🏷️ Select Category
                  </label>
                  <div className="category-grid">
                    {categories.map((category) => (
                      <button
                        key={category}
                        type="button"
                        className={`category-option ${selectedCategory === category ? 'selected' : ''}`}
                        onClick={() => setSelectedCategory(selectedCategory === category ? '' : category)}
                      >
                        {category}
                      </button>
                    ))}
                  </div>
                  {manualCategoryEnabled && !selectedCategory && (
                    <p className="category-hint">Please select a category above</p>
                  )}
                </div>
              )}

              {/* Feedback Text */}
              <div className="form-group">
                <label htmlFor="feedback" className="label">
                  💬 Detailed Feedback
                </label>
                <textarea
                  id="feedback"
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  placeholder="Please describe your issue, feature request, or feedback in detail. The more specific you are, the better we can help you..."
                  className="textarea"
                  rows={6}
                  maxLength={1000}
                  required
                />
                <div className="char-count">
                  <span>{feedbackText.length}/1000 characters</span>
                  <div className="char-progress">
                    <div 
                      className="char-progress-bar"
                      style={{ width: `${getCharacterProgress()}%` }}
                    />
                  </div>
                  <span>{1000 - feedbackText.length} remaining</span>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || !feedbackText.trim()}
                className={`submit-btn ${loading ? 'loading' : ''}`}
              >
                {loading ? 'Analyzing your feedback...' : '🔍 Analyze Feedback'}
              </button>
            </div>
          </form>

          {error && (
            <div className="error">
              <h3>⚠️ Error</h3>
              <p>{error}</p>
            </div>
          )}

          {result && (
            <div className="result">
              <div className="result-header">
                <h3>✨ Analysis Results</h3>
                <button onClick={resetForm} className="reset-btn">
                  🔄 New Feedback
                </button>
              </div>
              <div className="result-grid">
                <div className="result-item">
                  <div className="result-label">Category</div>
                  <div className="result-value category">
                    🏷️ {result.category}
                  </div>
                </div>
                <div className="result-item">
                  <div className="result-label">Urgency Level</div>
                  <div className="result-value urgency">
                    <span 
                      className="urgency-indicator"
                      style={{ backgroundColor: getUrgencyColor(result.urgency_score) }}
                    />
                    {getUrgencyLabel(result.urgency_score)} ({result.urgency_score}/5)
                  </div>
                </div>
                <div className="result-item full-width">
                  <div className="result-label">Your Feedback</div>
                  <div className="result-value feedback-text">
                    "{result.feedback_text}"
                  </div>
                </div>
                {userRating > 0 && (
                  <div className="result-item full-width">
                    <div className="result-label">Your Rating</div>
                    <div className="result-value">
                      <div className="star-rating">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <span
                            key={star}
                            className={`star ${star <= userRating ? 'filled' : ''}`}
                          >
                            ★
                          </span>
                        ))}
                      </div>
                      <span style={{ marginLeft: '0.5rem', color: 'var(--text-secondary)' }}>
                        {ratingDescriptions[userRating]}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </main>

        <footer className="footer">
          <div className="footer-content">
            <span>⚡ Powered by AI</span>
            <span>•</span>
            <span>Built with React & FastAPI</span>
            <button 
              onClick={() => setCurrentView('dashboard')}
              className="footer-nav-btn"
            >
              📊 Dashboard
            </button>
          </div>
        </footer>
      </div>
      )}
      
      {/* Rating Popup Modal */}
      {renderRatingPopup()}
    </div>
  );
}

export default App;
