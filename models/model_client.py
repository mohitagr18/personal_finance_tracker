from autogen_ext.models.openai import OpenAIChatCompletionClient
from config import constants

def get_categorizer_client():
    """
    Initializes and returns the OpenAI client configured for the categorization task.

    This client is optimized for classification and uses the designated categorizer model.

    Returns:
        (OpenAIChatCompletionClient): An instance of the OpenAI client.
    
    Raises:
        ValueError: If the OpenAI API key is not configured in the environment.
    """
    if not constants.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found. Please set it in your .env file.")

    return OpenAIChatCompletionClient(
        model=constants.CATEGORIZER_MODEL,
        api_key=constants.OPENAI_API_KEY,
    )

def get_analyzer_client():
    """
    Initializes and returns the OpenAI client for the analysis and report generation task.

    This client uses specific decoding parameters (temperature, top_p, seed) for more 
    deterministic and consistent outputs, as defined in the generator notebook.

    Returns:
        (OpenAIChatCompletionClient): An instance of the OpenAI client.

    Raises:
        ValueError: If the OpenAI API key is not configured in the environment.
    """
    if not constants.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found. Please set it in your .env file.")

    return OpenAIChatCompletionClient(
        model=constants.ANALYZER_MODEL,
        api_key=constants.OPENAI_API_KEY,
        temperature=constants.LLM_TEMPERATURE,
        top_p=constants.LLM_TOP_P,
        seed=constants.LLM_SEED,
    )