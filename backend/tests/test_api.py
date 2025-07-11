import pytest
import json
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from src.main import app
from src.models.feedback import FeedbackCategory, UrgencyScore, LLMResponse
from src.services.llm_service import LLMService

client = TestClient(app)

class TestTriageAPI:
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "feedback-triage-api"}
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_triage_success(self, monkeypatch):
        """Test successful feedback triage"""
        # Mock LLM service
        mock_analysis = LLMResponse(
            category=FeedbackCategory.BUG_REPORT,
            urgency_score=UrgencyScore.HIGH,
            reasoning="Login issues are critical"
        )
        
        async def mock_analyze(text):
            return mock_analysis
        
        monkeypatch.setattr(LLMService, "analyze_feedback", mock_analyze)
        
        response = client.post("/api/triage", json={
            "text": "I can't log in to my account!"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "Bug Report"
        assert data["urgency_score"] == 4
        assert data["feedback_text"] == "I can't log in to my account!"
    
    def test_triage_empty_text(self):
        """Test triage with empty text"""
        response = client.post("/api/triage", json={
            "text": ""
        })
        assert response.status_code == 422
    
    def test_triage_long_text(self):
        """Test triage with text exceeding max length"""
        long_text = "a" * 1001  # Exceeds 1000 character limit
        response = client.post("/api/triage", json={
            "text": long_text
        })
        assert response.status_code == 422
    
    def test_triage_missing_text(self):
        """Test triage with missing text field"""
        response = client.post("/api/triage", json={})
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_triage_llm_error(self, monkeypatch):
        """Test triage with LLM service error"""
        async def mock_analyze_error(text):
            raise Exception("API error: 500")
        
        monkeypatch.setattr(LLMService, "analyze_feedback", mock_analyze_error)
        
        response = client.post("/api/triage", json={
            "text": "Test feedback"
        })
        
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"]
