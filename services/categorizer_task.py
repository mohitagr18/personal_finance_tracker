import re

from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import TextMessage

from config import constants
from agents import categorizer_agent


def _extract_csv_from_text(text: str) -> str | None:
    """
    A helper function to robustly extract CSV content from an agent's response,
    which might be wrapped in markdown code fences.
    """
    if not text:
        return None
    # Prefer the first fenced block if present
    fence_match = re.search(r"```(?:csv)?\\s*(.*?)\\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    # Otherwise, assume the whole text is the CSV if it looks like one
    if "\\n" in text and "," in text:
        return text.strip()
    return None


async def run_categorization():
    """
    Runs the AutoGen agent workflow to categorize transactions.

    This function reads the parsed transaction data, sends it to the categorizer
    agent, and saves the agent's response (the categorized CSV) back to the same file.
    """
    print("\n🚀 Starting transaction categorization...")

    # 1. Read the parsed data from the CSV file
    try:
        with open(constants.CSV_PATH, "r", encoding="utf-8") as f:
            input_csv_text = f.read()
    except FileNotFoundError:
        print(f"❌ Error: Input CSV not found at '{constants.CSV_PATH}'. Please run the parser first.")
        return

    # 2. Get the pre-configured categorizer agent
    agent = categorizer_agent.get_agent()

    # 3. Define the task message, including the CSV data
    task_message = TextMessage(
        content=(
            "The input CSV columns are exactly: bank_name, cardholder, transaction_date, description, amount.\\n"
            "Append a new final column named 'Category', categorize each row using ONLY the allowed categories, "
            "and return ONLY the CSV text with the new column included.\\n\\n"
            f"{input_csv_text}"
        ),
        source="user",
    )

    # 4. Set up a simple, single-agent team
    team = RoundRobinGroupChat(
        participants=[agent],
        termination_condition=TextMentionTermination("STOP") | MaxMessageTermination(max_messages=2),
    )

    # 5. Run the chat and get the result
    chat_result = await team.run(task=task_message)

    # 6. Extract the CSV from the last message from the agent
    final_csv_text = None
    if chat_result and chat_result.messages:
        for msg in reversed(chat_result.messages): # Check latest messages first
            if msg.source == agent.name:
                maybe_csv = _extract_csv_from_text(str(msg.content))
                if maybe_csv:
                    final_csv_text = maybe_csv
                    break
    
    # 7. Overwrite the original CSV with the new categorized data
    if final_csv_text:
        with open(constants.CSV_PATH, "w", encoding="utf-8", newline="") as f:
            f.write(final_csv_text if final_csv_text.endswith("\\n") else final_csv_text + "\\n")
        print(f"✅ Categorization complete. Updated CSV saved to '{constants.CSV_PATH}'")
    else:
        print("❌ Error: Failed to extract categorized CSV from the agent's response.")