#!/bin/bash
# Wrapper script for rob CLI tool

# Use the virtual environment created during installation
VENV_DIR="$HOME/.local/share/rob-venv"
VENV_PYTHON="$VENV_DIR/bin/python"

# Check if the virtual environment exists
if [[ ! -f "$VENV_PYTHON" ]]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Please reinstall rob: ./install.sh"
    exit 1
fi

# Look for the installed script in /usr/local/share/rob
SCRIPT_PATH="/usr/local/share/rob/rob.py"

# Check if the script exists
if [[ ! -f "$SCRIPT_PATH" ]]; then
    echo "Error: Could not find rob.py script at $SCRIPT_PATH"
    echo "Make sure rob is properly installed"
    exit 1
fi

# Run the Python script with the virtual environment
cd "/usr/local/share/rob" && "$VENV_PYTHON" rob.py "$@"
