import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from src.services.llm_service import (
    LLMService, 
    OpenAIProvider, 
    AnthropicProvider, 
    AzureOpenAIProvider,
    GroqProvider
)
from src.models.feedback import FeedbackCategory, UrgencyScore, LLMResponse

class TestLLMService:
    
    def test_init_with_openai_provider(self):
        """Test LLMService initialization with OpenAI provider"""
        with patch.dict('os.environ', {
            'DEFAULT_LLM_PROVIDER': 'openai',
            'LLM_API_KEY': 'test-key'
        }):
            service = LLMService()
            assert isinstance(service.provider, OpenAIProvider)
    
    def test_init_with_anthropic_provider(self):
        """Test LLMService initialization with Anthropic provider"""
        with patch.dict('os.environ', {
            'DEFAULT_LLM_PROVIDER': 'anthropic',
            'LLM_API_KEY': 'test-key'
        }):
            service = LLMService()
            assert isinstance(service.provider, AnthropicProvider)
    
    def test_init_without_api_key(self):
        """Test LLMService initialization without API key"""
        with patch.dict('os.environ', {
            'DEFAULT_LLM_PROVIDER': 'openai'
        }, clear=True):
            with pytest.raises(ValueError, match="LLM_API_KEY or OPENAI_API_KEY environment variable is required"):
                LLMService()
    
    def test_init_with_unsupported_provider(self):
        """Test LLMService initialization with unsupported provider"""
        with patch.dict('os.environ', {
            'DEFAULT_LLM_PROVIDER': 'unsupported',
            'LLM_API_KEY': 'test-key'
        }):
            with pytest.raises(ValueError, match="Unsupported LLM provider"):
                LLMService()

class TestOpenAIProvider:
    
    def test_create_prompt(self):
        """Test prompt creation"""
        provider = OpenAIProvider("test-key")
        prompt = provider._create_prompt("Test feedback")
        assert "Test feedback" in prompt
        assert "Bug Report" in prompt
        assert "urgency_score" in prompt
    
    @pytest.mark.asyncio
    async def test_analyze_feedback_success(self):
        """Test successful feedback analysis"""
        provider = OpenAIProvider("test-key")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"category": "Bug Report", "urgency_score": 4, "reasoning": "Login issue"}'
                }
            }]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await provider.analyze_feedback("I can't log in")
            
            assert result.category == FeedbackCategory.BUG_REPORT
            assert result.urgency_score == UrgencyScore.HIGH
            assert result.reasoning == "Login issue"
    
    @pytest.mark.asyncio
    async def test_analyze_feedback_api_error(self):
        """Test API error handling"""
        provider = OpenAIProvider("test-key")
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            with pytest.raises(Exception, match="OpenAI API error"):
                await provider.analyze_feedback("Test feedback")

class TestAnthropicProvider:
    
    def test_create_prompt(self):
        """Test prompt creation"""
        provider = AnthropicProvider("test-key")
        prompt = provider._create_prompt("Test feedback")
        assert "Test feedback" in prompt
        assert "Bug Report" in prompt
        assert "urgency_score" in prompt
    
    @pytest.mark.asyncio
    async def test_analyze_feedback_success(self):
        """Test successful feedback analysis"""
        provider = AnthropicProvider("test-key")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{
                "text": '{"category": "Feature Request", "urgency_score": 2, "reasoning": "Enhancement request"}'
            }]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await provider.analyze_feedback("Add dark mode please")
            
            assert result.category == FeedbackCategory.FEATURE_REQUEST
            assert result.urgency_score == UrgencyScore.LOW
            assert result.reasoning == "Enhancement request"


class TestAzureOpenAIProvider:
    
    def test_create_prompt(self):
        """Test prompt creation"""
        provider = AzureOpenAIProvider(
            "test-key", 
            "https://test.cognitiveservices.azure.com", 
            "gpt-4o"
        )
        prompt = provider._create_prompt("Test feedback")
        assert "Test feedback" in prompt
        assert "Bug Report" in prompt
        assert "urgency_score" in prompt
    
    @pytest.mark.asyncio
    async def test_analyze_feedback_success(self):
        """Test successful feedback analysis"""
        provider = AzureOpenAIProvider(
            "test-key", 
            "https://test.cognitiveservices.azure.com", 
            "gpt-4o"
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"category": "Bug Report", "urgency_score": 5, "reasoning": "Critical login issue"}'
                }
            }]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await provider.analyze_feedback("System is down!")
            
            assert result.category == FeedbackCategory.BUG_REPORT
            assert result.urgency_score == UrgencyScore.CRITICAL
            assert result.reasoning == "Critical login issue"


class TestGroqProvider:
    
    def test_create_prompt(self):
        """Test prompt creation"""
        provider = GroqProvider("test-key", "llama3-8b-8192")
        prompt = provider._create_prompt("Test feedback")
        assert "Test feedback" in prompt
        assert "Bug Report" in prompt
        assert "urgency_score" in prompt
    
    @pytest.mark.asyncio
    async def test_analyze_feedback_success(self):
        """Test successful feedback analysis"""
        provider = GroqProvider("test-key", "llama3-8b-8192")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"category": "Praise/Positive Feedback", "urgency_score": 1, "reasoning": "Positive user feedback"}'
                }
            }]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await provider.analyze_feedback("Great app, love using it!")
            
            assert result.category == FeedbackCategory.PRAISE_POSITIVE_FEEDBACK
            assert result.urgency_score == UrgencyScore.NOT_URGENT
            assert result.reasoning == "Positive user feedback"


class TestLLMServiceWithNewProviders:
    
    def test_init_with_azure_openai_provider(self):
        """Test LLMService initialization with Azure OpenAI provider"""
        with patch.dict('os.environ', {
            'DEFAULT_LLM_PROVIDER': 'azure_openai',
            'AZURE_OPENAI_API_KEY': 'test-key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.cognitiveservices.azure.com',
            'AZURE_OPENAI_DEPLOYMENT': 'gpt-4o'
        }):
            service = LLMService()
            assert isinstance(service.provider, AzureOpenAIProvider)
    
    def test_init_with_groq_provider(self):
        """Test LLMService initialization with Groq provider"""
        with patch.dict('os.environ', {
            'DEFAULT_LLM_PROVIDER': 'groq',
            'GROQ_API_KEY': 'test-key'
        }):
            service = LLMService()
            assert isinstance(service.provider, GroqProvider)
    
    def test_init_with_missing_azure_config(self):
        """Test LLMService initialization with missing Azure config"""
        with patch.dict('os.environ', {
            'DEFAULT_LLM_PROVIDER': 'azure_openai'
        }, clear=True):
            with pytest.raises(ValueError, match="AZURE_OPENAI_API_KEY"):
                LLMService()
    
    def test_init_with_missing_groq_config(self):
        """Test LLMService initialization with missing Groq config"""
        with patch.dict('os.environ', {
            'DEFAULT_LLM_PROVIDER': 'groq'
        }, clear=True):
            with pytest.raises(ValueError, match="GROQ_API_KEY"):
                LLMService()
