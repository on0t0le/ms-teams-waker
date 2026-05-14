#!/bin/bash
caffeinate -d &
CAFF_PID=$!
trap "kill $CAFF_PID" EXIT INT TERM

while true; do
    osascript -e '
        try
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
            end tell
        on error
            set frontApp to "Finder"
        end try
        tell application "Microsoft Teams" to activate
        delay 0.2
        tell application "System Events" to keystroke "2" using command down
        delay 0.2
        tell application (frontApp) to activate
    '
    echo "Teams Status Refreshed"
    sleep 300
done
