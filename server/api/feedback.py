from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from database.feedback_model import FeedbackEntry, SessionLocal, LearningMetrics
import json
from datetime import datetime

router = APIRouter()

class FeedbackRequest(BaseModel):
    question: str
    original_solution: dict
    user_rating: int  
    user_comment: Optional[str] = None
    corrected_answer: Optional[str] = None
    corrected_steps: Optional[List[str]] = None
    
class FeedbackResponse(BaseModel):
    status: str
    message: str
    feedback_id: int
    improvement_triggered: bool

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest, db: Session = Depends(get_db)):
    """Collect user feedback for HITL learning"""
    
    try:
        feedback_entry = FeedbackEntry(
            question=feedback.question,
            original_solution=json.dumps(feedback.original_solution),
            user_rating=feedback.user_rating,
            user_comment=feedback.user_comment,
            corrected_answer=feedback.corrected_answer,
            corrected_steps=json.dumps(feedback.corrected_steps) if feedback.corrected_steps else None,
            is_helpful=feedback.user_rating >= 3,
            route_used=feedback.original_solution.get("route", "unknown"),
            confidence_score=feedback.original_solution.get("confidence", 0.0),
            topic=feedback.original_solution.get("topic", "mathematics"),
            difficulty=feedback.original_solution.get("difficulty", 0)
        )
        
        db.add(feedback_entry)
        db.commit()
        db.refresh(feedback_entry)
        improvement_triggered = False
        if feedback.user_rating <= 2:
            await trigger_learning_improvement(feedback_entry.id, db)
            improvement_triggered = True
        
        return FeedbackResponse(
            status="success",
            message="Feedback received! This will help improve our math tutoring.",
            feedback_id=feedback_entry.id,
            improvement_triggered=improvement_triggered
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {str(e)}")

@router.get("/learning-stats")
async def get_learning_stats(db: Session = Depends(get_db)):
    """Get learning performance statistics"""
    total_feedback = db.query(FeedbackEntry).count()
    
    if total_feedback == 0:
        return {"status": "no_feedback", "message": "No feedback data available yet"}
    avg_rating_result = db.query(db.func.avg(FeedbackEntry.user_rating)).scalar()
    avg_rating = float(avg_rating_result) if avg_rating_result else 0.0

    kb_feedback = db.query(FeedbackEntry).filter(FeedbackEntry.route_used == "knowledge_base").all()
    web_feedback = db.query(FeedbackEntry).filter(FeedbackEntry.route_used == "web_search").all()
    
    kb_accuracy = sum(1 for f in kb_feedback if f.user_rating >= 4) / len(kb_feedback) if kb_feedback else 0
    web_accuracy = sum(1 for f in web_feedback if f.user_rating >= 4) / len(web_feedback) if web_feedback else 0
    low_ratings = db.query(FeedbackEntry).filter(FeedbackEntry.user_rating <= 2).count()
    high_ratings = db.query(FeedbackEntry).filter(FeedbackEntry.user_rating >= 4).count()
    
    return {
        "total_feedback": total_feedback,
        "average_rating": round(avg_rating, 2),
        "kb_accuracy": round(kb_accuracy, 2),
        "web_accuracy": round(web_accuracy, 2),
        "low_ratings": low_ratings,
        "high_ratings": high_ratings,
        "learning_status": "active" if low_ratings > 0 else "stable"
    }

async def trigger_learning_improvement(feedback_id: int, db: Session):
    """Trigger learning improvements for low-rated responses"""
    
    feedback = db.query(FeedbackEntry).filter(FeedbackEntry.id == feedback_id).first()
    if not feedback:
        return
    
    if feedback.corrected_answer or feedback.corrected_steps:
        print(f" Learning trigger: Feedback ID {feedback_id} with corrections")
        await update_dspy_training_data(feedback)

async def update_dspy_training_data(feedback: FeedbackEntry):
    """Update DSPy training data with corrected examples"""
    print(f" Adding training example from feedback ID {feedback.id}")
