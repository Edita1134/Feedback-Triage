from abc import ABC, abstractmethod
from typing import Dict, Any
import json
import httpx
import os
from models.feedback import LLMResponse, FeedbackCategory, UrgencyScore


class LLMProvider(ABC):
    @abstractmethod
    async def analyze_feedback(self, text: str) -> LLMResponse:
        pass
    
    @abstractmethod
    async def analyze_feedback_with_category(self, text: str, category: str) -> LLMResponse:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        
    def _create_prompt(self, text: str) -> str:
        return f"""
You are a feedback analysis agent. Your job is to analyze user feedback and classify it into categories and urgency levels.

CATEGORIES:
1. Bug Report: Identifies a technical issue or something that is broken
2. Feature Request: Suggests a new feature or enhancement
3. Praise/Positive Feedback: Expresses satisfaction or appreciation
4. General Inquiry: Questions or comments that don't fit other categories

URGENCY SCALE (1-5):
1: Not Urgent - Minor issues, general questions, positive feedback
2: Low - Small improvements, non-critical issues
3: Medium - Moderate impact, affects some users
4: High - Significant impact, affects many users, time-sensitive
5: Critical - Severe issues, blocks core functionality, urgent business need

EXAMPLES FOR REFERENCE:

Example 1:
Feedback: "I can't log in to my account, the password reset link is broken. I need to access my files urgently for a client meeting!"
Analysis: {{
  "category": "Bug Report",
  "urgency_score": 4,
  "reasoning": "Login functionality is broken affecting user's ability to work with time pressure",
  "confidence_score": 0.95
}}

Example 2:
Feedback: "Could you add a dark mode feature? It would be great for late-night work sessions."
Analysis: {{
  "category": "Feature Request", 
  "urgency_score": 2,
  "reasoning": "Nice-to-have feature request without urgency",
  "confidence_score": 0.98
}}

Example 3:
Feedback: "The app is amazing! Thank you for all the improvements. The load time is so much faster now."
Analysis: {{
  "category": "Praise/Positive Feedback",
  "urgency_score": 1,
  "reasoning": "Positive feedback expressing satisfaction",
  "confidence_score": 0.99
}}

Example 4:
Feedback: "How do I export my data to CSV? I checked the menu but couldn't find the option."
Analysis: {{
  "category": "General Inquiry",
  "urgency_score": 2,
  "reasoning": "User question about existing functionality",
  "confidence_score": 0.92
}}

Example 5:
Feedback: "URGENT: The app crashes every time I try to save my work. I've lost 3 hours of progress!"
Analysis: {{
  "category": "Bug Report",
  "urgency_score": 5,
  "reasoning": "Critical bug causing data loss with high user frustration",
  "confidence_score": 0.97
}}

Now analyze this feedback and respond with ONLY valid JSON including confidence_score (0-1):

{{
  "category": "one of the four categories above",
  "urgency_score": 1-5,
  "reasoning": "brief explanation of your decision",
  "confidence_score": 0.0-1.0
}}

Feedback to analyze:
{text}
"""

    async def analyze_feedback(self, text: str) -> LLMResponse:
        prompt = self._create_prompt(text)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a feedback analysis agent that returns only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 300
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            try:
                parsed = json.loads(content)
                return LLMResponse(
                    category=FeedbackCategory(parsed["category"]),
                    urgency_score=UrgencyScore(parsed["urgency_score"]),
                    reasoning=parsed.get("reasoning", ""),
                    confidence_score=parsed.get("confidence_score")
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                raise Exception(f"Failed to parse LLM response: {e}")

    async def analyze_feedback_with_category(self, text: str, category: str) -> LLMResponse:
        # For OpenAI provider - analyze only urgency with given category
        prompt = f"""
You are analyzing feedback urgency. The category "{category}" has been manually selected.
Analyze ONLY the urgency level (1-5) for this feedback.

URGENCY (1-5): 1=Not Urgent, 2=Low, 3=Medium, 4=High, 5=Critical

Respond with ONLY valid JSON:
{{
  "category": "{category}",
  "urgency_score": 1-5,
  "reasoning": "brief explanation",
  "confidence_score": 0.0-1.0
}}

Feedback: {text}
"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a feedback analysis agent that returns only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 300
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            try:
                parsed = json.loads(content)
                return LLMResponse(
                    category=FeedbackCategory(category),
                    urgency_score=UrgencyScore(parsed["urgency_score"]),
                    reasoning=parsed.get("reasoning", ""),
                    confidence_score=parsed.get("confidence_score")
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                raise Exception(f"Failed to parse LLM response: {e}")

class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com"
        
    def _create_prompt(self, text: str) -> str:
        return f"""
You are a feedback analysis agent. Analyze user feedback and classify it.

CATEGORIES:
1. Bug Report: Technical issues or broken functionality
2. Feature Request: New features or enhancements
3. Praise/Positive Feedback: Satisfaction or appreciation
4. General Inquiry: Questions or general comments

URGENCY SCALE (1-5):
1: Not Urgent, 2: Low, 3: Medium, 4: High, 5: Critical

EXAMPLES:
- "Login broken, urgent meeting" → Bug Report, urgency 4, confidence 0.95
- "Add dark mode please" → Feature Request, urgency 2, confidence 0.98
- "App is amazing!" → Praise/Positive Feedback, urgency 1, confidence 0.99
- "How to export data?" → General Inquiry, urgency 2, confidence 0.92

Respond with ONLY valid JSON:

{{
  "category": "one of the four categories above",
  "urgency_score": 1-5,
  "reasoning": "brief explanation",
  "confidence_score": 0.0-1.0
}}

Feedback: {text}
"""

    async def analyze_feedback(self, text: str) -> LLMResponse:
        prompt = self._create_prompt(text)
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": 300,
            "temperature": 0.1,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Anthropic API error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result["content"][0]["text"].strip()
            
            try:
                parsed = json.loads(content)
                return LLMResponse(
                    category=FeedbackCategory(parsed["category"]),
                    urgency_score=UrgencyScore(parsed["urgency_score"]),
                    reasoning=parsed.get("reasoning", ""),
                    confidence_score=parsed.get("confidence_score")
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                raise Exception(f"Failed to parse LLM response: {e}")

    async def analyze_feedback_with_category(self, text: str, category: str) -> LLMResponse:
        # For Anthropic provider - analyze only urgency with given category
        prompt = f"""
You are analyzing feedback urgency. The category "{category}" has been manually selected.
Analyze ONLY the urgency level (1-5) for this feedback.

URGENCY (1-5): 1=Not Urgent, 2=Low, 3=Medium, 4=High, 5=Critical

Respond with ONLY valid JSON:
{{
  "category": "{category}",
  "urgency_score": 1-5,
  "reasoning": "brief explanation",
  "confidence_score": 0.0-1.0
}}

Feedback: {text}
"""
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": 300,
            "temperature": 0.1,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Anthropic API error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result["content"][0]["text"].strip()
            
            try:
                parsed = json.loads(content)
                return LLMResponse(
                    category=FeedbackCategory(category),
                    urgency_score=UrgencyScore(parsed["urgency_score"]),
                    reasoning=parsed.get("reasoning", ""),
                    confidence_score=parsed.get("confidence_score")
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                raise Exception(f"Failed to parse LLM response: {e}")

class AzureOpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, endpoint: str, deployment: str, api_version: str = "2024-02-01"):
        self.api_key = api_key
        self.endpoint = endpoint.rstrip('/')
        self.deployment = deployment
        self.api_version = api_version
        
    def _create_prompt(self, text: str) -> str:
        return f"""
You are a feedback analysis agent. Your job is to analyze user feedback and classify it into categories and urgency levels.

CATEGORIES:
1. Bug Report: Identifies a technical issue or something that is broken
2. Feature Request: Suggests a new feature or enhancement
3. Praise/Positive Feedback: Expresses satisfaction or appreciation
4. General Inquiry: Questions or comments that don't fit other categories

URGENCY SCALE (1-5):
1: Not Urgent - Minor issues, general questions, positive feedback
2: Low - Small improvements, non-critical issues
3: Medium - Moderate impact, affects some users
4: High - Significant impact, affects many users, time-sensitive
5: Critical - Severe issues, blocks core functionality, urgent business need

EXAMPLES:
- "Can't login, urgent meeting!" → Bug Report, urgency 4, confidence 0.95
- "Add dark mode feature" → Feature Request, urgency 2, confidence 0.98
- "Love the new interface!" → Praise/Positive Feedback, urgency 1, confidence 0.99

Analyze this feedback and respond with ONLY valid JSON:

{{
  "category": "one of the four categories above",
  "urgency_score": 1-5,
  "reasoning": "brief explanation of your decision",
  "confidence_score": 0.0-1.0
}}

Feedback to analyze:
{text}
"""

    async def analyze_feedback(self, text: str) -> LLMResponse:
        prompt = self._create_prompt(text)
        
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [
                {"role": "system", "content": "You are a feedback analysis agent that returns only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 300
        }
        
        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"Azure OpenAI API error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            try:
                parsed = json.loads(content)
                return LLMResponse(
                    category=FeedbackCategory(parsed["category"]),
                    urgency_score=UrgencyScore(parsed["urgency_score"]),
                    reasoning=parsed.get("reasoning", ""),
                    confidence_score=parsed.get("confidence_score")
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                raise Exception(f"Failed to parse LLM response: {e}")

    async def analyze_feedback_with_category(self, text: str, category: str) -> LLMResponse:
        """Analyze feedback urgency with user-provided category"""
        prompt = f"""
You are a feedback analysis agent. The user has manually selected the category "{category}" for their feedback.
Your job is to analyze ONLY the urgency level (1-5) for this feedback.

URGENCY SCALE (1-5):
1: Not Urgent - Minor issues, general questions, positive feedback
2: Low - Small improvements, non-critical issues
3: Medium - Moderate impact, affects some users
4: High - Significant impact, affects many users, time-sensitive
5: Critical - Severe issues, blocks core functionality, urgent business need

Analyze this feedback and respond with ONLY valid JSON:

{{
  "category": "{category}",
  "urgency_score": 1-5,
  "reasoning": "brief explanation of urgency level",
  "confidence_score": 0.0-1.0
}}

Feedback to analyze:
{text}
"""
        
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [
                {"role": "system", "content": "You are a feedback analysis agent that returns only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 300
        }
        
        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"Azure OpenAI API error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            try:
                parsed = json.loads(content)
                return LLMResponse(
                    category=FeedbackCategory(category),  # Use the user-selected category
                    urgency_score=UrgencyScore(parsed["urgency_score"]),
                    reasoning=parsed.get("reasoning", ""),
                    confidence_score=parsed.get("confidence_score")
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                raise Exception(f"Failed to parse LLM response: {e}")


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "llama3-8b-8192"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"
        
    def _create_prompt(self, text: str) -> str:
        return f"""
You are a feedback analysis agent. Classify user feedback into categories and urgency levels.

CATEGORIES:
1. Bug Report: Technical issues or broken functionality
2. Feature Request: New features or enhancements  
3. Praise/Positive Feedback: Satisfaction or appreciation
4. General Inquiry: Questions or general comments

URGENCY (1-5): 1=Not Urgent, 2=Low, 3=Medium, 4=High, 5=Critical

EXAMPLES:
"Login broken urgently!" → Bug Report, 4, 0.95
"Add dark mode" → Feature Request, 2, 0.98
"Great app!" → Praise/Positive Feedback, 1, 0.99

Respond with ONLY valid JSON:

{{
  "category": "one of the four categories above",
  "urgency_score": 1-5,
  "reasoning": "brief explanation",
  "confidence_score": 0.0-1.0
}}

Feedback: {text}
"""

    async def analyze_feedback(self, text: str) -> LLMResponse:
        prompt = self._create_prompt(text)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a feedback analysis agent that returns only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 300
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Groq API error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            try:
                parsed = json.loads(content)
                return LLMResponse(
                    category=FeedbackCategory(parsed["category"]),
                    urgency_score=UrgencyScore(parsed["urgency_score"]),
                    reasoning=parsed.get("reasoning", ""),
                    confidence_score=parsed.get("confidence_score")
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                raise Exception(f"Failed to parse LLM response: {e}")

    async def analyze_feedback_with_category(self, text: str, category: str) -> LLMResponse:
        # For Groq provider - analyze only urgency with given category
        prompt = f"""
You are analyzing feedback urgency. The category "{category}" has been manually selected.
Analyze ONLY the urgency level (1-5) for this feedback.

URGENCY (1-5): 1=Not Urgent, 2=Low, 3=Medium, 4=High, 5=Critical

Respond with ONLY valid JSON:
{{
  "category": "{category}",
  "urgency_score": 1-5,
  "reasoning": "brief explanation",
  "confidence_score": 0.0-1.0
}}

Feedback: {text}
"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a feedback analysis agent that returns only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 300
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Groq API error: {response.status_code} - {response.text}")
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            try:
                parsed = json.loads(content)
                return LLMResponse(
                    category=FeedbackCategory(category),
                    urgency_score=UrgencyScore(parsed["urgency_score"]),
                    reasoning=parsed.get("reasoning", ""),
                    confidence_score=parsed.get("confidence_score")
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                raise Exception(f"Failed to parse LLM response: {e}")

class LLMService:
    def __init__(self):
        self.provider = self._create_provider()
    
    def _create_provider(self) -> LLMProvider:
        provider_type = os.getenv("DEFAULT_LLM_PROVIDER", "openai").lower()
        
        if provider_type == "openai":
            api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("LLM_API_KEY or OPENAI_API_KEY environment variable is required")
            model = os.getenv("LLM_MODEL", "gpt-4")
            return OpenAIProvider(api_key, model)
            
        elif provider_type == "anthropic":
            api_key = os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("LLM_API_KEY or ANTHROPIC_API_KEY environment variable is required")
            model = os.getenv("LLM_MODEL", "claude-3-sonnet-20240229")
            return AnthropicProvider(api_key, model)
            
        elif provider_type == "azure_openai":
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
            
            if not all([api_key, endpoint, deployment]):
                raise ValueError("AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT environment variables are required")
            
            return AzureOpenAIProvider(api_key, endpoint, deployment, api_version)
            
        elif provider_type == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY environment variable is required")
            model = os.getenv("GROQ_MODEL", "llama3-8b-8192")
            return GroqProvider(api_key, model)
            
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_type}")
    
    async def analyze_feedback(self, text: str) -> LLMResponse:
        return await self.provider.analyze_feedback(text)
    
    async def analyze_feedback_with_category(self, text: str, category: str) -> LLMResponse:
        return await self.provider.analyze_feedback_with_category(text, category)
    
    def get_provider_name(self) -> str:
        """Get the name of the current LLM provider"""
        return self.provider.__class__.__name__.replace("Provider", "").lower()
