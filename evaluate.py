import pandas as pd
import time
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from main import app_graph

# Initialize your free Judge
judge_llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

def evaluate_run(prompt, output, criteria):
    """Uses Groq to score output and provide explicit feedback."""
    eval_prompt = f"""
    You are an objective grader. 
    User Prompt: {prompt}
    Agent Output: {output}
    Grading Criteria: {criteria}
    
    Did the Agent Output meet ALL Grading Criteria? 
    Provide a concise 1-sentence explanation of why it passed or failed, then end strictly with either 'VERDICT: PASS' or 'VERDICT: FAIL'.
    """
    result = judge_llm.invoke([HumanMessage(content=eval_prompt)])
    raw_response = result.content.strip()
    
    # Extract verdict and return the full feedback for debugging
    is_pass = 1 if "VERDICT: PASS" in raw_response.upper() else 0
    return is_pass, raw_response

def run_eval_suite():
    try:
        df = pd.read_csv("eval_dataset.csv")
    except FileNotFoundError:
        print("CRITICAL ERROR: eval_dataset.csv not found in the root directory.")
        return

    results = []
    
    for index, row in df.iterrows():
        print(f"\n" + "="*50)
        print(f"Testing: {row['prompt']}")
        print("="*50)
        
        initial_state = {
            "user_request": row['prompt'], 
            "research_plan": [], 
            "current_topic": "", 
            "collected_research": [], 
            "final_report": "", 
            "loop_count": 0
        }
        
        # Execute the LangGraph workflow
        final_state = app_graph.invoke(initial_state)
        report = final_state.get("final_report", "")
        
        # Diagnostic 1: Did it even generate a report?
        if not report or len(report.strip()) == 0:
            print("❌ FAIL: Final report is EMPTY. Pipeline broke before the Synthesizer.")
            results.append(0)
            continue
            
        print(f"📄 Report Generated: {len(report)} characters.")
        
        # Diagnostic 2: What did the Judge actually say?
        # ... existing evaluate.py code ...
        score, feedback = evaluate_run(row['prompt'], report, row['expected_criteria'])
        print(f"\n🤖 Judge Feedback:\n{feedback}\n")
        
        results.append(score)
        
        # PROACTIVE PACING: Let the TPM bucket refill before starting the next full test
        # PROACTIVE PACING: Let the TPM bucket completely flush
        print("⏳ Pacing test suite: Sleeping 65s before next run to clear TPM bucket...")
        time.sleep(65)
        
    pass_rate = (sum(results) / len(results)) * 100 if results else 0.0
    # ... rest of file ...
    print("="*50)
    print(f"Final Pass Rate: {pass_rate:.1f}%")
    print("="*50)

if __name__ == "__main__":
    run_eval_suite()