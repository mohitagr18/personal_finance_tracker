import re

from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import TextMessage

from config import constants
from agents import categorizer_agent

async def run_categorization():
    """
    Runs the AutoGen agent workflow to categorize transactions.
    """
    print("🚀 Starting transaction categorization...")

    try:
        with open(constants.CSV_PATH, "r", encoding="utf-8") as f:
            input_csv_text = f.read()
    except FileNotFoundError:
        print(f"❌ Error: Input CSV not found at '{constants.CSV_PATH}'. Please run the parser first.")
        return

    agent = categorizer_agent.get_agent()

    task_message = TextMessage(
        content=(
            "The input CSV columns are exactly: bank_name, cardholder, transaction_date, description, amount.\\n"
            "Append a new final column named 'Category', categorize each row using ONLY the allowed categories, "
            "and return ONLY the CSV text with the new column included.\\n\\n"
            f"{input_csv_text}"
        ),
        source="user",
    )

    team = RoundRobinGroupChat(
        participants=[agent],
        termination_condition=TextMentionTermination("STOP") | MaxMessageTermination(max_messages=2),
    )

    chat_result = await team.run(task=task_message)

    final_csv_text = None
    if chat_result and chat_result.messages:
        for msg in reversed(chat_result.messages):
            if msg.source == agent.name and msg.content:
                content_str = str(msg.content).strip()
                
                # --- START: ROBUST EXTRACTION LOGIC ---
                # Find the start of the CSV content by looking for the known header.
                header = "bank_name,cardholder,transaction_date,description,amount,Category"
                header_index = content_str.find(header)
                
                if header_index != -1:
                    # Take everything from the header to the end of the string.
                    csv_block = content_str[header_index:]
                    
                    # Clean the trailing "STOP" keyword if it exists.
                    if csv_block.endswith("STOP"):
                        csv_block = csv_block[:-4].strip()
                    
                    final_csv_text = csv_block
                    break  # Exit the loop once we've found and processed the CSV block.
                # --- END: ROBUST EXTRACTION LOGIC ---

    if final_csv_text:
        with open(constants.CSV_PATH, "w", encoding="utf-8", newline="") as f:
            f.write(final_csv_text if final_csv_text.endswith("\\n") else final_csv_text + "\\n")
        print(f"✅ Categorization complete. Updated CSV saved to '{constants.CSV_PATH}'")
    else:
        print("❌ Error: Failed to extract categorized CSV from the agent's response.")