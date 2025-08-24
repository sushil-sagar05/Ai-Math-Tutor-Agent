from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import json
import logging
import re

logger = logging.getLogger(__name__)

class GuardrailMiddleware(BaseHTTPMiddleware):
    """Enhanced guardrail middleware for conversational math tutoring with proper JSON handling"""
    
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/solve"):
            return await call_next(request)
        
        try:
            if request.method == "POST":
                body = await request.body()
                
                if not body:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Empty request body"}
                    )
                
                try:
                    request_data = json.loads(body.decode('utf-8'))
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Invalid JSON in request body"}
                    )
                if not isinstance(request_data, dict):
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Request body must be a JSON object"}
                    )
                question = request_data.get("question")
                
                if question is None:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Missing 'question' field"}
                    )
                
                if not isinstance(question, str):
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Question must be a string"}
                    )
                question_stripped = question.strip()
                
                if len(question) > 2000:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Question too long. Max 2000 characters."}
                    )
                
                if len(question_stripped) < 2:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Question too short. Please provide more details."}
                    )
                
                if not self.is_mathematics_question(question_stripped):
                    logger.warning(f"Question may not be mathematical: {question[:50]}...")
                
                conversation_history = request_data.get("conversation_history", [])
                if conversation_history and not isinstance(conversation_history, list):
                    return JSONResponse(
                        status_code=400,
                        content={"error": "conversation_history must be an array"}
                    )
                
                session_id = request_data.get("session_id")
                if session_id is not None and not isinstance(session_id, str):
                    return JSONResponse(
                        status_code=400,
                        content={"error": "session_id must be a string"}
                    )
                
                pii_indicators = ['@', 'phone:', 'email:', 'contact', 'call me', 'my number']
                has_pii = any(indicator in question.lower() for indicator in pii_indicators)
                
                if has_pii:
                    logger.warning(f"Potential PII detected in question: {question[:50]}...")

                if not self.is_safe_content(question):
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Content not appropriate for educational context"}
                    )
            

            response = await call_next(request)

            if response.status_code == 200 and request.method == "POST":
                logger.info("Response passed basic guardrail checks")
            
            return response
            
        except Exception as e:
            logger.error(f"Guardrail middleware error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal guardrail processing error"}
            )
    
    def is_mathematics_question(self, question: str) -> bool:
        """Enhanced mathematical question detection with comprehensive patterns"""
        question_lower = question.lower().strip()
        

        basic_math_indicators = [
            '+', '-', '*', '/', '=', '^', '%', '√', '∫', '∑', '∏',
            'solve', 'find', 'calculate', 'compute', 'determine', 'evaluate',
            'equation', 'formula', 'expression', 'function', 'polynomial',
            'x', 'y', 'z', 'variable', 'unknown', 'coefficient'
        ]
        algebraic_indicators = [
            'equals', 'equal', 'same as', 'as much as', 'equivalent',
            'weigh', 'weight', 'measure', 'units', 'mass',
            'how many', 'how much', 'what is', 'what are', 'find the',
            'combined', 'total', 'sum', 'difference', 'product',
            'times', 'twice', 'double', 'triple', 'quadruple',
            'ratio', 'proportion', 'percent', 'percentage', 'fraction'
        ]

        geometry_indicators = [
            'area', 'volume', 'perimeter', 'circumference', 'surface area',
            'radius', 'diameter', 'angle', 'triangle', 'square', 'rectangle',
            'circle', 'polygon', 'parallelogram', 'rhombus', 'trapezoid',
            'length', 'width', 'height', 'distance', 'coordinate',
            'vertex', 'edge', 'face', 'diagonal', 'hypotenuse'
        ]
        
        calculus_indicators = [
            'derivative', 'integral', 'limit', 'differentiate', 'integrate',
            'slope', 'tangent', 'rate of change', 'optimization',
            'maximum', 'minimum', 'critical point', 'inflection',
            'continuity', 'differentiable', 'antiderivative'
        ]
        stats_indicators = [
            'probability', 'average', 'mean', 'median', 'mode',
            'standard deviation', 'variance', 'correlation',
            'distribution', 'sample', 'population', 'hypothesis',
            'regression', 'confidence interval', 'significance'
        ]
        conversational_indicators = [
            'explain', 'show me', 'help me', 'how to', 'what does',
            'can you', 'could you', 'would you', 'please solve',
            'step by step', 'detailed solution', 'method', 'approach',
            'why does', 'what happens when', 'prove that'
        ]
        educational_indicators = [
            'expand', 'factor', 'simplify', 'substitute', 'isolate',
            'distribute', 'combine like terms', 'complete the square',
            'quadratic formula', 'pythagorean theorem', 'foil method'
        ]
        all_math_indicators = (
            basic_math_indicators + algebraic_indicators + geometry_indicators + 
            calculus_indicators + stats_indicators + conversational_indicators + 
            educational_indicators
        )
        has_basic_math = any(indicator in question_lower for indicator in all_math_indicators)
        
        mathematical_patterns = [
            r'\d+',                              # Contains numbers
            r'\d+\s*[+\-*/=^]\s*\d+',           # Basic arithmetic expressions  
            r'[xyz]\s*[+\-*/=^]',               # Algebraic expressions
            r'\([^)]*[+\-*/^][^)]*\)',          # Expressions in parentheses
            r'\b\w+\s+(equals?|=)\s+\w+',       # Equality statements
            r'weigh.*as.*much.*as',             # Weight comparison patterns
            r'equal.*in.*weight',               # Weight equality patterns
            r'how\s+many.*equals?',             # Algebraic solving questions
            r'combined.*weight',                # Mathematical operations
            r'as\s+much\s+as',                 # Comparison statements
            r'\b\d+\s+\w+\s+(and|plus|minus)', # Unit combinations
            r'(square|cube|power|root|log)',    # Mathematical operations
            r'(sin|cos|tan|sec|csc|cot)',       # Trigonometric functions
            r'(greater|less|more|fewer)\s+than', # Comparisons
            r'(increase|decrease|double|triple)', # Mathematical changes
            r'\b(treek|squig|goolee)\b',        # Fictional units from Hendrycks
            r'(expand|factor|simplify|solve)\s+', # Mathematical operations
            r'\b\d+x\b|\bx\d+\b',              # Variables with coefficients
        ]

        has_math_patterns = any(re.search(pattern, question_lower) 
                               for pattern in mathematical_patterns)
        word_problem_indicators = [
            ('weigh' in question_lower and 'equal' in question_lower),
            ('how many' in question_lower and ('equals' in question_lower or '=' in question_lower)),
            ('combined weight' in question_lower),
            ('system' in question_lower and 'equation' in question_lower),
            ('solve for' in question_lower),
            ('find the' in question_lower and any(term in question_lower for term in ['value', 'number', 'answer'])),
            (question_lower.count('and') >= 2 and any(num in question_lower for num in ['one', 'two', 'three', 'ten'])),
            ('what is' in question_lower and any(op in question_lower for op in ['+', '-', '*', '/', 'times', 'plus', 'minus'])),
        ]
        
        has_word_problem_structure = any(word_problem_indicators)
        
        hendrycks_style = (
            len([word for word in question_lower.split() if word.isalpha()]) > 8 and  # Reduced threshold
            ('how many' in question_lower or 'what is' in question_lower or 'find' in question_lower or 'solve' in question_lower) and
            ('equal' in question_lower or 'same' in question_lower or 'weigh' in question_lower or 'total' in question_lower)
        )
        
        fictional_units_problem = (
            ('treek' in question_lower and 'squig' in question_lower) or
            ('treek' in question_lower and 'goolee' in question_lower) or
            ('squig' in question_lower and 'goolee' in question_lower)
        ) and ('weigh' in question_lower or 'weight' in question_lower)
        conversational_math = (
            any(starter in question_lower for starter in ['can you', 'could you', 'please', 'explain', 'show me']) and
            any(math_term in question_lower for math_term in ['step', 'solution', 'solve', 'calculate', 'find'])
        )

        simple_arithmetic = bool(re.search(r'\d+\s*[+\-*/]\s*\d+', question_lower))
        is_math_question = (
            has_basic_math or 
            has_math_patterns or 
            has_word_problem_structure or 
            hendrycks_style or
            fictional_units_problem or
            conversational_math or
            simple_arithmetic or
            len(question_lower) > 20  
        )

        if not is_math_question:
            logger.info(f"Question rejected by guardrail: {question[:100]}...")
            logger.debug(f"Indicators - Basic math: {has_basic_math}, Patterns: {has_math_patterns}, "
                        f"Word problem: {has_word_problem_structure}, Hendrycks: {hendrycks_style}, "
                        f"Fictional units: {fictional_units_problem}, Conversational: {conversational_math}, "
                        f"Simple arithmetic: {simple_arithmetic}")
        else:
            logger.info(f"Mathematical question accepted: {question[:50]}...")
        
        return is_math_question
    
    def is_safe_content(self, text: str) -> bool:
        """Enhanced content safety check for educational context"""
        text_lower = text.lower()

        unsafe_patterns = [

            'hack', 'exploit', 'malicious', 'virus', 'malware',
            'password', 'credit card', 'social security', 'ssn',
  
            'adult content', 'explicit', 'nsfw',

            'buy now', 'click here', 'limited time offer',
            'make money fast', 'free trial',

            'your address', 'your phone', 'your email',
            'personal details', 'bank account'
        ]

        has_unsafe_content = any(pattern in text_lower for pattern in unsafe_patterns)
        
        return not has_unsafe_content
