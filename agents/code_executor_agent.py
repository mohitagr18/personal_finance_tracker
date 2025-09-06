import os
from autogen_agentchat.agents import CodeExecutorAgent
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from config import constants

def get_agent(work_dir: str) -> CodeExecutorAgent:
    """
    Initializes and returns the code executor agent.

    This agent is responsible for executing Python code provided by other agents
    within a specified, isolated working directory.

    Args:
        work_dir (str): The directory where the code will be executed. A new
                        directory is created for each run to prevent conflicts.

    Returns:
        (CodeExecutorAgent): An instance of CodeExecutorAgent.
    """
    
    # The LocalCommandLineCodeExecutor runs code in a local subprocess.
    # We create a new one for each run, pointed to a unique directory.
    code_executor = LocalCommandLineCodeExecutor(work_dir=work_dir)

    return CodeExecutorAgent(
        name="Python_Code_Executor",
        code_executor=code_executor,
        description="Python code executor agent that runs Python scripts locally."
    )