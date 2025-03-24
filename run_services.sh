#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the absolute path of the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"
PYTHON_PATH="$VENV_PATH/bin/python"

# Make sure we have a clean start
echo -e "${BLUE}Stopping any existing PocketBase or Uvicorn processes...${NC}"
pkill -f pocketbase
pkill -f uvicorn
sleep 2

# Start PocketBase in the background
echo -e "${BLUE}Starting PocketBase server...${NC}"
cd "$PROJECT_ROOT/pocketbase" && ./pocketbase serve --http="127.0.0.1:8090" &
POCKETBASE_PID=$!

# Wait for PocketBase to start - increased wait time
echo -e "${BLUE}Waiting for PocketBase to initialize...${NC}"
sleep 5
if ps -p $POCKETBASE_PID > /dev/null; then
    echo -e "${GREEN}PocketBase started with PID: $POCKETBASE_PID${NC}"
else
    echo -e "${RED}PocketBase failed to start!${NC}"
    exit 1
fi

# Check if PocketBase is running and reachable
echo -e "${BLUE}Testing PocketBase connection...${NC}"
if curl -s "http://127.0.0.1:8090/api/health" | grep -q "ok"; then
    echo -e "${GREEN}PocketBase is reachable!${NC}"
else
    echo -e "${YELLOW}PocketBase health check failed - continuing anyway...${NC}"
fi

echo -e "${YELLOW}IMPORTANT: You need to create an admin account in PocketBase.${NC}"
echo -e "${YELLOW}Visit http://127.0.0.1:8090/_/ and follow the setup instructions.${NC}"
echo -e "${YELLOW}After creating your admin account, update the .env file with your credentials:${NC}"
echo -e "${YELLOW}POCKETBASE_ADMIN_EMAIL=your-email@example.com${NC}"
echo -e "${YELLOW}POCKETBASE_ADMIN_PASSWORD=your-password${NC}"
echo ""

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
cd "$PROJECT_ROOT"
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
    echo -e "${GREEN}Virtual environment activated${NC}"
else
    echo -e "${YELLOW}Virtual environment not found at $VENV_PATH - creating new one${NC}"
    /opt/homebrew/bin/python3 -m venv "$VENV_PATH"
    source "$VENV_PATH/bin/activate"
    pip install -r requirements.txt || pip install uvicorn fastapi httpx loguru aiofiles beautifulsoup4 apscheduler pocketbase python-dotenv jinja2
    echo -e "${GREEN}Virtual environment created and activated${NC}"
fi

# Display current .env values
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${BLUE}Current environment settings:${NC}"
    cat "$PROJECT_ROOT/.env"
    echo ""
else
    echo -e "${YELLOW}No .env file found. Using default values.${NC}"
fi

# Start FastAPI application with debugging enabled
echo -e "${BLUE}Starting FastAPI application...${NC}"
echo -e "${YELLOW}Once running, visit http://localhost:8001 to view the dashboard${NC}"
PYTHONPATH="$PROJECT_ROOT" LOGURU_LEVEL=DEBUG python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Handle CTRL+C to stop both services
trap 'kill $POCKETBASE_PID; exit' INT 