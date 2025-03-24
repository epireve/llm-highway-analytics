#!/bin/bash

# Helper script to initialize PocketBase

# Get credentials from .env file
if [ -f .env ]; then
    source <(grep -v '^#' .env | sed -E 's/^(.+)=(.+)$/export \1="\2"/')
else
    echo "Error: .env file not found."
    exit 1
fi

# Make sure PocketBase URL is set
if [ -z "$POCKETBASE_URL" ]; then
    POCKETBASE_URL="http://127.0.0.1:8090"
    echo "Using default PocketBase URL: $POCKETBASE_URL"
fi

# Check if PocketBase is running
if ! curl -s "$POCKETBASE_URL/api/health" > /dev/null; then
    echo "PocketBase is not running. Starting PocketBase..."
    if [ -d "pocketbase" ]; then
        cd pocketbase
        ./pocketbase serve --http="127.0.0.1:8090" &
        POCKETBASE_PID=$!
        cd ..
        echo "PocketBase started with PID: $POCKETBASE_PID"
        # Wait for PocketBase to start
        echo "Waiting for PocketBase to start..."
        sleep 3
    else
        echo "Error: pocketbase directory not found."
        exit 1
    fi
else
    echo "PocketBase is already running."
fi

# Open PocketBase admin URL
echo "Opening PocketBase admin UI in your default browser..."
echo "Please create an admin account with these credentials:"
echo "Email: $POCKETBASE_ADMIN_EMAIL"
echo "Password: $POCKETBASE_ADMIN_PASSWORD"
echo ""
echo "After creating the account, press Enter to continue with collection setup..."

# Open the browser
open "$POCKETBASE_URL/_/" || xdg-open "$POCKETBASE_URL/_/" || echo "Please open $POCKETBASE_URL/_/ in your browser manually."

# Wait for user to press Enter
read -p "Press Enter after creating the admin account..."

# Run the Python script to set up collections
echo "Setting up PocketBase collections..."
.venv/bin/python setup_pocketbase.py

# Check if setup was successful
if [ $? -eq 0 ]; then
    echo "PocketBase initialization completed successfully."
    echo "You can now run the FastAPI application with:"
    echo ".venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001"
else
    echo "Error: PocketBase setup failed."
    echo "Please check the logs and try again."
fi 