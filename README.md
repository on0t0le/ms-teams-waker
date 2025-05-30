# MS Teams Waker

A simple application to keep Microsoft Teams active by periodically bringing it to the foreground and simulating a keystroke.

## Features

- Start/stop the Teams waker process with a single click
- Customize the wake frequency (in minutes)
- Activity log to track when Teams is refreshed
- Prevents system sleep while running
- Runs in the background while you work

## Requirements

- macOS (uses macOS-specific commands)
- Microsoft Teams installed

## Installation

### Option 1: Install from DMG (Recommended)

1. Download the latest release DMG file from the [Releases page](https://github.com/YOUR_USERNAME/msteams_waker/releases)
2. Open the DMG file by double-clicking it
3. Drag the MSTeamsWaker application to your Applications folder
4. Eject the DMG by dragging it to the Trash
5. Launch the application from your Applications folder or Launchpad

### Option 2: Run from Source

If you prefer to run from source code:

1. Ensure you have Python 3.6 or higher installed
2. Install PyQt5: `pip install PyQt5`
3. Run the application: `python3 teams_waker_app.py`

## Usage

1. Launch MS Teams Waker from your Applications folder or by running the script

2. Set your desired wake frequency (in minutes)

3. Click "Start" to begin the process

4. The application will:
   - Prevent your system from sleeping
   - Periodically activate Microsoft Teams
   - Simulate pressing Command+2 to refresh status

5. Click "Stop" to end the process

## Uninstallation

To uninstall MS Teams Waker:

1. Quit the application if it's running
2. Open Finder and navigate to your Applications folder
3. Drag the MSTeamsWaker application to the Trash
4. Empty the Trash to completely remove the application

## How It Works

The application uses:
- `osascript` to control Microsoft Teams via AppleScript
- `caffeinate` to prevent the system from sleeping
- A background thread to handle the waking process without freezing the UI

## Notes

- The application must be running for the waker to function
- Closing the application window will prompt you to stop the waker if it's running
- When first launched, you may need to grant permissions for the app to control Microsoft Teams
- The application is not signed with an Apple developer certificate, so you may need to bypass Gatekeeper security by right-clicking the app and selecting "Open"
