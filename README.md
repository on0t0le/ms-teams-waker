# MS Teams Waker

A simple application to keep Microsoft Teams active by periodically bringing it to the foreground and simulating a keystroke.

## Features

- Start/stop the Teams waker process with a single click
- Customize the wake frequency (in minutes)
- Activity log to track when Teams is refreshed
- Prevents system sleep while running
- Runs in the background while you work

## Requirements

- Python 3.6 or higher
- macOS (uses macOS-specific commands)
- Microsoft Teams installed

## Usage

1. Run the application:
   ```
   python3 teams_waker_app.py
   ```

2. Set your desired wake frequency (in minutes)

3. Click "Start" to begin the process

4. The application will:
   - Prevent your system from sleeping
   - Periodically activate Microsoft Teams
   - Simulate pressing Command+2 to refresh status

5. Click "Stop" to end the process

## How It Works

The application uses:
- `osascript` to control Microsoft Teams via AppleScript
- `caffeinate` to prevent the system from sleeping
- A background thread to handle the waking process without freezing the UI

## Notes

- The application must be running for the waker to function
- Closing the application window will prompt you to stop the waker if it's running
