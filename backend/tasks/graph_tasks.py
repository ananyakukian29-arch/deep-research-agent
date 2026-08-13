from celery import shared_task
from backend.workflow import app_graph
from backend.memory.db import save_research_run
import time

@shared_task(bind=True)
def run_research_pipeline(self, user_query: str):
    """Executes the LangGraph pipeline asynchronously in the background."""
    
    current_state = {
        "user_request": user_query,
        "research_plan": [],
        "current_topic": "",
        "collected_research": [],
        "final_report": "",
        "loop_count": 0,
        "metrics": {
            "total_cost": 0.0, 
            "total_prompt_tokens": 0, 
            "total_completion_tokens": 0, 
            "node_latencies": {}
        }
    }
    
    start_time = time.perf_counter()
    
    try:
        self.update_state(state="PROGRESS", meta={"status": "Starting multi-agent workflow..."})
        
        for event in app_graph.stream(current_state):
            for node_name, state_update in event.items():
                current_state.update(state_update)
                
                if node_name == "orchestrator":
                    self.update_state(state="PROGRESS", meta={"status": "Orchestrator generated plan."})
                elif node_name == "researcher":
                    self.update_state(state="PROGRESS", meta={"status": "Researcher collecting facts."})
                elif node_name == "synthesizer":
                    self.update_state(state="PROGRESS", meta={"status": "Synthesizer writing report."})

        elapsed_latency = round(time.perf_counter() - start_time, 2)
        report = current_state.get("final_report", "").strip()

        if not report:
            return {"status": "FAILED", "error": "No report generated."}

        saved_id = save_research_run(
            user_request=current_state.get("user_request", ""),
            sub_topics=current_state.get("research_plan", []),
            final_report=report,
            latency_seconds=elapsed_latency
        )

        return {
            "status": "SUCCESS", 
            "report": report,
            "latency": elapsed_latency,
            "saved_id": saved_id
        }

    except Exception as e:
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise e