#!/bin/bash

echo "🔧 Setting up GitHub PR blink(1) Notifier..."

# Check if we're in the right directory
if [[ ! -f "github_pr_notifier.py" ]]; then
    echo "❌ Please run this script from the gh2blink directory"
    exit 1
fi

# Check if uv is available (recommended) or fallback to manual installation
echo "📦 Checking Python package manager..."
if command -v uv &> /dev/null; then
    echo "✅ uv found! Dependencies will be managed automatically via PEP 723."
    echo "💡 The script now uses inline metadata - no separate requirements file needed!"
else
    echo "⚠️  uv not found. You can:"
    echo "   1. Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "   2. Or manually install: pip3 install requests>=2.32.5 blink1>=0.4.0"
    echo "   3. The script uses PEP 723 inline metadata for dependencies"
fi

# Check for GitHub token
if [[ -z "$GITHUB_TOKEN" ]]; then
    echo "⚠️  GITHUB_TOKEN environment variable not set"
    echo "Please create a GitHub personal access token and add to your shell profile:"
    echo ""
    echo "1. Go to: https://github.com/settings/tokens"
    echo "2. Create new token (classic) with 'repo' scope"
    echo "3. Add to ~/.bashrc or ~/.zshrc:"
    echo "   export GITHUB_TOKEN=\"your_token_here\""
    echo "   export GITHUB_USERNAME=\"your_github_username\""
    echo ""
else
    echo "✅ GITHUB_TOKEN found"
fi

# Check for GitHub username
if [[ -z "$GITHUB_USERNAME" ]]; then
    echo "⚠️  GITHUB_USERNAME environment variable not set"
    echo "Add to ~/.bashrc or ~/.zshrc:"
    echo "   export GITHUB_USERNAME=\"your_github_username\""
    echo ""
else
    echo "✅ GITHUB_USERNAME found: $GITHUB_USERNAME"
fi

# Test blink(1) connection
echo "🔍 Testing blink(1) connection..."
if command -v uv &> /dev/null; then
    uv run github_pr_notifier.py --test
else
    python3 github_pr_notifier.py --test
fi

if [[ $? -eq 0 ]]; then
    echo ""
    echo "🎉 Setup complete! You can now run:"
    if command -v uv &> /dev/null; then
        echo "   uv run github_pr_notifier.py       # Recommended (auto-manages dependencies)"
        echo "   python3 github_pr_notifier.py      # Traditional approach"
        echo ""
        echo "💡 To run in background:"
        echo "   nohup uv run github_pr_notifier.py > github_monitor.log 2>&1 &"
    else
        echo "   python3 github_pr_notifier.py"
        echo ""
        echo "💡 To run in background:"
        echo "   tmux new-session -d -s github-blink1 'cd ~/dev/gh2blink && python3 github_pr_notifier.py'"
    fi
    echo ""
else
    echo "❌ blink(1) test failed. Please check your device connection."
fi
