"""
Language Detection Service

Detects the language of user input text and produces LANGUAGE entities.
Used to route conversations to appropriate language handlers and track
language preferences in the system.

This service:
- Detects language from text input
- Produces LANGUAGE entities for persistence
- Supports multiple language detection strategies
"""

from typing import Optional, Dict
import re

from global_data import LANGUAGES, DEFAULT_LANGUAGE


class LanguageDetectionService:
    """
    Service for detecting language from text input
    
    Produces LANGUAGE entities that can be linked to CALL and REQUEST
    entities in the system.
    """
    
    def __init__(self):
        """Initialize language detection service"""
        self.supported_languages = set(LANGUAGES.keys())
    
    def detect_language(self, text: str) -> str:
        """
        Detect language from text input
        
        Uses keyword detection and character analysis to determine
        the most likely language.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Language code (e.g., 'en', 'hi', 'gu')
        """
        if not text or not text.strip():
            return DEFAULT_LANGUAGE
        
        text_lower = text.lower()
        
        # Check for language-specific keywords
        language_keywords = {
            'en': ['hello', 'hi', 'yes', 'no', 'please', 'thank', 'order', 'menu'],
            'hi': ['नमस्ते', 'हैं', 'क्या', 'में', 'के', 'है'],
            'gu': ['નમસ્તે', 'છે', 'કેવી', 'માં', 'ના'],
            'mr': ['नमस्कार', 'आहे', 'काय', 'मध्ये', 'चा'],
        }
        
        scores = {lang: 0 for lang in self.supported_languages}
        
        for lang, keywords in language_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[lang] += 1
        
        # Check for Devanagari script (Hindi, Marathi)
        if re.search(r'[\u0900-\u097F]', text):
            scores['hi'] += 3
            scores['mr'] += 2
        
        # Check for Gujarati script
        if re.search(r'[\u0A80-\u0AFF]', text):
            scores['gu'] += 3
        
        # Return language with highest score, default to English
        detected = max(scores.items(), key=lambda x: x[1])
        return detected[0] if detected[1] > 0 else DEFAULT_LANGUAGE
    
    def get_language_entity(self, text: str) -> Dict[str, str]:
        """
        Produce LANGUAGE entity from text
        
        Returns a dictionary representing a LANGUAGE entity that can
        be persisted and linked to CALL/REQUEST entities.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary with language code and name
        """
        lang_code = self.detect_language(text)
        return {
            'code': lang_code,
            'name': LANGUAGES.get(lang_code, 'Unknown'),
            'confidence': 'high' if lang_code != DEFAULT_LANGUAGE else 'medium'
        }

