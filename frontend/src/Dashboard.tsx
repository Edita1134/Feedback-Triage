import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Dashboard.css';

interface FeedbackHistory {
  id: number;
  feedback_text: string;
  category: string;
  urgency_score: number;
  confidence_score?: number;
  processing_time?: number;
  llm_provider?: string;
  created_at: string;
  user_ip?: string;
}

interface DashboardStats {
  total_feedback: number;
  categories: Record<string, number>;
  urgency_distribution: Record<string, number>;
  avg_processing_time?: number;
  recent_feedback: FeedbackHistory[];
}

interface DashboardProps {
  onBack?: () => void;
}

function Dashboard({ onBack }: DashboardProps) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await axios.get<DashboardStats>(`${apiUrl}/api/dashboard`);
      setStats(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const getUrgencyColor = (score: number) => {
    switch (score) {
      case 1: return '#10b981'; // green-500
      case 2: return '#22d3ee'; // cyan-400
      case 3: return '#f59e0b'; // amber-500
      case 4: return '#f97316'; // orange-500
      case 5: return '#ef4444'; // red-500
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'Bug Report': return '🐛';
      case 'Feature Request': return '💡';
      case 'Praise/Positive Feedback': return '😊';
      case 'General Inquiry': return '❓';
      default: return '📝';
    }
  };

  if (loading) {
    return (
      <div className="dashboard">
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard">
        <div className="error">
          <h3>⚠️ Error</h3>
          <p>{error}</p>
          <button onClick={fetchDashboard} className="retry-btn">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-left">
          {onBack && (
            <button onClick={onBack} className="back-btn">
              ← Back to Form
            </button>
          )}
          <h1>📊 Feedback Dashboard</h1>
        </div>
        
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">📈</div>
          <div className="stat-content">
            <h3>Total Feedback</h3>
            <div className="stat-value">{stats.total_feedback}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">⚡</div>
          <div className="stat-content">
            <h3>Avg Processing Time</h3>
            <div className="stat-value">
              {stats.avg_processing_time ? `${stats.avg_processing_time.toFixed(2)}s` : 'N/A'}
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🏷️</div>
          <div className="stat-content">
            <h3>Categories</h3>
            <div className="stat-value">{Object.keys(stats.categories).length}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🚨</div>
          <div className="stat-content">
            <h3>Critical Issues</h3>
            <div className="stat-value">{stats.urgency_distribution['5'] || 0}</div>
          </div>
        </div>
      </div>

      <div className="charts-section">
        <div className="chart-container">
          <h3>📊 Categories Distribution</h3>
          <div className="category-chart">
            {Object.entries(stats.categories).map(([category, count]) => (
              <div key={category} className="category-bar">
                <div className="category-info">
                  <span className="category-icon">{getCategoryIcon(category)}</span>
                  <span className="category-name">{category}</span>
                  <span className="category-count">{count}</span>
                </div>
                <div className="bar-container">
                  <div 
                    className="bar-fill"
                    style={{ 
                      width: `${(count / Math.max(...Object.values(stats.categories))) * 100}%`
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="chart-container">
          <h3>🎯 Urgency Distribution</h3>
          <div className="urgency-chart">
            {[1, 2, 3, 4, 5].map(score => (
              <div key={score} className="urgency-item">
                <div className="urgency-info">
                  <span 
                    className="urgency-indicator"
                    style={{ backgroundColor: getUrgencyColor(score) }}
                  />
                  <span className="urgency-label">{getUrgencyLabel(score)}</span>
                  <span className="urgency-count">{stats.urgency_distribution[score.toString()] || 0}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="recent-feedback-section">
        <h3>📝 Recent Feedback</h3>
        <div className="feedback-list">
          {stats.recent_feedback.length === 0 ? (
            <div className="no-feedback">
              <p>No feedback submitted yet</p>
            </div>
          ) : (
            stats.recent_feedback.map(feedback => (
              <div key={feedback.id} className="feedback-item">
                <div className="feedback-header">
                  <div className="feedback-meta">
                    <span className="feedback-id">#{feedback.id}</span>
                    <span className="feedback-date">{formatDate(feedback.created_at)}</span>
                    {feedback.llm_provider && (
                      <span className="feedback-provider">{feedback.llm_provider}</span>
                    )}
                  </div>
                  <div className="feedback-badges">
                    <span className="category-badge">
                      {getCategoryIcon(feedback.category)} {feedback.category}
                    </span>
                    <span 
                      className="urgency-badge"
                      style={{ backgroundColor: getUrgencyColor(feedback.urgency_score) }}
                    >
                      {getUrgencyLabel(feedback.urgency_score)}
                    </span>
                  </div>
                </div>
                <div className="feedback-text">
                  "{feedback.feedback_text}"
                </div>
                <div className="feedback-stats">
                  {feedback.confidence_score && (
                    <span className="confidence">
                      Confidence: {(feedback.confidence_score * 100).toFixed(1)}%
                    </span>
                  )}
                  {feedback.processing_time && (
                    <span className="processing-time">
                      {feedback.processing_time.toFixed(2)}s
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
