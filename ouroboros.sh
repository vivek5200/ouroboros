#!/bin/bash
# Ouroboros CLI Launcher for Unix/Linux/Mac
# Quick shortcut to run the Ouroboros CLI

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the CLI with all arguments passed through
python3 ouroboros_cli.py "$@"
