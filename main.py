"""NetworkingAgent - Enterprise Autonomous Network Assistant.

Main entrypoint for development and direct execution.
Supports both Interactive Setup Wizard and automated execution.
"""

import sys
from pathlib import Path

# Add 'src' directory to sys.path so the package is always importable directly
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from networking_agent.cli.main import cli_entrypoint  # noqa: E402

if __name__ == "__main__":
    cli_entrypoint()
