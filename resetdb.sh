#!/bin/bash
# Make sure you're in the project directory
cd "$(dirname "$0")"

# Activate virtual environment (if using one)
source .venv/bin/activate

# Run the reset script with auto-confirmation
python resetdb.py --yes

echo "DB reset complete!"