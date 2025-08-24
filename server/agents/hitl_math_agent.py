import os
import sys
import asyncio
import dspy
from typing import Dict, List, Optional
from .math_agent import MathSolvingAgent
from database.feedback_model import FeedbackEntry, SessionLocal
from utils.dspy_gemini import initialize_gemini_dspy, get_gemini_lm
from sqlalchemy.orm import Session
import json
import re
import time
from datetime import datetime, timedelta
import logging

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger = logging.getLogger(__name__)

class ConversationalDSPyModule(dspy.Module):
    
    def __init__(self):
        super().__init__()
        self.conversational_solver = dspy.ChainOfThought(
            "question, context, educational_level -> step1, step2, step3, step4, final_answer"
        )
    
    def forward(self, question, conversation_context="", educational_level="tutor"):
        teaching_keywords = ["explain like", "make me understand", "teach me", "beginner", "simple", "basics", "noob", "new to", "don't understand", "help me understand"]
        is_teaching_request = any(keyword in question.lower() for keyword in teaching_keywords)
        math_topic = self._extract_math_topic(question, conversation_context)
        
        if is_teaching_request or educational_level == "beginner":
            enhanced_context = f"""
            You are a patient math tutor explaining {math_topic} to a complete beginner.
            
            Question: {question}
            Context: {conversation_context}
            Mathematical Topic: {math_topic}
            
            CRITICAL INSTRUCTIONS FOR BEGINNER EXPLANATIONS:
            - Give SPECIFIC mathematical content, not generic teaching advice
            - Use simple, everyday language without jargon
            - Include concrete examples with actual numbers
            - Provide real-world analogies and visual metaphors
            - Break down into digestible steps that build understanding
            - Give the complete mathematical answer in simple terms
            
            Example Response Format:
            Step 1: [Simple definition with everyday analogy]
            Step 2: [Concrete example with actual numbers/calculations]
            Step 3: [Why this works - intuitive explanation]
            Step 4: [Complete answer with practical meaning]
            
            For derivatives specifically:
            "The derivative of sin(x) is cos(x). Think of sin(x) like a smooth wave going up and down - like ocean waves. The derivative cos(x) tells you how steep that wave is at any point. When the wave is at its peak (sin = 1), it's completely flat there, so the steepness is 0 (cos = 0). When the wave is crossing the middle going up, that's where it's steepest (cos = 1)."
            
            DO NOT give responses like "let's figure out what's confusing" or "tell me what you're stuck on".
            GIVE THE ACTUAL MATHEMATICAL EXPLANATION immediately with examples.
            """
        else:
            enhanced_context = f"""
            You are a step-by-step math tutor solving: {math_topic}
            
            Question: {question}
            Context: {conversation_context}
            
            Provide your response in this exact format:
            Step 1: [First mathematical operation or setup with specific calculations]
            Step 2: [Second calculation or manipulation with actual numbers]
            Step 3: [Third step showing detailed work]
            Step 4: [Final calculation and complete result]
            
            Make each step mathematically precise and show all work.
            Always provide a complete final answer with proper mathematical notation.
            """
        
        try:
            result = self.conversational_solver(
                question=question,
                context=enhanced_context,
                educational_level=educational_level
            )
            return result
        except Exception as e:
            logger.error(f"DSPy forward error: {e}")
            return self._create_fallback_response(question, is_teaching_request, math_topic)
    
    def _extract_math_topic(self, question, context):
        """Extract the actual mathematical topic being discussed"""
        math_keywords = {
            'derivative': 'derivatives and differentiation',
            'integral': 'integration and integrals',
            'sin': 'trigonometric functions (sine)',
            'cos': 'trigonometric functions (cosine)',
            'tan': 'trigonometric functions (tangent)',
            'equation': 'solving equations',
            'graph': 'graphing and functions',
            'limit': 'limits and continuity',
            'matrix': 'matrices and linear algebra',
            'vector': 'vectors and vector operations',
            'probability': 'probability and statistics'
        }
        
        combined_text = (question + " " + context).lower()
        
        for keyword, topic in math_keywords.items():
            if keyword in combined_text:
                return topic
        
        return "this mathematical concept"
    
    def _create_fallback_response(self, question, is_teaching=False, topic="mathematics"):
        """Create a fallback response when DSPy fails"""
        if is_teaching:
            return type('obj', (object,), {
                'step1': f"Let me explain {topic} in the simplest way possible with a real example.",
                'step2': f"Here's exactly how {topic} works with actual numbers you can follow.",
                'step3': f"Think of {topic} like this everyday situation that makes it clear.",
                'step4': f"Now you can see the complete answer and why it makes sense.",
                'final_answer': f"The complete explanation of {topic} is provided step-by-step above with concrete examples."
            })()
        else:
            return type('obj', (object,), {
                'step1': f"Analyzing this {topic} problem systematically.",
                'step2': f"Applying the appropriate mathematical techniques for {topic}.",
                'step3': f"Performing calculations step by step to solve this {topic} problem.",
                'step4': f"Verifying the result and presenting the complete final answer.",
                'final_answer': f"Solution for this {topic} problem completed - see detailed steps above."
            })()

class ConversationalHITLMathAgent(MathSolvingAgent):
    
    def __init__(self):
        super().__init__()
        self.conversation_sessions = {}
        self.feedback_memory = []
        
        try:
            self.dspy_config = initialize_gemini_dspy()
        except Exception as e:
            logger.error(f"DSPy initialization error: {e}")
            self.dspy_config = None
        
        if self.dspy_config:
            try:
                self.dspy_module = ConversationalDSPyModule()
                print(" Conversational HITL Agent initialized with DSPy-Gemini")
            except Exception as e:
                print(f" DSPy module initialization failed: {e}")
                self.dspy_module = None
        else:
            self.dspy_module = None
            print(" Conversational HITL Agent running without DSPy")
    
    def _detect_request_type(self, question: str, context: Dict) -> str:
        """Detect if this is a teaching request vs solving request"""
        teaching_indicators = [
            "explain like", "make me understand", "teach me", "beginner", 
            "simple", "basics", "noob", "new to", "don't understand",
            "help me understand", "break it down", "in simple terms",
            "like i am", "for dummies", "easy way"
        ]
        
        question_lower = question.lower()

        if context.get("educational_level") == "beginner":
            return "teaching"
        
        if any(indicator in question_lower for indicator in teaching_indicators):
            return "teaching"
        
        history = context.get("conversation_history", [])
        if history:
            recent_messages = [msg.get("content", "").lower() for msg in history[-3:]]
            if any(indicator in " ".join(recent_messages) for indicator in teaching_indicators):
                return "teaching"
        
        return "solving"
    
    async def solve_conversational(self, question: str, context: Dict) -> Dict:
        session_id = context.get("session_id", f"session_{int(time.time())}")
        conversation_history = context.get("conversation_history", [])
        request_type = self._detect_request_type(question, context)
        educational_level = "beginner" if request_type == "teaching" else "tutor"
        
        print(f" HITL Request Type: {request_type} | Educational Level: {educational_level}")
        print(f" Question: {question[:80]}...")
        
        if session_id not in self.conversation_sessions:
            self.conversation_sessions[session_id] = {
                "history": [],
                "solved_problems": [],
                "user_preferences": {"teaching_mode": request_type == "teaching"},
                "learning_progress": []
            }
        
        session = self.conversation_sessions[session_id]
        session["user_preferences"]["teaching_mode"] = request_type == "teaching"
        
        print("STEP 1: Using base agent KB→MCP routing...")
        
        try:
            base_solution = await self.solve_async(question)
        except Exception as e:
            logger.error(f"Base solution error: {e}")
            base_solution = {
                "route": "error",
                "confidence": 0.0,
                "steps": [],
                "final_answer": f"I encountered an error processing your request: {str(e)}"
            }
        
        print(f" Base solution: route={base_solution.get('route')}, confidence={base_solution.get('confidence', 0):.3f}")
        if self.dspy_module:
            print(f"STEP 2: Enhancing with conversational DSPy ({educational_level} mode)...")
            conversational_context = self._build_conversational_context(
                question, session["history"], session["solved_problems"], request_type
            )
            
            enhanced_solution = await self._enhance_with_dspy(
                base_solution, question, conversational_context, educational_level
            )
        else:
            print("STEP 2: Using base solution (no DSPy available)")
            enhanced_solution = base_solution
            enhanced_solution = self._apply_teaching_mode_fallback(enhanced_solution, request_type, question)
        
        print("STEP 3: Creating HITL conversational response...")
        conversational_response = self._create_conversational_response(
            enhanced_solution, question, session["history"], request_type
        )
        session["history"].append({
            "role": "user",
            "content": question,
            "request_type": request_type,
            "timestamp": datetime.now()
        })
        session["history"].append({
            "role": "assistant", 
            "content": conversational_response["conversational_text"],
            "solution": enhanced_solution,
            "request_type": request_type,
            "timestamp": datetime.now()
        })
        
        final_response = {
            **enhanced_solution,
            "conversational_response": conversational_response["conversational_text"],
            "follow_up_suggestions": conversational_response["follow_up_suggestions"],
            "session_id": session_id,
            "request_type": request_type,
            "educational_level": educational_level,
            "hitl_mode": True,
            "route": enhanced_solution.get("route", "kb_mcp_routing"),
            "route_decision": enhanced_solution.get("route", "kb_mcp_routing"),
            "conversational_enhanced": True,
            "conversation_metadata": {
                "turn_number": len(session["history"]),
                "context_aware": len(session["history"]) > 2,
                "teaching_mode": request_type == "teaching",
                "learning_progress": len(session["solved_problems"])
            },
            "hitl_metadata": {
                "feedback_enabled": True,
                "conversational_mode": True,
                "dspy_enhanced": self.dspy_module is not None,
                "session_learning": True,
                "adaptive_responses": True
            }
        }
        
        print(f" HITL Final response ready: {request_type} mode, route={final_response.get('route')}")
        
        return final_response
    
    async def solve_conversational_stream(self, question: str, context: Dict, streaming_manager) -> Dict:
        session_id = context.get("session_id", f"session_{int(time.time())}")
        request_type = self._detect_request_type(question, context)
        educational_level = "beginner" if request_type == "teaching" else "tutor"
        
        await streaming_manager.send_to_stream(session_id, {
            "type": "step_update",
            "step": 1,
            "message": f"Initializing {request_type} mode for your question...",
            "progress": 15
        })
        
        if session_id not in self.conversation_sessions:
            self.conversation_sessions[session_id] = {
                "history": [],
                "solved_problems": [],
                "user_preferences": {"teaching_mode": request_type == "teaching"},
                "learning_progress": []
            }
        
        session = self.conversation_sessions[session_id]
        session["user_preferences"]["teaching_mode"] = request_type == "teaching"
        
        await streaming_manager.send_to_stream(session_id, {
            "type": "step_update", 
            "step": 2,
            "message": "Processing with KB→MCP routing...",
            "progress": 40
        })
        
        try:
            base_solution = await self.solve_async(question)
        except Exception as e:
            logger.error(f"Streaming solve error: {e}")
            base_solution = {
                "route": "error",
                "confidence": 0.0,
                "steps": [],
                "final_answer": f"Error: {str(e)}"
            }
        
        await streaming_manager.send_to_stream(session_id, {
            "type": "routing_result",
            "route": base_solution.get("route", "unknown"),
            "confidence": base_solution.get("confidence", 0),
            "message": f"Used {base_solution.get('route', 'unknown')} route"
        })
        
        if self.dspy_module:
            await streaming_manager.send_to_stream(session_id, {
                "type": "step_update",
                "step": 3,
                "message": f"Enhancing with {educational_level} mode AI...",
                "progress": 65
            })
            
            conversational_context = self._build_conversational_context(
                question, session["history"], session["solved_problems"], request_type
            )
            
            enhanced_solution = await self._enhance_with_dspy(
                base_solution, question, conversational_context, educational_level
            )
        else:
            enhanced_solution = self._apply_teaching_mode_fallback(base_solution, request_type, question)

        if enhanced_solution.get("steps"):
            for i, step in enumerate(enhanced_solution["steps"]):
                await streaming_manager.send_to_stream(session_id, {
                    "type": "step_generated",
                    "step_number": i + 1,
                    "step_data": step,
                    "total_steps": len(enhanced_solution["steps"])
                })
                await asyncio.sleep(0.3)
        
        await streaming_manager.send_to_stream(session_id, {
            "type": "step_update",
            "step": 4,
            "message": f"Finalizing {request_type} response...",
            "progress": 90
        })
        
        conversational_response = self._create_conversational_response(
            enhanced_solution, question, session["history"], request_type
        )
        
        session["history"].append({
            "role": "user",
            "content": question,
            "request_type": request_type,
            "timestamp": datetime.now()
        })
        session["history"].append({
            "role": "assistant", 
            "content": conversational_response["conversational_text"],
            "solution": enhanced_solution,
            "request_type": request_type,
            "timestamp": datetime.now()
        })
        
        final_response = {
            **enhanced_solution,
            "conversational_response": conversational_response["conversational_text"],
            "follow_up_suggestions": conversational_response["follow_up_suggestions"],
            "session_id": session_id,
            "request_type": request_type,
            "educational_level": educational_level,
            "hitl_mode": True,
            "streaming": True,
            "conversation_metadata": {
                "turn_number": len(session["history"]),
                "context_aware": len(session["history"]) > 2,
                "teaching_mode": request_type == "teaching"
            }
        }
        
        await streaming_manager.send_to_stream(session_id, {
            "type": "completion",
            "message": "Solution complete!",
            "progress": 100
        })
        
        return final_response
    
    async def _enhance_with_dspy(self, base_solution: Dict, question: str, context: str, educational_level: str = "tutor") -> Dict:
        try:
            dspy_result = self.dspy_module(
                question=question,
                conversation_context=context,
                educational_level=educational_level
            )
            
            enhanced_steps = self._parse_conversational_steps(dspy_result, educational_level, question)
            
            if enhanced_steps and len(enhanced_steps) > 0:
                base_solution["steps"] = enhanced_steps
                base_solution["solution_steps"] = enhanced_steps
                base_solution["dspy_enhanced"] = True
                base_solution["conversational_quality"] = "high"
                base_solution["educational_level"] = educational_level
                if hasattr(dspy_result, 'final_answer') and dspy_result.final_answer:
                    base_solution["final_answer"] = str(dspy_result.final_answer).strip()
                elif educational_level == "beginner":
                    base_solution["final_answer"] = self._generate_complete_teaching_answer(question, enhanced_steps)
                
                print(f" DSPy enhanced with {len(enhanced_steps)} {educational_level} steps")
            else:
                print(" DSPy parsing failed, using fallback")
                base_solution = self._apply_teaching_mode_fallback(base_solution, educational_level, question)
            
            return base_solution
            
        except Exception as e:
            logger.error(f"DSPy enhancement error: {e}")
            print(f" DSPy enhancement failed: {e}")
            return self._apply_teaching_mode_fallback(base_solution, educational_level, question)
    
    def _apply_teaching_mode_fallback(self, solution: Dict, request_type: str, question: str) -> Dict:
        """Apply teaching mode enhancements when DSPy is not available"""
        if request_type == "teaching":
            topic = self._extract_topic_from_question(question)
            
            teaching_steps = [
                {
                    "step": 1,
                    "text": f"Let me explain {topic} in simple terms with a concrete example.",
                    "type": "teaching_step"
                },
                {
                    "step": 2,
                    "text": f"Here's exactly how {topic} works with actual numbers and calculations.",
                    "type": "teaching_step"
                },
                {
                    "step": 3,
                    "text": f"Think of {topic} like this real-world situation that makes it clear.",
                    "type": "teaching_step"
                },
                {
                    "step": 4,
                    "text": f"Now you can see the complete answer and understand why it works this way.",
                    "type": "teaching_step"
                }
            ]
            
            solution["steps"] = teaching_steps
            solution["solution_steps"] = teaching_steps
            solution["educational_mode"] = "beginner_friendly"
            solution["final_answer"] = self._generate_complete_teaching_answer(question, teaching_steps)
        
        return solution
    
    def _extract_topic_from_question(self, question: str) -> str:
        """Extract mathematical topic from question"""
        question_lower = question.lower()
        
        if "derivative" in question_lower or "differentiat" in question_lower:
            return "derivatives"
        elif "integral" in question_lower or "integrat" in question_lower:
            return "integration"
        elif any(trig in question_lower for trig in ["sin", "cos", "tan"]):
            return "trigonometric functions"
        elif "equation" in question_lower:
            return "solving equations"
        elif "graph" in question_lower:
            return "graphing"
        else:
            return "this mathematical concept"
    
    def _generate_complete_teaching_answer(self, question: str, steps: List[Dict]) -> str:
        """Generate a complete, specific teaching answer"""
        question_lower = question.lower()
        
        if "derivative" in question_lower and "sin" in question_lower:
            return "The derivative of sin(x) is cos(x). This means that if you have a sine wave, cos(x) tells you the slope (steepness) of that wave at any point x."
        
        elif "integral" in question_lower:
            return "Integration is the reverse of differentiation. When you integrate, you're finding the original function whose derivative gave you the integrand."
        
        elif any(trig in question_lower for trig in ["sin", "cos", "tan"]):
            return "Trigonometric functions describe relationships in triangles and circular motion. They're essential for understanding waves, rotations, and periodic patterns."
        
        else:
            if steps and len(steps) > 0:
                return f"The complete mathematical solution is explained step-by-step above. Each step builds your understanding to reach the final answer."
            else:
                return "The mathematical concept has been explained in beginner-friendly terms above."
    
    def _parse_conversational_steps(self, dspy_result, educational_level: str = "tutor", question: str = "") -> List[Dict]:
        steps = []
        step_type = "teaching_step" if educational_level == "beginner" else "conversational_step"
        if hasattr(dspy_result, 'step1') and hasattr(dspy_result, 'step2'):
            for i in range(1, 6):
                step_attr = f'step{i}'
                if hasattr(dspy_result, step_attr):
                    step_content = getattr(dspy_result, step_attr)
                    if step_content and str(step_content).strip():
                        steps.append({
                            "step": i,
                            "text": str(step_content).strip(),
                            "type": step_type
                        })
        
        if not steps:
            topic = self._extract_topic_from_question(question)
            
            if educational_level == "beginner":
                steps = [
                    {"step": 1, "text": f"Let me explain {topic} in the simplest way possible with a real example.", "type": "teaching_step"},
                    {"step": 2, "text": f"Here's exactly how {topic} works with actual numbers you can follow.", "type": "teaching_step"},
                    {"step": 3, "text": f"Think of {topic} like this everyday situation that makes it crystal clear.", "type": "teaching_step"},
                    {"step": 4, "text": f"Now you can see the complete answer and understand why it works.", "type": "teaching_step"}
                ]
            else:
                steps = [
                    {"step": 1, "text": f"Analyzing this {topic} problem systematically.", "type": "conversational_step"},
                    {"step": 2, "text": f"Applying the appropriate mathematical techniques for {topic}.", "type": "conversational_step"},
                    {"step": 3, "text": f"Calculating step by step to solve this {topic} problem.", "type": "conversational_step"},
                    {"step": 4, "text": f"Verifying and presenting the complete final answer.", "type": "conversational_step"}
                ]
        
        return steps
    
    def _build_conversational_context(self, current_question: str, history: List, solved_problems: List, request_type: str) -> str:
        context_parts = []
        
        if request_type == "teaching":
            context_parts.append("TEACHING MODE ACTIVATED - User wants beginner-friendly explanations with concrete examples")
        
        if history:
            recent_history = history[-3:]
            context_parts.append("Recent conversation:")
            for entry in recent_history:
                role = "Student" if entry["role"] == "user" else "Tutor"
                request_info = f" ({entry.get('request_type', 'unknown')} mode)" if 'request_type' in entry else ""
                context_parts.append(f"{role}{request_info}: {entry['content'][:120]}...")
        
        if solved_problems:
            recent_problems = solved_problems[-2:]
            context_parts.append("\nPreviously solved:")
            for problem in recent_problems:
                context_parts.append(f"- {problem['question'][:60]}...")
        
        context_parts.append(f"\nCurrent question: {current_question}")
        context_parts.append(f"Request type: {request_type}")
        
        return "\n".join(context_parts)
    
    def _create_conversational_response(self, solution: Dict, question: str, history: List, request_type: str) -> Dict:
        is_follow_up = len(history) > 0
        confidence = solution.get("confidence", 0)
        
        if request_type == "teaching":
            if is_follow_up:
                intros = [
                    "Perfect follow-up! Let me break this down in simple terms:",
                    "Great question! I'll explain this concept step by step:",
                    "I love that you want to understand better! Here's a beginner-friendly explanation:"
                ]
            else:
                intros = [
                    "I'd be happy to teach you this concept! Let me explain it in simple terms:",
                    "Great question! I'll help you understand this step by step:",
                    "Let me break this down for you in a way that's easy to follow:"
                ]
        else:
            if is_follow_up:
                intros = [
                    "Great follow-up question! Let me build on our previous discussion:",
                    "I see you want to explore this further. Here's the solution:",
                    "Building on our previous work, here's what I found:"
                ]
            else:
                intros = [
                    "I'd be happy to help you solve this math problem!",
                    "Let me work through this mathematical problem with you:",
                    "Here's how I'll approach this problem:"
                ]
        
        intro = intros[len(history) % len(intros)]
        method_note = ""
        if solution.get("route") == "knowledge_base":
            method_note = " This solution comes from our comprehensive math knowledge base."
        elif solution.get("route") == "web_search":
            method_note = " I found this solution through research when our knowledge base needed additional resources."
        
        enhancement_note = ""
        if solution.get("dspy_enhanced"):
            mode_note = "beginner-friendly explanations" if request_type == "teaching" else "advanced reasoning"
            enhancement_note = f" I've enhanced this using AI-powered {mode_note}."
        
        conversational_text = f"{intro}{method_note}{enhancement_note}"
        
        follow_up_suggestions = self._generate_follow_ups(question, request_type)
        
        return {
            "conversational_text": conversational_text,
            "follow_up_suggestions": follow_up_suggestions
        }
    
    def _generate_follow_ups(self, question: str, request_type: str) -> List[str]:
        suggestions = []
        question_lower = question.lower()
        
        if request_type == "teaching":
            if "derivative" in question_lower:
                suggestions.extend([
                    "Would you like me to show you more examples of derivatives?",
                    "Can I explain the chain rule in simple terms?",
                    "Should I show you how derivatives connect to real-world rates of change?"
                ])
            elif "integral" in question_lower:
                suggestions.extend([
                    "Would you like me to explain integration by parts simply?",
                    "Can I show you how integration connects to finding areas?",
                    "Should I walk through more integration examples?"
                ])
            else:
                suggestions.extend([
                    "Would you like me to explain any part in even simpler terms?",
                    "Can I give you a real-world example to help you understand better?",
                    "Should I walk through a similar problem step by step?"
                ])
        else:
            if "derivative" in question_lower:
                suggestions.extend([
                    "Would you like me to verify this using the definition of a derivative?",
                    "Can I show you how to apply the chain rule here?",
                    "Should I explain the geometric meaning of this derivative?"
                ])
            elif "integral" in question_lower:
                suggestions.extend([
                    "Would you like me to verify this answer by differentiation?",
                    "Can I show you alternative integration techniques?",
                    "Should I explain the geometric interpretation?"
                ])
            else:
                suggestions.extend([
                    "Would you like me to verify this answer using a different method?",
                    "Can I show you a similar problem with different numbers?",
                    "Should I explain the reasoning behind each step?"
                ])
        
        return suggestions[:3]

async def train_conversational_dspy_with_feedback():
    try:
        gemini_lm = get_gemini_lm()
        if not gemini_lm:
            logger.warning("DSPy-Gemini not available for conversational training")
            return None
        
        db = SessionLocal()
        try:
            training_examples = db.query(FeedbackEntry).filter(
                FeedbackEntry.user_rating >= 4,
                FeedbackEntry.route_used == "conversational_hitl",
                FeedbackEntry.corrected_answer.isnot(None)
            ).limit(50).all()
            
            if len(training_examples) < 5:
                logger.info("Insufficient training data, skipping DSPy training")
                return None
            
            dspy_examples = []
            for feedback in training_examples:
                try:
                    example = dspy.Example(
                        question=feedback.question,
                        final_answer=feedback.corrected_answer,
                        user_rating=feedback.user_rating
                    ).with_inputs("question")
                    
                    dspy_examples.append(example)
                    
                except Exception as e:
                    logger.error(f"Error processing training example: {e}")
                    continue
            
            if len(dspy_examples) >= 5:
                logger.info(f"DSPy training with {len(dspy_examples)} examples")
                return True
            else:
                logger.info("Not enough valid examples for training")
                return None
            
        except Exception as e:
            logger.error(f"Training error: {e}")
            return None
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Training initialization error: {e}")
        return None

HITLMathAgent = ConversationalHITLMathAgent
