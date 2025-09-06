import os
from dotenv import load_dotenv

# Load environment variables from a .env file in the project root
load_dotenv()

# --- DIRECTORY AND FILE PATHS ---

# We define the project root to build absolute paths, ensuring the script runs from anywhere
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Folder for input PDF statements
STATEMENTS_FOLDER = os.path.join(PROJECT_ROOT, "statements")

# Temporary folder for intermediate and output files
TEMP_DIR = os.path.join(PROJECT_ROOT, "temp")

# Path for the processed CSV data that moves between tasks
CSV_PATH = os.path.join(TEMP_DIR, "data.csv")
CSV_ABS_PATH = os.path.abspath(CSV_PATH)


# --- LARGE LANGUAGE MODEL CONFIGURATION ---

# Decoding parameters for the data analyzer agent
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
LLM_TOP_P = float(os.getenv("LLM_TOP_P", "1"))
LLM_SEED = int(os.getenv("LLM_SEED", "45"))

# API Keys (ensure this is set in your .env file, e.g., OPENAI_API_KEY="sk-...")
# The notebooks used OPENAI_API_KEY2; we are standardizing it to OPENAI_API_KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY2")

# Model identifiers used for different tasks
# Model for the transaction categorization task
CATEGORIZER_MODEL = os.getenv("CATEGORIZER_MODEL", "gpt-4o")
# Model for the final report generation task
ANALYZER_MODEL = os.getenv("ANALYZER_MODEL", "gpt-4o")


# --- GOOGLE CLOUD DOCUMENT AI CONFIGURATION ---

# Your Google Cloud Project ID
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0299904904")

# The location of your Document AI processor ("us" or "eu")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us")

# The ID of your Document AI processor
GCP_PROCESSOR_ID = os.getenv("GCP_PROCESSOR_ID", "bf2685d686b2d8db")

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


# NOTE: For authentication, ensure the 'GOOGLE_APPLICATION_CREDENTIALS' environment
# variable is set to the path of your GCP service account key file.
# You can set this in your .env file or your system's environment.
# Example: GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/credentials.json"