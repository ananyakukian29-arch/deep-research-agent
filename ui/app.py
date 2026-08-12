import sys
import os
import streamlit as st

# Add root directory to python path for clean import resolution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app_graph

# Page configuration
st.set_page_config(
    page_title="Deep Research Agent",
    page_icon="🔬",
    layout="wide"
)

st.title("🔬 Deep Research Agent System")
st.caption("Powered by Multi-Agent LangGraph Architecture & Groq LLMs")

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
        
        # Mirroring exact AgentState structure
        current_state = {
            "user_request": user_query,
            "research_plan": [],
            "current_topic": "",
            "collected_research": [],
            "final_report": "",
            "loop_count": 0
        }
        
        try:
            status_box.write("🚀 **Pipeline:** Starting multi-agent workflow...")
            
            # Stream execution real-time across graph nodes
            for event in app_graph.stream(current_state):
                for node_name, state_update in event.items():
                    current_state.update(state_update)
                    
                    if node_name == "orchestrator":
                        plan = state_update.get("research_plan", [])
                        status_box.write(f"🧠 **Orchestrator:** Generated plan with {len(plan)} sub-topics.")
                        for idx, topic in enumerate(plan, 1):
                            status_box.write(f"  • Sub-topic {idx}: *{topic}*")
                            
                    elif node_name == "researcher":
                        research_count = len(state_update.get("collected_research", []))
                        status_box.write(f"🔎 **Researcher:** Completed research pass ({research_count} context blocks collected).")
                        
                    elif node_name == "synthesizer":
                        status_box.write("📝 **Synthesizer:** Compiling and formatting final Markdown report...")

            report = current_state.get("final_report", "").strip()

            if not report:
                status_box.update(label="Pipeline Completed (Empty Output)", state="error", expanded=True)
                st.error("Execution finished, but no report was generated. Check terminal logs for backend details.")
            else:
                status_box.update(label="Research Complete!", state="complete", expanded=False)
                
                # Render Report
                st.subheader("📄 Generated Research Report")
                st.markdown(report)
                
                st.divider()
                
                # Download button
                st.download_button(
                    label="Download Report (.md)",
                    data=report,
                    file_name="research_report.md",
                    mime="text/markdown"
                )
                
        except Exception as e:
            status_box.update(label="Error Occurred!", state="error", expanded=True)
            st.error(f"Execution failed with error:\n\n`{str(e)}`")