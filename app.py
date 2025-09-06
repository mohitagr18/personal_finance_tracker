import os
import json
from config import constants

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

import os
import uuid
import asyncio
from datetime import datetime, timezone

from autogen_agentchat.messages import TextMessage

from config import constants
from services import parser, categorizer_task
from agents import data_analyzer_agent, code_executor_agent
from teams import finance_team

async def main():
    """
    Main asynchronous function to run the end-to-end financial analysis workflow.
    """
    # --- 1. PDF Parsing ---
    # Process all PDF files in the 'statements' folder and create a single CSV
    # in the 'temp' directory.
    parser.run_parsing()

    # --- 2. Transaction Categorization ---
    # Run the categorizer agent to add a 'Category' column to the CSV file.
    await categorizer_task.run_categorization()

    # --- 3. Report Generation ---
    print("\n🚀 Starting final report generation...")

    # Create a unique, timestamped directory for this run's output.
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    work_dir = os.path.join(constants.TEMP_DIR, f"run_{run_id}")
    output_dir = os.path.join(work_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created working directory: {work_dir}")

    # Get the pre-configured agents. The executor needs the unique work_dir.
    analyzer = data_analyzer_agent.get_agent()
    executor = code_executor_agent.get_agent(work_dir)
    
    # Create the team
    team = finance_team.create_team(analyzer, executor)
    
    # Define the user's question for the analysis.
    user_question = (
        "Analyze the CSV and produce a comprehensive markdown report with monthly spend trends by cardholder, "
        "by Category, and top merchants inferred from the description field, including at least two charts."
    )

    # Compose the initial task message for the team.
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

    # Run the team chat.
    chat_result = await team.run(task=task)

    print("\n===================================================")
    print(f"🎉 Analysis workflow complete!")
    print(f"Run directory: {work_dir}")
    print(f"Output directory: {output_dir}")
    print("If a report was generated, it should be in the output directory.")
    print("===================================================")


if __name__ == "__main__":
    # Ensure the temp directory exists before starting
    os.makedirs(constants.TEMP_DIR, exist_ok=True)
    
    # Run the main asynchronous event loop
    asyncio.run(main())