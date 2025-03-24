#!/bin/bash

# Stop any existing scraper
if [ -f scraper.pid ]; then
    pid=$(cat scraper.pid)
    if ps -p $pid > /dev/null; then
        echo "Stopping existing scraper (PID: $pid)"
        kill $pid
        sleep 2
    fi
    rm scraper.pid
fi

# Ensure virtual environment exists and is activated
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    /opt/homebrew/bin/python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install or upgrade required packages
echo "Installing/upgrading dependencies..."
pip install -r requirements.txt

# Ensure storage directories exist
mkdir -p storage/images storage/metadata

# Start the scraper in background
echo "Starting image scraper..."
nohup python app/image_scraper.py > scraper_output.log 2>&1 &

# Save PID
echo $! > scraper.pid
echo "Image scraper started with PID: $!"

# Show initial logs
sleep 2
echo "Initial logs:"
tail -n 10 scraper_output.log
echo "For full logs, use: tail -f scraper_output.log" 