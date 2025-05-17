#!/bin/bash
#
# Resume AI Assistant Setup Script
#
# This script automates the setup process for the Resume AI Assistant application.
# It handles the following tasks:
# - Checking for required dependencies (Python 3.9+, Node.js 14+, uv)
# - Setting up a Python virtual environment
# - Installing Python dependencies via uv
# - Setting up the Next.js frontend
# - Creating a sample .env.local configuration file
#
# Usage: ./setup.sh

set -e

# Color outputs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Utility functions for colored output
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check for required tools and their versions
check_requirements() {
    print_message "Checking requirements..."

    # Check Python version
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed. Please install Python 3.9 or newer."
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
    if [[ $(echo "$PYTHON_VERSION" | cut -d. -f1) -lt 3 ]] || [[ $(echo "$PYTHON_VERSION" | cut -d. -f2) -lt 9 ]]; then
        print_error "Python 3.9+ is required, but you have $PYTHON_VERSION. Please upgrade Python."
        exit 1
    fi

    # Check Node.js version
    if ! command -v node &> /dev/null; then
        print_error "Node.js is required but not installed. Please install Node.js 14 or newer."
        exit 1
    fi

    NODE_VERSION=$(node --version | cut -c 2-)
    if [[ $(echo "$NODE_VERSION" | cut -d. -f1) -lt 14 ]]; then
        print_error "Node.js 14+ is required, but you have $NODE_VERSION. Please upgrade Node.js."
        exit 1
    fi

    # Check for uv
    if ! command -v uv &> /dev/null; then
        print_warning "uv is not installed. Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Add uv to the current path
        export PATH="$HOME/.cargo/bin:$PATH"
    fi

    # Check for curl
    if ! command -v curl &> /dev/null; then
        print_warning "curl is not installed. It may be needed for some operations."
    fi

    print_message "All requirements satisfied!"
}

# Setup Python virtual environment and install dependencies
setup_python_env() {
    print_message "Setting up Python virtual environment..."

    if [ -d ".venv" ]; then
        print_warning "Virtual environment already exists. Skipping creation."
    else
        python3 -m venv .venv
        print_message "Virtual environment created."
    fi

    # Activate virtual environment
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    else
        source .venv/Scripts/activate  # For Windows
    fi

    print_message "Installing Python dependencies..."
    uv sync

    print_message "Python setup complete!"
}

# Setup Next.js frontend and install dependencies
setup_frontend() {
    print_message "Setting up frontend..."

    if [ -d "nextjs-frontend" ]; then
        cd nextjs-frontend
        print_message "Installing Node.js dependencies..."
        npm install
        cd ..
        print_message "Frontend setup complete!"
    else
        print_error "Frontend directory 'nextjs-frontend' not found. Skipping frontend setup."
    fi
}

# Create a sample .env.local file with configuration template
create_env_file() {
    print_message "Creating sample .env file..."

    if [ -f ".env.local" ]; then
        print_warning ".env.local file already exists. Skipping creation."
    else
        cat > ".env.local" << EOF
# Application Configuration
PORT=5001
HOST=0.0.0.0

LOGFIRE_PROJECT=resume-ai-assistant
ENVIRONMENT=development
LOG_LEVEL=INFO
LOGFIRE_ENABLED=false

# Application Configuration
EOF
        print_message ".env.local file created. Please update it with your actual API keys."
    fi
}

# Main setup function that orchestrates the entire setup process
main() {
    print_message "Starting Resume AI Assistant setup..."

    check_requirements
    setup_python_env
    setup_frontend
    create_env_file

    print_message "Setup complete! Here's how to run the application:"
    echo -e "  1. Start the backend server:\n     ${GREEN}source .venv/bin/activate && uv run uvicorn main:app --host 0.0.0.0 --port 5001 --reload${NC}"
    echo -e "  2. Start the frontend (in another terminal):\n     ${GREEN}cd nextjs-frontend && npm run dev${NC}"
    echo -e "  3. Open your browser to ${GREEN}http://localhost:3000${NC}"
    echo -e "\nMake sure to update your ${YELLOW}.env.local${NC} file with your actual API keys!"


}

# Run the main setup function
main

# Exit with success
exit 0
