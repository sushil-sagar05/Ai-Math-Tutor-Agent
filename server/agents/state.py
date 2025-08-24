from typing import TypedDict, Annotated, List, Dict, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages 
class MathAgentState(TypedDict):
    """Comprehensive state for the Math Agent workflow"""

    messages: Annotated[List[BaseMessage], add_messages]  
    question: str
    original_question: str
    
    route_decision: str 
    confidence_threshold: float

    kb_results: List[Dict]
    kb_confidence: float
    kb_solution: Dict

    web_results: Dict
    web_sources: List[Dict]
    web_confidence: float
    

    solution_steps: List[Dict]
    final_answer: str
    solution_method: str
    confidence_score: float
    

    human_feedback: Dict
    feedback_required: bool
    correction_applied: bool
    

    iteration_count: int
    max_iterations: int
    retry_count: int
    

    errors: List[str]
    fallback_used: bool
    

    processing_time: float
    sources: List[Dict]
    topic: str
    difficulty: str
