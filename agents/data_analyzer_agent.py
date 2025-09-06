from autogen_agentchat.agents import AssistantAgent
from agents.prompts import data_analyzer_prompt
from models import model_client
from config import constants

def get_agent() -> AssistantAgent:
    """
    Initializes and returns the data analyzer agent.

    This agent is responsible for writing and executing Python code to perform
    financial analysis and generate a markdown report, as defined in its system prompt.
    It formats the system prompt with the absolute path to the data CSV.

    Returns:
        (AssistantAgent): An instance of AssistantAgent configured for data analysis.
    """
    
    # Format the system message with the absolute path from constants
    system_message = data_analyzer_prompt.SYSTEM_MESSAGE_TEMPLATE.format(
        CSV_ABS_PATH=constants.CSV_ABS_PATH
    )

    return AssistantAgent(
        name="Data_Analyzer",
        model_client=model_client.get_analyzer_client(),
        system_message=system_message,
        description="Data analysis agent that processes and analyzes CSV data directly from temp/data.csv."
    )