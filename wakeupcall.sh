#!/bin/bash
caffeinate -d &
CAFF_PID=$!
trap "kill $CAFF_PID" EXIT INT TERM

while true; do
    osascript -e 'tell application "Microsoft Teams" to activate'
    osascript -e 'tell application "System Events" to keystroke "2" using {command down}'
    echo "Teams Status Refreshed"
    sleep 300
done
