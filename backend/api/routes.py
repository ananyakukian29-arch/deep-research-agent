from fastapi import APIRouter, HTTPException, BackgroundTasks
import uuid
from backend.api.models import ResearchRequest, TaskResponse
from backend.tasks.graph_tasks import run_research_pipeline

# INJECTED IMPORT: Pulls the DB function you just wrote
from backend.memory.db import fetch_recent_history

router = APIRouter()

# Mock Celery's state tracker to keep the React frontend polling loop alive
MOCK_CELERY_STORE = {}

def background_execution_wrapper(task_id: str, query: str):
    """Executes the LangGraph pipeline natively in a FastAPI background thread."""
    try:
        MOCK_CELERY_STORE[task_id] = {"status": "PROGRESS", "details": "Processing..."}
        
        # Call your existing LangGraph logic synchronously
        # Note: If run_research_pipeline is still decorated with @celery_app.task in graph_tasks.py, 
        # you must call it as run_research_pipeline.__wrapped__(query) to bypass Celery.
        result = run_research_pipeline(query, task_id) 
        
        MOCK_CELERY_STORE[task_id] = {"status": "SUCCESS", "result": result}
    except Exception as e:
        MOCK_CELERY_STORE[task_id] = {"status": "FAILURE", "error": str(e)}

@router.post("/research", response_model=TaskResponse)
def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Takes a user query, sends it to FastAPI BackgroundTasks, and returns a Task ID."""
    try:
        task_id = str(uuid.uuid4())
        MOCK_CELERY_STORE[task_id] = {"status": "PENDING"}
        
        # Offload execution to FastAPI's internal thread pool
        background_tasks.add_task(background_execution_wrapper, task_id, request.query)
        
        return TaskResponse(task_id=task_id, status="PENDING")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{task_id}")
def get_task_status(task_id: str):
    """Checks the in-memory store for the live status of a specific task."""
    task_data = MOCK_CELERY_STORE.get(task_id)
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Formatting explicitly matches what React expects from the old Celery logic
    response = {
        "task_id": task_id,
        "status": task_data["status"],
    }
    
    if task_data["status"] == 'PROGRESS':
        response["details"] = task_data.get("details", "Processing...")
    elif task_data["status"] == 'SUCCESS':
        response["result"] = task_data.get("result")
    elif task_data["status"] == 'FAILURE':
        response["error"] = task_data.get("error", "Unknown error occurred")
        
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