# GitHub PR blink(1) Notifier

Flash your blink(1) device whenever someone comments on or approves your GitHub pull requests.

Uses the GitHub CLI (`gh`) for authentication - no tokens required.

## Features

- **Blue flash**: New comments on your PRs
- **Green flash**: PR approvals
- **Red flash**: Change requests
- **Yellow flash**: Review comments (including Copilot reviews)
- Monitors all your open PRs across all repositories
- Avoids duplicate notifications
- Configurable polling interval
- Automatic lookback to catch recent activity when starting

## Setup

### 1. Dependencies (PEP 723 - Automatic!)

This script uses **PEP 723 inline metadata** - dependencies are embedded directly in the script! 

**Recommended approach** (with `uv`):

```bash
cd ~/dev/gh2blink
# Dependencies are automatically installed when you run:
uv run github_pr_notifier.py --test
```

**Traditional approach** (manual installation):

```bash
pip install requests>=2.32.5 blink1>=0.4.0
```

**What is PEP 723?** The script now contains this metadata block:

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests>=2.32.5",
#     "blink1>=0.4.0",
# ]
# ///
```

Modern tools like `uv` can read this and automatically manage dependencies!

### 2. Install and Authenticate GitHub CLI

Install the GitHub CLI if you haven't already:

```bash
# Ubuntu/Debian
sudo apt install gh

# macOS
brew install gh

# Or download from https://cli.github.com/
```

Authenticate with GitHub:

```bash
gh auth login
```

Follow the prompts to log in via web browser or with a token.

## Usage

### Test blink(1) Connection

First, make sure your blink(1) device is connected and test it:

**With uv (recommended):**

```bash
uv run github_pr_notifier.py --test
```

**Traditional:**

```bash
python3 github_pr_notifier.py --test
```

This will:

- Check if blink(1) is connected
- Check if gh CLI is authenticated
- Flash red, green, blue, and yellow patterns
- Report any connection issues

### Run the Monitor

Start monitoring your PRs:

**With uv (recommended):**

```bash
uv run github_pr_notifier.py
```

**Traditional:**

```bash
python3 github_pr_notifier.py
```

Options:

- `--interval 30` - Check every 30 seconds (default: 60)
- `--username yourname` - Override auto-detected username
- `--test-mode` - Include your own comments/reviews for testing (normally filtered out)

### Test Mode vs Normal Mode

**Normal Mode** (default):

- Only flashes for comments/reviews from **other people**
- Filters out your own comments to avoid self-notifications
- Recommended for daily use

**Test Mode** (`--test-mode`):

- Includes your own comments/reviews for testing
- Useful when you want to test the device by commenting on your own PRs
- Shows "TEST MODE" message in logs

### Example Output

```
2024-09-07 14:30:15 - INFO - Connected to blink(1) device: 12345
2024-09-07 14:30:15 - INFO - TEST MODE: Will flash for your own comments/reviews
2024-09-07 14:30:15 - INFO - Starting GitHub PR monitor for user: frica
2024-09-07 14:30:15 - INFO - Poll interval: 60 seconds
2024-09-07 14:30:16 - INFO - Checking for PR updates...
2024-09-07 14:30:17 - INFO - Monitoring 3 open PRs
2024-09-07 14:30:18 - INFO - New comment on PR #1000 by reviewer-name
2024-09-07 14:30:18 - INFO - Content: Looks good, just a minor suggestion...
2024-09-07 14:30:18 - INFO - Flashing BLUE for comment from reviewer-name
```

## Running in Background

### Quick Background Run

To run the script in the background and test it immediately:

**With uv (recommended):**

```bash
# Normal mode (filters out your own comments)
nohup uv run github_pr_notifier.py --interval 30 > github_monitor.log 2>&1 &

# Test mode (includes your own comments for testing)
nohup uv run github_pr_notifier.py --interval 30 --test-mode > github_monitor.log 2>&1 &
```

**Traditional:**

```bash
# Normal mode
nohup python3 github_pr_notifier.py --interval 30 > github_monitor.log 2>&1 &

# Test mode
nohup python3 github_pr_notifier.py --interval 30 --test-mode > github_monitor.log 2>&1 &
```

This will:

- Run the script in the background with 30-second intervals
- Log all output to `github_monitor.log`
- Continue running even after you close the terminal

To check if it's running:

```bash
ps aux | grep github_pr_notifier
```

To view the logs:

```bash
tail -f github_monitor.log
```

To stop the background process:

```bash
# Method 1: Kill by script name (recommended)
pkill -f github_pr_notifier.py

# Method 2: Find process ID and kill it
ps aux | grep github_pr_notifier
# Note the PID (process ID) from the output, then:
kill <PID>
```

To verify it's stopped:

```bash
ps aux | grep github_pr_notifier
# Should show no results (except the grep command itself)
```

## Running as Background Service

### Option 1: Using tmux/screen

```bash
# Start a new tmux session
tmux new-session -d -s github-blink1 'cd ~/dev/gh2blink && python3 github_pr_notifier.py'

# Attach to see output
tmux attach -t github-blink1

# Detach: Ctrl+B, then D
```

### Option 2: Create systemd service

Create a systemd service file:

```bash
sudo tee /etc/systemd/system/github-blink1.service > /dev/null << EOF
[Unit]
Description=GitHub PR blink(1) Notifier
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/dev/gh2blink
Environment=GITHUB_TOKEN=$GITHUB_TOKEN
Environment=GITHUB_USERNAME=$GITHUB_USERNAME
ExecStart=/usr/bin/python3 /home/$USER/<my_folder>/github_pr_notifier.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable github-blink1.service
sudo systemctl start github-blink1.service
```

Check status:

```bash
sudo systemctl status github-blink1.service
sudo journalctl -u github-blink1.service -f
```

## Troubleshooting

### blink(1) not found

- Make sure device is plugged in
- Check USB permissions (see blink1-python README)
- Try running with `sudo` temporarily

### GitHub CLI authentication

- Make sure you're logged in: `gh auth status`
- Re-authenticate if needed: `gh auth login`
- The script uses the gh CLI's authenticated sessions

### No notifications

- Check that you have open PRs: `gh search prs --author your-username --state open`
- Verify gh CLI has proper permissions: `gh auth status`
- Check the log file: `github_pr_notifier.log`
- **For testing**: Use `--test-mode` to include your own comments (normally filtered out)
- The script looks back 1 hour when starting to catch recent activity

## Customization

### Different Flash Patterns

Edit the `flash_for_event()` method in the script to customize patterns:

```python
# Example: Longer green flash for approvals
elif event.event_type == 'approved':
    self.blink1.play_pattern('10, #00FF00,0.3,0, #000000,0.1,0')
```

### Monitor Different Events

The script currently monitors:

- Issue comments on PRs
- PR reviews (approved/changes requested/commented)
- Review comments (including automated reviews from tools like Copilot)

You can extend it to monitor:

- New PRs assigned to you
- PR merges
- Specific keywords in comments

## About PEP 723 Inline Script Metadata

This script now uses **PEP 723**, a Python standard that allows embedding dependency information directly in script files. Here's what this means:

### Benefits

- **Self-contained**: Script includes its own dependency information
- **No separate files**: No need for `requirements.txt` or `pyproject.toml`
- **Tool integration**: Modern tools like `uv` automatically install dependencies
- **Portable**: Share the script file and dependencies come with it!

### Running with PEP 723

- **With `uv`**: `uv run github_pr_notifier.py` (automatically installs dependencies in isolated environment)
- **Traditional**: Install dependencies manually, then `python3 github_pr_notifier.py`

### Installing uv (recommended)
If you don't have `uv` installed:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Flash Pattern Reference
| Event Type | Color | Pattern | Description |
|------------|-------|---------|-------------|
| Comment | 🔵 Blue | 3 flashes, 0.3s on/off | New comment on PR |
| Approved | 🟢 Green | 5 flashes, 0.5s on, 0.2s off | PR approved |
| Changes Requested | 🔴 Red | 2 flashes, 1.0s on, 0.5s off | Changes requested |
| Review Comment | 🟡 Yellow | 3 flashes, 0.3s on/off | Review comment (including Copilot) |
