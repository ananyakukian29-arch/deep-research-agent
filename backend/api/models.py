from pydantic import BaseModel

class ResearchRequest(BaseModel):
    query: str

class TaskResponse(BaseModel):
    task_id: str
    status: str