#!/usr/bin/env bash
# Setup daily scheduling for claude-daily-post at 06:30
# Tries systemd timer first, falls back to cron, then Python scheduler
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON=$(command -v python3 || command -v python)

echo "=== claude-daily-post setup ==="
echo ""

# Option 1: systemd timer (preferred)
if command -v systemctl &>/dev/null && systemctl --user status &>/dev/null 2>&1; then
    echo "Setting up systemd user timer..."
    mkdir -p ~/.config/systemd/user/

    sed "s|/home/user/claude-daily-post|$SCRIPT_DIR|g" \
        "$SCRIPT_DIR/claude-daily-post.service" \
        > ~/.config/systemd/user/claude-daily-post.service

    sed "s|/home/user/claude-daily-post|$SCRIPT_DIR|g" \
        "$SCRIPT_DIR/claude-daily-post.timer" \
        > ~/.config/systemd/user/claude-daily-post.timer

    systemctl --user daemon-reload
    systemctl --user enable --now claude-daily-post.timer
    echo "✓ systemd timer installed and active"
    systemctl --user status claude-daily-post.timer --no-pager || true

# Option 2: cron
elif command -v crontab &>/dev/null; then
    echo "Setting up cron job..."
    LOG_FILE="$SCRIPT_DIR/logs/cron.log"
    mkdir -p "$SCRIPT_DIR/logs"
    CRON_LINE="30 6 * * * cd $SCRIPT_DIR && $PYTHON main.py >> $LOG_FILE 2>&1"
    (crontab -l 2>/dev/null | grep -v "claude-daily-post"; echo "# claude-daily-post"; echo "$CRON_LINE") | crontab -
    echo "✓ Cron job installed"

# Option 3: Python background scheduler
else
    echo "No cron/systemd available — using Python scheduler"
    mkdir -p "$SCRIPT_DIR/logs"
    nohup $PYTHON "$SCRIPT_DIR/scheduler.py" >> "$SCRIPT_DIR/logs/scheduler.log" 2>&1 &
    echo "✓ Python scheduler started (PID: $!)"
fi

echo ""
echo "To run the first post right now:"
echo "  $PYTHON $SCRIPT_DIR/main.py --seed"
echo ""
echo "To test without publishing:"
echo "  $PYTHON $SCRIPT_DIR/main.py --seed --dry-run"
