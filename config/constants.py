import os
from pathlib import Path

# Directory configuration
BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = os.path.join(BASE_DIR, "temp")
STATEMENTS_FOLDER = os.path.join(BASE_DIR, "statements")
CSV_PATH = os.path.join(TEMP_DIR, "data.csv")

# Document AI configuration
PROJECT_ID = "gen-lang-client-0299904904"
LOCATION = "us"
PROCESSOR_ID = "bf2685d686b2d8db"

# Output configuration
OUTPUT_CSV_PATH = os.path.join(BASE_DIR, "all_bank_transactions_final.csv")

# Model configuration
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY2")

# Ensure temp directory exists
os.makedirs(TEMP_DIR, exist_ok=True)