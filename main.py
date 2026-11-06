"""NetworkingAgent - Enterprise Autonomous Network Assistant.

Main entrypoint for development and direct execution.
Supports both Interactive Setup Wizard and automated execution.
"""

from networking_agent.cli.main import cli_entrypoint

if __name__ == "__main__":
    cli_entrypoint()
