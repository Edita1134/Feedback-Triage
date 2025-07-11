from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models.feedback import FeedbackRequest, FeedbackResponse, ErrorResponse, FeedbackHistoryResponse, DashboardStats
from models.database import get_db, FeedbackHistory, create_tables
from services.llm_service import LLMService
from services.validation import input_validator
import logging
import time
from datetime import datetime, timedelta
from sqlalchemy import func, desc

router = APIRouter()
logger = logging.getLogger(__name__)

# Ensure database tables exist
create_tables()


def get_client_ip(request: Request) -> str:
    """Get client IP from request"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/triage", response_model=FeedbackResponse)
async def triage_feedback(request: FeedbackRequest, http_request: Request, db: Session = Depends(get_db)):
    """
    Analyze user feedback and classify it by category and urgency.
    
    Enhanced with input validation, database storage, and detailed logging.
    """
    start_time = time.time()
    client_ip = get_client_ip(http_request)
    
    try:
        # Enhanced input validation
        validation_result = input_validator.validate_feedback_text(request.text)
        
        if not validation_result["valid"]:
            logger.warning(f"Invalid input from {client_ip}: {validation_result['errors']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Input validation failed",
                    "message": "The feedback text contains issues that need to be addressed",
                    "errors": validation_result["errors"],
                    "warnings": validation_result.get("warnings", []),
                    "status_code": 400
                }
            )
        
        # Log warnings if any
        if validation_result.get("warnings"):
            logger.info(f"Input warnings from {client_ip}: {validation_result['warnings']}")
        
        # Use cleaned text for analysis
        cleaned_text = validation_result["cleaned_text"]
        
        # Initialize LLM service
        llm_service = LLMService()
        
        # Check if user manually selected a category
        if request.category and request.category.strip():
            # User manually selected category - use it and only analyze urgency
            logger.info(f"Using manually selected category: {request.category}")
            analysis = await llm_service.analyze_feedback_with_category(cleaned_text, request.category)
        else:
            # Let LLM analyze and determine category automatically
            logger.info("LLM analyzing category automatically")
            analysis = await llm_service.analyze_feedback(cleaned_text)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Store in database
        feedback_record = FeedbackHistory(
            feedback_text=cleaned_text,
            category=analysis.category.value,
            urgency_score=analysis.urgency_score.value,
            confidence_score=analysis.confidence_score,
            processing_time=processing_time,
            llm_provider=llm_service.get_provider_name(),
            user_ip=client_ip
        )
        
        db.add(feedback_record)
        db.commit()
        db.refresh(feedback_record)
        
        logger.info(f"Feedback analyzed: ID={feedback_record.id}, Category={analysis.category.value}, Urgency={analysis.urgency_score.value}, Time={processing_time:.2f}s")
        
        # Return response
        return FeedbackResponse(
            feedback_text=cleaned_text,
            category=analysis.category,
            urgency_score=analysis.urgency_score
        )
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service configuration error"
        )
    
    except Exception as e:
        logger.error(f"Error analyzing feedback: {e}")
        
        # Handle specific error types
        if "API error" in str(e) or "timeout" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM service is temporarily unavailable"
            )
        elif "parse" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid response from LLM service"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "feedback-triage-api"}


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(db: Session = Depends(get_db)):
    """
    Get dashboard statistics and recent feedback history.
    """
    try:
        # Get total feedback count
        total_feedback = db.query(FeedbackHistory).count()
        
        # Get category distribution
        category_stats = db.query(
            FeedbackHistory.category,
            func.count(FeedbackHistory.id).label('count')
        ).group_by(FeedbackHistory.category).all()
        
        categories = {stat.category: stat.count for stat in category_stats}
        
        # Get urgency distribution
        urgency_stats = db.query(
            FeedbackHistory.urgency_score,
            func.count(FeedbackHistory.id).label('count')
        ).group_by(FeedbackHistory.urgency_score).all()
        
        urgency_distribution = {str(stat.urgency_score): stat.count for stat in urgency_stats}
        
        # Get average processing time
        avg_time_result = db.query(func.avg(FeedbackHistory.processing_time)).scalar()
        avg_processing_time = float(avg_time_result) if avg_time_result else None
        
        # Get recent feedback (last 10)
        recent_feedback = db.query(FeedbackHistory).order_by(
            desc(FeedbackHistory.created_at)
        ).limit(10).all()
        
        recent_feedback_list = [
            FeedbackHistoryResponse(
                id=record.id,
                feedback_text=record.feedback_text,
                category=record.category,
                urgency_score=record.urgency_score,
                confidence_score=record.confidence_score,
                processing_time=record.processing_time,
                llm_provider=record.llm_provider,
                created_at=record.created_at,
                user_ip=record.user_ip
            ) for record in recent_feedback
        ]
        
        return DashboardStats(
            total_feedback=total_feedback,
            categories=categories,
            urgency_distribution=urgency_distribution,
            avg_processing_time=avg_processing_time,
            recent_feedback=recent_feedback_list
        )
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard data"
        )


@router.get("/feedback/history")
async def get_feedback_history(
    limit: int = 20, 
    offset: int = 0,
    category: str = None,
    urgency: int = None,
    db: Session = Depends(get_db)
):
    """
    Get paginated feedback history with optional filtering.
    """
    try:
        query = db.query(FeedbackHistory)
        
        # Apply filters
        if category:
            query = query.filter(FeedbackHistory.category == category)
        if urgency:
            query = query.filter(FeedbackHistory.urgency_score == urgency)
        
        # Get total count for pagination
        total = query.count()
        
        # Apply pagination
        feedback_records = query.order_by(
            desc(FeedbackHistory.created_at)
        ).offset(offset).limit(limit).all()
        
        feedback_list = [
            FeedbackHistoryResponse(
                id=record.id,
                feedback_text=record.feedback_text,
                category=record.category,
                urgency_score=record.urgency_score,
                confidence_score=record.confidence_score,
                processing_time=record.processing_time,
                llm_provider=record.llm_provider,
                created_at=record.created_at,
                user_ip=record.user_ip
            ) for record in feedback_records
        ]
        
        return {
            "feedback": feedback_list,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
        
    except Exception as e:
        logger.error(f"History fetch error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch feedback history"
        )
