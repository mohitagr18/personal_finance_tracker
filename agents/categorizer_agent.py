from autogen_agentchat.agents import AssistantAgent
from agents.prompts import categorizer_prompt
from models import model_client

def get_agent() -> AssistantAgent:
    """
    Initializes and returns the categorizer agent.

    This agent is responsible for taking raw transaction data and appending a 'Category'
    column based on the rules defined in its system prompt.

    Returns:
        (AssistantAgent): An instance of AssistantAgent configured for the categorization task.
    """
    return AssistantAgent(
        name="categorizer",
        model_client=model_client.get_categorizer_client(),
        system_message=categorizer_prompt.SYSTEM_MESSAGE,
        reflect_on_tool_use=False,
    )