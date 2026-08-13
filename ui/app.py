import sys
import os
import time
import streamlit as st

# Add root directory to python path for clean import resolution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app_graph
from memory.db import save_research_run, fetch_recent_history

# Page configuration
st.set_page_config(
    page_title="Deep Research Agent",
    page_icon="🔬",
    layout="wide"
)

# Initialize session state for selected history report
if "selected_report" not in st.session_state:
    st.session_state.selected_report = None
if "selected_query" not in st.session_state:
    st.session_state.selected_query = ""
if "selected_latency" not in st.session_state:
    st.session_state.selected_latency = None

st.title("🔬 Deep Research Agent System")
st.caption("Powered by Multi-Agent LangGraph Architecture & Groq LLMs")

# Sidebar: Persistent MongoDB History
st.sidebar.header("📜 Research History")

if st.sidebar.button("➕ New Research Query"):
    st.session_state.selected_report = None
    st.session_state.selected_query = ""
    st.session_state.selected_latency = None
    st.rerun()

st.sidebar.divider()

recent_history = fetch_recent_history(limit=5)

if recent_history:
    for idx, item in enumerate(recent_history, 1):
        query_text = item.get('user_request', 'Query')
        latency = item.get('latency_seconds')
        latency_label = f" ({latency}s)" if latency else ""
        if st.sidebar.button(f"{idx}. {query_text[:22]}...{latency_label}", key=f"hist_btn_{idx}"):
            st.session_state.selected_report = item.get('final_report', '')
            st.session_state.selected_query = query_text
            st.session_state.selected_latency = latency
            st.rerun()
else:
    st.sidebar.info("No prior research records found in MongoDB.")

# Main Display Logic: If a history item is selected, render it. Otherwise, show the input form.
if st.session_state.selected_report:
    st.info(f"Viewing archived report for: **{st.session_state.selected_query}**")
    if st.session_state.selected_latency:
        st.caption(f"⚡ **Execution Latency:** {st.session_state.selected_latency} seconds")
    st.subheader("📄 Archived Research Report")
    st.markdown(st.session_state.selected_report)
    
    st.divider()
    st.download_button(
        label="Download Report (.md)",
        data=st.session_state.selected_report,
        file_name="archived_research_report.md",
        mime="text/markdown"
    )
else:
    # Main Input Section
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
            
            current_state = {
                "user_request": user_query,
                "research_plan": [],
                "current_topic": "",
                "collected_research": [],
                "final_report": "",
                "loop_count": 0
            }
            
            try:
                start_time = time.perf_counter()
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

                elapsed_latency = round(time.perf_counter() - start_time, 2)
                report = current_state.get("final_report", "").strip()

                if not report:
                    status_box.update(label="Pipeline Completed (Empty Output)", state="error", expanded=True)
                    st.error("Execution finished, but no report was generated. Check terminal logs for backend details.")
                else:
                    status_box.update(label=f"Research Complete in {elapsed_latency}s!", state="complete", expanded=False)
                    
                    # Persist to MongoDB with latency metric
                    saved_id = save_research_run(
                        user_request=current_state.get("user_request", ""),
                        sub_topics=current_state.get("research_plan", []),
                        final_report=report,
                        latency_seconds=elapsed_latency
                    )
                    if saved_id:
                        st.toast(f"✅ Saved to MongoDB! Latency: {elapsed_latency}s", icon="💾")
                    
                    # Render Report
                    st.caption(f"⚡ **Total Execution Time:** {elapsed_latency} seconds")
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