from pydantic import BaseModel
from typing import List, Dict
import re

class GuardrailConfig(BaseModel):

    max_question_length: int = 2000
    allowed_domains: List[str] = ["mathematics", "math", "calculus", "algebra", "geometry", "statistics", "trigonometry"]
    blocked_keywords: List[str] = ["essay", "homework answers", "cheat", "assignment solution"]
    
    pii_patterns: Dict[str, str] = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "student_id": r'\b(?:student|id|roll)[\s#:]*\d{6,}\b'
    }
    
    min_confidence_threshold: float = 0.7
    max_response_length: int = 5000
    require_citations_for_web: bool = True

GUARDRAIL_CONFIG = GuardrailConfig()
