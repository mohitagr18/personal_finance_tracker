from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.agents import Agent

def create_team(analyzer_agent: Agent, executor_agent: Agent) -> RoundRobinGroupChat:
    """
    Creates and configures the finance analysis team.

    This team consists of a data analyzer agent to write code and a code
    executor agent to run it. The conversation terminates when the analyzer
    agent says "STOP" or after a set number of messages.

    Args:
        analyzer_agent (Agent): The pre-configured data analyzer agent.
        executor_agent (Agent): The pre-configured code executor agent.

    Returns:
        (RoundRobinGroupChat): An instance of the configured agent team.
    """
    
    # Define the condition that ends the conversation.
    termination_condition = TextMentionTermination("STOP") | MaxMessageTermination(max_messages=30)

    return RoundRobinGroupChat(
        participants=[analyzer_agent, executor_agent],
        termination_condition=termination_condition,
        max_turns=20
    )