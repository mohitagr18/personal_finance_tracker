import streamlit as st
import asyncio
import os
import glob
import uuid
import time
from datetime import datetime, timezone

# Import your existing modules
from config import constants
from services import parser, categorizer_task
from agents import data_analyzer_agent, code_executor_agent
from teams import finance_team
from autogen_agentchat.messages import TextMessage

# --- Page Configuration ---
st.set_page_config(page_title="AI Financial Analyst", layout="wide")
st.title("🤖 AI Financial Data Analyst")

st.markdown("""
Welcome! This app uses Google's Document AI to read your PDFs, then unleashes a team of AutoGen agents powered by GPT-4o to answer your questions.
It's a squad of financial robots ready to do your busywork, so you don't have to.
""")

# --- GCP CREDENTIALS SETUP ---
gcp_creds_json = os.getenv("GCP_CREDENTIALS_JSON")
if gcp_creds_json:
    os.makedirs(constants.TEMP_DIR, exist_ok=True)
    creds_path = os.path.join(constants.TEMP_DIR, "gcp_creds.json")
    with open(creds_path, "w") as f:
        f.write(gcp_creds_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
# --- END GCP CREDENTIALS SETUP ---

# --- Sidebar for File Upload and Initial Processing ---
with st.sidebar:
    st.header("Step 1: Process Statements")
    uploaded_files = st.file_uploader(
        "Upload your PDF bank statements here",
        accept_multiple_files=True,
        type="pdf"
    )

    st.info("Note: Initial processing can take 3-5 minutes. This only needs to be done once per session.")

    process_button = st.button("Process Uploaded Statements ✨", disabled=not uploaded_files)

    # Placeholder for real-time status updates and the final persistent log
    status_placeholder = st.container()

    if process_button:
        # When new files are processed, reset the session state
        st.session_state.clear()
        st.session_state.files_processed = False
        
        log_messages = []
        start_time = time.time()
        
        try:
            # Save uploaded files
            log_messages.append("Status: Saving uploaded files...")
            status_placeholder.markdown("\n\n".join(log_messages))
            statements_dir = constants.STATEMENTS_FOLDER
            os.makedirs(statements_dir, exist_ok=True)
            for old_file in glob.glob(os.path.join(statements_dir, "*.pdf")):
                os.remove(old_file)
            for uploaded_file in uploaded_files:
                with open(os.path.join(statements_dir, uploaded_file.name), "wb") as f:
                    f.write(uploaded_file.getbuffer())

            # Run parsing and categorization
            log_messages.append("Status: Parsing PDFs with Document AI...")
            status_placeholder.markdown("\n\n".join(log_messages))
            parser.run_parsing()
            
            if not os.path.exists(constants.CSV_PATH) or os.path.getsize(constants.CSV_PATH) == 0:
                st.error("Parsing failed. No data was extracted.")
            else:
                log_messages.append("Status: Categorizing transactions with AI...")
                status_placeholder.markdown("\n\n".join(log_messages))
                asyncio.run(categorizer_task.run_categorization())
                st.session_state.files_processed = True
                log_messages.append("✅ **Processing Complete!**")
                status_placeholder.markdown("\n\n".join(log_messages))


        except Exception as e:
            st.error(f"An error occurred during processing: {e}")

        end_time = time.time()
        if st.session_state.get("files_processed"):
            st.session_state.processing_time = (end_time - start_time) / 60
            st.session_state.processing_log = log_messages # Save final log
            st.rerun()

    # Display the persistent log messages from session state
    if "processing_log" in st.session_state:
        for message in st.session_state.processing_log:
            status_placeholder.write(message)
        if "processing_time" in st.session_state:
            status_placeholder.success(f"Time taken: {st.session_state.processing_time:.2f} minutes.")


# --- Main Area for Analysis ---
st.header("Step 1: Process Statements")
if not st.session_state.get("files_processed"):
    st.info("⬅️ Please upload your bank statements and click 'Process' in the sidebar to begin.")
else:
    st.success("✅ Statements processed. You can now ask questions.")

st.header("Step 2: Ask a Question")
if st.session_state.get("files_processed"):
    default_question = "Analyze the files and produce a comprehensive markdown report."
    user_question = st.text_input("Enter your question about the statements:", default_question)

    if st.button("Analyze Data 🧠"):
        if not user_question:
            st.warning("Please enter a question.")
        else:
            start_time = time.time()
            with st.spinner("Running data analysis with AI agents..."):
                run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
                work_dir = os.path.join(constants.TEMP_DIR, f"run_{run_id}")
                os.makedirs(work_dir, exist_ok=True)

                analyzer = data_analyzer_agent.get_agent()
                executor = code_executor_agent.get_agent(work_dir)
                team = finance_team.create_team(analyzer, executor)

                task = TextMessage(
                    content=(
                        "You must read the CSV directly from temp/data.csv using the absolute path provided in your system prompt. "
                        f"User question: {user_question}\\n\\n"
                        "Your script should save all files (charts, reports) into the current working directory, "
                        f"which is set to: {work_dir}"
                    ),
                    source="user"
                )
                chat_result = asyncio.run(team.run(task=task))
                end_time = time.time()

                st.session_state.last_run_dir = work_dir
                st.session_state.last_chat_result = chat_result
                st.session_state.last_analysis_time = end_time - start_time
                st.session_state.last_question = user_question
                st.rerun()
else:
    st.info("This step will be enabled after your statements are processed.")

# --- Display Results Section ---
if 'last_run_dir' in st.session_state:
    st.markdown("---")
    st.header("💡 Analysis Results")
    if 'last_question' in st.session_state:
        st.subheader("Your Question:")
        st.markdown(f"> {st.session_state.last_question}")
    work_dir = st.session_state.last_run_dir
    chat_result = st.session_state.last_chat_result
    analysis_time = st.session_state.last_analysis_time

    st.success(f"Analysis completed in {analysis_time / 60:.2f} minutes.")

    report_path = os.path.join(work_dir, "report.md")
    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            st.markdown(f.read(), unsafe_allow_html=True)
    else:
        final_answer = "Could not retrieve a final answer from the agent."
        if chat_result and chat_result.messages:
            for msg in reversed(chat_result.messages):
                if msg.source == "Data_Analyzer" and msg.content:
                    final_answer = msg.content
                    break
        st.markdown(final_answer)

    chart_files = glob.glob(os.path.join(work_dir, "*.png"))
    if chart_files:
        st.subheader("📊 Charts")
        for chart_file in sorted(chart_files):
            st.image(chart_file)

