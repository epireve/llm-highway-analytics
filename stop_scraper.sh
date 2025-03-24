#!/bin/bash

if [ -f scraper.pid ]; then
    pid=$(cat scraper.pid)
    if ps -p $pid > /dev/null; then
        echo "Stopping image scraper (PID: $pid)..."
        kill $pid
        rm scraper.pid
        echo "Image scraper stopped"
    else
        echo "Image scraper not running (stale PID file)"
        rm scraper.pid
    fi
else
    echo "No scraper.pid file found"
fi 