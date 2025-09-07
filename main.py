import os
import uuid
import asyncio
import glob
from datetime import datetime, timezone

from autogen_agentchat.messages import TextMessage

from config import constants
from services import parser, categorizer_task
from agents import data_analyzer_agent, code_executor_agent
from teams import finance_team

# --- GCP CREDENTIALS SETUP ---
# This block must run before any code that uses Google Cloud services.
gcp_creds_json = os.getenv("GCP_CREDENTIALS_JSON")
if gcp_creds_json:
    os.makedirs(constants.TEMP_DIR, exist_ok=True)
    creds_path = os.path.join(constants.TEMP_DIR, "gcp_creds.json")
    with open(creds_path, "w") as f:
        f.write(gcp_creds_json)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
# --- END GCP CREDENTIALS SETUP ---

async def main():
    """
    Main asynchronous function to run the end-to-end financial analysis workflow.
    """
    # --- 1. PDF Parsing ---
    parser.run_parsing()

    # --- 2. Transaction Categorization ---
    await categorizer_task.run_categorization()

    # --- 3. Report Generation ---
    print("\n🚀 Starting final report generation...")
    
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    work_dir = os.path.join(constants.TEMP_DIR, f"run_{run_id}")
    output_dir = os.path.join(work_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created working directory: {work_dir}")

    analyzer = data_analyzer_agent.get_agent()
    executor = code_executor_agent.get_agent(work_dir)
    
    team = finance_team.create_team(analyzer, executor)
    
    # --- CHOOSE YOUR QUESTION TYPE ---
    # Example for Workflow 1 (Broad Report)
    user_question = "Analyze the CSV and produce a comprehensive report."
    
    # Example for Workflow 2 (Specific Question with Chart)
    # user_question = "What are the top 5 merchants by total spending? Show me a chart."

    task = TextMessage(
        content=(
            "You must read the CSV directly from temp/data.csv using the absolute path provided in your system prompt. "
            "Do not move or copy the file. Follow the Execution Protocol and Python Scripting Guidelines.\\n\\n"
            f"User question: {user_question}\\n\\n"
            f"Per-run output directory (already created): {output_dir}. "
            "Your script should save all files (charts, reports) into the current working directory, "
            f"which is set to: {work_dir}"
        ),
        source="user"
    )

    chat_result = await team.run(task=task)

    # --- START: CORRECTED FINAL OUTPUT LOGIC ---
    print("\n===================================================")
    print(f"🎉 Analysis workflow complete!")
    print(f"Run directory: {work_dir}")

    report_path = os.path.join(work_dir, "report.md")
    if os.path.exists(report_path):
        print(f"Output directory: {output_dir}")
        print("A report was generated and should be in the output directory.")
    else:
        # For specific questions, print the agent's answer and link to any charts.
        print("\n--- Final Answer ---")
        final_answer = "No final answer found."
        if chat_result and chat_result.messages:
            for msg in reversed(chat_result.messages):
                if msg.source == analyzer.name and msg.content:
                    final_answer = msg.content
                    break
        print(final_answer)

        # Check for generated chart files and announce them
        chart_files = glob.glob(os.path.join(work_dir, "*.png"))
        if chart_files:
            print("\n--- Generated Charts ---")
            for chart_file in chart_files:
                print(f"Chart saved at: {chart_file}")
            print("------------------------")

    print("===================================================")
    # --- END: CORRECTED FINAL OUTPUT LOGIC ---


if __name__ == "__main__":
    os.makedirs(constants.TEMP_DIR, exist_ok=True)
    asyncio.run(main())