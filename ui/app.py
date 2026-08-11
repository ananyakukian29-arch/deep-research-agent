import streamlit as st
import sys
import os

# Add root folder to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app_graph

st.set_page_config(
    page_title="Deep Research Agent",
    page_icon="🔬",
    layout="wide"
)

st.title("🔬 Deep Research Agent System")
st.caption("Powered by Gemini (Research & Planning) and Groq (Fast Report Synthesis)")

# Input Section
user_query = st.text_area(
    "Enter your research query:",
    placeholder="e.g., Analyze the performance and security trade-offs of microservices vs monolithic architectures for high-traffic financial applications.",
    height=100
)

if st.button("Start Deep Research", type="primary"):
    if not user_query.strip():
        st.warning("Please enter a research query before starting.")
    else:
        st.divider()
        status_box = st.status("Initializing Research Pipeline...", expanded=True)
        
        initial_state = {
            "user_request": user_query,
            "research_plan": [],
            "current_topic": "",
            "collected_research": [],
            "final_report": "",
            "loop_count": 0
        }
        
        try:
            status_box.write("🧠 **Orchestrator:** Generating sub-topic research plan...")
            
            # Execute graph
            final_output = app_graph.invoke(initial_state)
            
            status_box.update(label="Research Complete!", state="complete", expanded=False)
            
            # Render Report
            st.subheader("📄 Generated Research Report")
            report = final_output.get("final_report", "No report was generated.")
            st.markdown(report)
            
            # Download option
            st.download_button(
                label="Download Report (.md)",
                data=report,
                file_name="research_report.md",
                mime="text/markdown"
            )
            
        except Exception as e:
            status_box.update(label="Error Occurred!", state="error", expanded=True)
            st.error(f"Execution failed: {str(e)}")