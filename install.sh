#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_SCRIPT="$SCRIPT_DIR/rob-wrapper.sh"
INSTALL_DIR="/usr/local/bin"

detect_shell() {
    if [ -n "$ZSH_VERSION" ]; then
        echo "zsh"
    elif [ -n "$BASH_VERSION" ]; then
        echo "bash"
    else
        echo "unknown"
    fi
}

get_rc_file() {
    local shell=$(detect_shell)
    if [ "$shell" = "zsh" ]; then
        echo "$HOME/.zshrc"
    elif [ "$shell" = "bash" ]; then
        echo "$HOME/.bashrc"
    else
        echo ""
    fi
}

# Check if we're being called with --install-only (internal use)
if [ "$1" = "--install-only" ]; then
    # This is the sudo part - just do the installation
    SHARE_DIR="/usr/local/share/rob"
    echo "Creating share directory: $SHARE_DIR"
    mkdir -p "$SHARE_DIR"

    echo "Copying rob.py to $SHARE_DIR..."
    if ! cp "$SCRIPT_DIR/rob.py" "$SHARE_DIR/"; then
        echo "Failed to copy rob.py to $SHARE_DIR"
        exit 1
    fi

    echo "Installing rob wrapper to ${INSTALL_DIR}..."
    if ! cp "$WRAPPER_SCRIPT" "$INSTALL_DIR/rob"; then
        echo "Failed to copy rob wrapper to $INSTALL_DIR"
        exit 1
    fi

    chmod +x "$INSTALL_DIR/rob"

    # Create config directory for user
    USER_CONFIG_DIR="$HOME/.config/rob"
    if [ ! -d "$USER_CONFIG_DIR" ]; then
        mkdir -p "$USER_CONFIG_DIR"
        echo "Created config directory: $USER_CONFIG_DIR"
    fi

    RC_FILE=$(get_rc_file)
    if [ -n "$RC_FILE" ]; then
        if ! grep -q "$INSTALL_DIR" "$RC_FILE"; then
            echo "export PATH=\$PATH:$INSTALL_DIR" >> "$RC_FILE"
            echo "Added $INSTALL_DIR to PATH in $RC_FILE"
        fi
    else
        echo "Couldn't detect shell. Please add $INSTALL_DIR to your PATH manually."
    fi

    echo "Installation completed successfully."
    exit 0
fi

# Check if wrapper script exists
if [ ! -f "$WRAPPER_SCRIPT" ]; then
    echo "Error: Wrapper script not found at $WRAPPER_SCRIPT"
    exit 1
fi

# Check if we're running as root
if [ "$EUID" -eq 0 ]; then
    echo "Error: Do not run this script as root. Run it as your regular user."
    exit 1
fi

# Create a virtual environment for rob
VENV_DIR="$HOME/.local/share/rob-venv"
echo "Creating virtual environment at $VENV_DIR..."
if ! python3 -m venv "$VENV_DIR"; then
    echo "Failed to create virtual environment."
    exit 1
fi

# Install dependencies in the virtual environment
echo "Installing Python dependencies..."
if ! "$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"; then
    echo "Failed to install Python dependencies."
    exit 1
fi

# Verify dependencies are installed
echo "Verifying Python dependencies..."
if ! "$VENV_DIR/bin/python" -c "import colorama, click, robin_stocks" 2>/dev/null; then
    echo "Failed to verify Python dependencies."
    exit 1
fi

echo "Dependencies installed successfully. Now installing rob system-wide..."

# Now run the install-only part with sudo
if ! sudo "$0" --install-only; then
    echo "Installation failed."
    exit 1
fi

echo "Installation complete! You can now use 'rob' immediately."
echo "Run 'rob --help' for instructions."