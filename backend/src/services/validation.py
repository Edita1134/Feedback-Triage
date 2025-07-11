"""
Enhanced input validation service
"""
import re
from typing import List, Dict, Any
from pydantic import validator
import html


class InputValidator:
    """Enhanced input validation with security and quality checks"""
    
    # Patterns for common attacks
    SQL_INJECTION_PATTERNS = [
        r"(union\s+select|drop\s+table|delete\s+from|insert\s+into)",
        r"(or\s+1\s*=\s*1|and\s+1\s*=\s*1)",
        r"(exec\s*\(|execute\s*\()",
        r"(script\s*>|javascript:|vbscript:)"
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"eval\s*\(",
        r"alert\s*\("
    ]
    
    # Spam/abuse patterns
    SPAM_PATTERNS = [
        r"(free\s+money|click\s+here|buy\s+now)",
        r"(viagra|cialis|casino|poker)",
        r"(\$\$\$|\!{3,}|\.{10,})",
        r"(win\s+\$|make\s+money\s+fast)"
    ]
    
    def __init__(self):
        self.min_length = 10
        self.max_length = 1000
        self.max_repeated_chars = 10
        self.max_caps_percentage = 70
    
    def validate_feedback_text(self, text: str) -> Dict[str, Any]:
        """
        Comprehensive validation of feedback text
        Returns validation result with any issues found
        """
        if not text or not text.strip():
            return {
                "valid": False,
                "errors": ["Feedback text cannot be empty"],
                "warnings": [],
                "cleaned_text": ""
            }
        
        # Clean and normalize text
        cleaned_text = self._clean_text(text)
        
        errors = []
        warnings = []
        
        # Length validation
        if len(cleaned_text) < self.min_length:
            errors.append(f"Feedback must be at least {self.min_length} characters long")
        
        if len(cleaned_text) > self.max_length:
            errors.append(f"Feedback must not exceed {self.max_length} characters")
        
        # Security validation
        security_issues = self._check_security(cleaned_text)
        if security_issues:
            errors.extend(security_issues)
        
        # Quality validation
        quality_issues = self._check_quality(cleaned_text)
        warnings.extend(quality_issues)
        
        # Content validation
        content_issues = self._check_content(cleaned_text)
        warnings.extend(content_issues)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "cleaned_text": cleaned_text,
            "original_length": len(text),
            "cleaned_length": len(cleaned_text)
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text input"""
        # HTML decode
        text = html.unescape(text)
        
        # Remove HTML tags (basic)
        text = re.sub(r'<[^>]+>', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        # Remove null bytes and other control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        return text
    
    def _check_security(self, text: str) -> List[str]:
        """Check for potential security issues"""
        issues = []
        text_lower = text.lower()
        
        # Check for SQL injection patterns
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                issues.append("Text contains potentially malicious SQL patterns")
                break
        
        # Check for XSS patterns
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                issues.append("Text contains potentially malicious script content")
                break
        
        # Check for excessive special characters (potential injection)
        special_char_ratio = len(re.findall(r'[<>"\';\\]', text)) / len(text) if text else 0
        if special_char_ratio > 0.1:  # More than 10% special chars
            issues.append("Text contains excessive special characters")
        
        return issues
    
    def _check_quality(self, text: str) -> List[str]:
        """Check text quality and provide warnings"""
        warnings = []
        
        # Check for excessive repeated characters
        repeated_chars = re.findall(r'(.)\1{' + str(self.max_repeated_chars) + ',}', text)
        if repeated_chars:
            warnings.append(f"Text contains excessive repeated characters: {''.join(set(repeated_chars))}")
        
        # Check for excessive capitalization
        caps_count = sum(1 for c in text if c.isupper())
        caps_percentage = (caps_count / len(text)) * 100 if text else 0
        if caps_percentage > self.max_caps_percentage:
            warnings.append(f"Text contains excessive capitalization ({caps_percentage:.1f}%)")
        
        # Check for very short words (potential spam)
        words = text.split()
        if len(words) > 5:  # Only check if sufficient words
            short_words = [w for w in words if len(w) <= 2]
            if len(short_words) / len(words) > 0.5:
                warnings.append("Text contains many very short words")
        
        # Check for lack of punctuation (potential spam)
        has_punctuation = bool(re.search(r'[.!?,:;]', text))
        if len(text) > 50 and not has_punctuation:
            warnings.append("Long text without punctuation may be unclear")
        
        return warnings
    
    def _check_content(self, text: str) -> List[str]:
        """Check content for spam or inappropriate patterns"""
        warnings = []
        text_lower = text.lower()
        
        # Check for spam patterns
        spam_matches = 0
        for pattern in self.SPAM_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                spam_matches += 1
        
        if spam_matches >= 2:
            warnings.append("Text may contain spam-like content")
        
        # Check for excessive URLs
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, text)
        if len(urls) > 2:
            warnings.append("Text contains multiple URLs")
        
        # Check for email addresses (potential spam)
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if len(emails) > 1:
            warnings.append("Text contains multiple email addresses")
        
        return warnings
    
    def get_text_stats(self, text: str) -> Dict[str, Any]:
        """Get statistics about the text"""
        if not text:
            return {"word_count": 0, "char_count": 0, "sentence_count": 0}
        
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        
        return {
            "word_count": len(words),
            "char_count": len(text),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "avg_word_length": sum(len(word) for word in words) / len(words) if words else 0,
            "caps_percentage": (sum(1 for c in text if c.isupper()) / len(text)) * 100 if text else 0
        }


# Global validator instance
input_validator = InputValidator()
