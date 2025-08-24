import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from guardrails.middleware import GuardrailMiddleware
import time
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from agents.hitl_math_agent import ConversationalHITLMathAgent, train_conversational_dspy_with_feedback
from api.feedback import router as feedback_router
from database.feedback_model import init_database
from utils.dspy_gemini import initialize_gemini_dspy
from Knowledge_Base.ingest import QuickIngest
import os
from dotenv import load_dotenv
import traceback

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

hitl_math_agent = None
dspy_config = None

class StreamingManager:
    def __init__(self):
        self.active_streams = {}
    
    async def create_stream(self, session_id: str):
        queue = asyncio.Queue()
        self.active_streams[session_id] = queue
        logger.info(f" Created stream for session: {session_id}")
        return queue
    
    async def send_to_stream(self, session_id: str, data: dict):
        if session_id in self.active_streams:
            try:
                await self.active_streams[session_id].put(data)
            except Exception as e:
                logger.error(f" Error sending to stream {session_id}: {e}")
    
    def close_stream(self, session_id: str):
        if session_id in self.active_streams:
            del self.active_streams[session_id]
            logger.info(f" Closed stream for session: {session_id}")

streaming_manager = StreamingManager()


class ConversationContextManager:
    def __init__(self):
        self.conversations = {} 
        self.max_history_length = 20  
        logger.info(" ConversationContextManager initialized")
    
    def get_conversation_context(self, session_id: str) -> Dict:
        """Get conversation context for a session"""
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                "history": [],
                "metadata": {
                    "created_at": time.time(),
                    "last_activity": time.time(),
                    "message_count": 0
                }
            }
            logger.info(f" Created new conversation context for session: {session_id}")
        
        return self.conversations[session_id]
    
    def add_message(self, session_id: str, message: Dict):
        """Add a message to conversation history"""
        context = self.get_conversation_context(session_id)
        message_with_timestamp = {
            **message,
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat()
        }
        context["history"].append(message_with_timestamp)
        
        logger.info(f" Added message to {session_id}: {message.get('role', 'unknown')} - {message.get('content', '')[:50]}...")
        
        if len(context["history"]) > self.max_history_length:
            removed_count = len(context["history"]) - self.max_history_length
            context["history"] = context["history"][-self.max_history_length:]
            logger.info(f" Trimmed {removed_count} old messages from session {session_id}")
        
        context["metadata"]["last_activity"] = time.time()
        context["metadata"]["message_count"] += 1
    
    def get_formatted_history(self, session_id: str) -> List[Dict]:
        """Get formatted conversation history for the agent"""
        context = self.get_conversation_context(session_id)
        formatted_history = [
            {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg.get("timestamp"),
                "request_type": msg.get("request_type", "unknown")
            }
            for msg in context["history"]
        ]
        
        logger.info(f" Formatted history for {session_id}: {len(formatted_history)} messages")
        return formatted_history

conversation_manager = ConversationContextManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global hitl_math_agent, dspy_config
    
    logger.info(" Starting system initialization...")
    
    try:
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY required for Gemini integration")
        
        try:
            dspy_config = initialize_gemini_dspy()
            logger.info(" DSPy-Gemini configuration initialized")
        except Exception as e:
            logger.warning(f" DSPy-Gemini initialization failed: {e}")
            dspy_config = None
        
        try:
            init_database()
            logger.info(" Database initialized")
        except Exception as e:
            logger.warning(f" Database initialization failed: {e}")
        
        kb_direct = QuickIngest()
        
        try:
            kb_info = kb_direct.get_collection_info()
            if kb_info.get("points_count", 0) == 0:
                logger.info(" Loading Hendrycks MATH dataset...")
                kb_direct.ingest(limit=500)
            logger.info(f" KB ready with {kb_info.get('points_count', 0)} problems")
        except Exception as e:
            logger.warning(f" KB initialization warning: {e}")
        
        try:
            hitl_math_agent = ConversationalHITLMathAgent()
            logger.info(" Conversational HITL Math Agent initialized")
        except Exception as e:
            logger.error(f" HITL Agent initialization failed: {e}")
            hitl_math_agent = None
        
        if hitl_math_agent and dspy_config:
            try:
                logger.info("🎓 Training conversational DSPy with feedback data...")
                await train_conversational_dspy_with_feedback()
                logger.info(" Conversational DSPy training completed")
            except Exception as e:
                logger.warning(f" DSPy training warning: {e}")
        
        logger.info(" System initialization complete!")
        
    except Exception as e:
        logger.error(f" Startup error: {e}")
        traceback.print_exc()
        hitl_math_agent = None
    
    yield
    
    logger.info(" Shutting down system...")

app = FastAPI(
    title="Conversational Math Agent with Human-in-the-Loop Learning", 
    version="2.5.0",
    description="Fixed Conversational Math Agent with proper context management",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "*"],
    allow_methods=["*"], 
    allow_headers=["*"],
    allow_credentials=True
)
app.add_middleware(GuardrailMiddleware)

app.include_router(feedback_router, prefix="/api")

processing_lock = asyncio.Lock()

@app.post("/api/solve")
async def solve_math_problem(request: Request):
    """Fixed endpoint with proper context management"""
    
    async with processing_lock:  
        logger.info(" NEW SOLVE REQUEST")
        
        if not hitl_math_agent:
            logger.error(" Math agent not ready")
            raise HTTPException(status_code=503, detail="Math agent not ready")
        
        body = await request.json()
        question = body.get("question", "")
        external_history = body.get("conversation_history", [])
        session_id = body.get("session_id", f"session_{int(time.time())}")
        
        logger.info(f" REQUEST DETAILS:")
        logger.info(f"    Session ID: {session_id}")
        logger.info(f"    Question: {question}")
        logger.info(f"    External history: {len(external_history)} messages")
        
        if not question:
            logger.error(" No question provided")
            raise HTTPException(status_code=400, detail="Question required")
        

        teaching_keywords = ["explain like", "make me understand", "teach me", "beginner", "simple", "basics", "noob", "more about"]
        detected_request_type = "teaching" if any(keyword in question.lower() for keyword in teaching_keywords) else "solving"
        
        logger.info(f" DETECTED REQUEST TYPE: {detected_request_type}")
        

        stored_context = conversation_manager.get_conversation_context(session_id)
        

        if external_history and not stored_context["history"]:
            logger.info(f" Importing external history: {len(external_history)} messages")
            for msg in external_history:
                conversation_manager.add_message(session_id, msg)
        

        user_message = {
            "role": "user",
            "content": question,
            "request_type": detected_request_type
        }
        conversation_manager.add_message(session_id, user_message)
        

        complete_history = conversation_manager.get_formatted_history(session_id)
        
        logger.info(f" COMPLETE CONVERSATION HISTORY: {len(complete_history)} messages")
        for i, msg in enumerate(complete_history[-3:]): 
            logger.info(f"   [{i}] {msg['role']}: {msg['content'][:50]}... (type: {msg.get('request_type', 'unknown')})")

        async def event_generator():
            try:
                queue = await streaming_manager.create_stream(session_id)
                
                yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
                
                yield f"data: {json.dumps({'type': 'processing_started', 'message': 'Starting to solve your math problem...', 'question': question[:100]})}\n\n"

                context = {
                    "conversation_history": complete_history,
                    "session_id": session_id,
                    "enable_conversational_response": True,
                    "is_follow_up": len(complete_history) > 1,
                    "streaming": True,
                    "request_type": detected_request_type,
                    "educational_level": "beginner" if detected_request_type == "teaching" else "tutor",
                    "context_metadata": {
                        "total_messages": len(complete_history),
                        "has_previous_context": len(complete_history) > 1,
                        "teaching_mode": detected_request_type == "teaching"
                    }
                }
                
                logger.info(f" CALLING AGENT WITH ENHANCED CONTEXT:")
                logger.info(f"    Messages: {context['context_metadata']['total_messages']}")
                logger.info(f"   Follow-up: {context['is_follow_up']}")
                logger.info(f"    Teaching mode: {context['context_metadata']['teaching_mode']}")
                
                if hasattr(hitl_math_agent, 'solve_conversational_stream'):
                    result = await hitl_math_agent.solve_conversational_stream(question, context, streaming_manager)

                    while not queue.empty():
                        try:
                            event_data = await asyncio.wait_for(queue.get(), timeout=1.0)
                            yield f"data: {json.dumps(event_data)}\n\n"
                        except asyncio.TimeoutError:
                            break
                else:
                    result = await hitl_math_agent.solve_conversational(question, context)
                
                    if result.get("steps"):
                        for i, step in enumerate(result["steps"]):
                            yield f"data: {json.dumps({'type': 'step_generated', 'step_number': i + 1, 'step_data': step, 'total_steps': len(result['steps'])})}\n\n"
                            await asyncio.sleep(0.3)
                if not result.get("steps"):
                    result["steps"] = [
                        {"step": 1, "text": "Analysis with conversation context", "type": "solution_step"},
                        {"step": 2, "text": "Applied mathematical techniques", "type": "solution_step"},
                        {"step": 3, "text": "Calculated systematically", "type": "solution_step"},
                        {"step": 4, "text": "Complete result provided", "type": "solution_step"}
                    ]
                
                result["session_id"] = session_id
                result["context_aware"] = len(complete_history) > 1
                
                logger.info(f" SOLUTION GENERATED:")
                logger.info(f"    Request type: {result.get('request_type', 'unknown')}")
                logger.info(f"    Context aware: {result.get('context_aware', False)}")
                logger.info(f"    Steps: {len(result.get('steps', []))}")

                ai_message = {
                    "role": "assistant",
                    "content": result.get("conversational_response", "Solution provided"),
                    "request_type": result.get("request_type", detected_request_type)
                }
                conversation_manager.add_message(session_id, ai_message)
                
                yield f"data: {json.dumps({'type': 'solution_complete', 'data': result})}\n\n"
                
            except Exception as e:
                logger.error(f" Streaming solve error: {e}")
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'message': f'Error: {str(e)}'})}\n\n"
            
            finally:
                streaming_manager.close_stream(session_id)
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )

@app.get("/api/context/{session_id}")
async def get_conversation_context(session_id: str):
    """Get conversation context for debugging"""
    context = conversation_manager.get_conversation_context(session_id)
    return {
        "session_id": session_id,
        "message_count": len(context["history"]),
        "metadata": context["metadata"],
        "full_history": context["history"]
    }

@app.get("/api/health")
async def health_check():
    """Health check with context stats"""
    total_conversations = len(conversation_manager.conversations)
    total_messages = sum(len(conv["history"]) for conv in conversation_manager.conversations.values())
    
    return {
        "status": "healthy" if hitl_math_agent else "unhealthy",
        "streaming": "enabled",
        "active_conversations": total_conversations,
        "total_stored_messages": total_messages,
        "context_management": "fixed",
        "duplicate_processing": "prevented"
    }

if __name__ == "__main__":
    import uvicorn
    logger.info(" Starting FastAPI server with FIXED context management")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
