from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult
from backend.api.models import ResearchRequest, TaskResponse
from backend.tasks.graph_tasks import run_research_pipeline
from backend.celery_app import celery_app

# INJECTED IMPORT: Pulls the DB function you just wrote
from backend.memory.db import fetch_recent_history

router = APIRouter()

@router.post("/research", response_model=TaskResponse)
def start_research(request: ResearchRequest):
    """Takes a user query, sends it to the Celery worker, and returns a Task ID."""
    try:
        task = run_research_pipeline.delay(request.query)
        return TaskResponse(task_id=task.id, status="PENDING")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{task_id}")
def get_task_status(task_id: str):
    """Checks Redis for the live status of a specific task."""
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
    }
    
    if task_result.state == 'PROGRESS':
        response["details"] = task_result.info.get("status", "Processing...")
    elif task_result.state == 'SUCCESS':
        response["result"] = task_result.result
    elif task_result.state == 'FAILURE':
        response["error"] = str(task_result.info)
        
    return response

# INJECTED ENDPOINT: Serves MongoDB data to the React UI
@router.get("/history")
def get_research_history(limit: int = 20):
    """Fetches the most recent research runs from MongoDB for the UI sidebar."""
    try:
        data = fetch_recent_history(limit=limit)
        return {"history": data}
    except Exception as e:
        # Fails safely so the backend doesn't crash if Mongo drops
        return {"error": f"Failed to fetch history: {str(e)}"}