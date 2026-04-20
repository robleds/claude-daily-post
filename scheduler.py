#!/usr/bin/env python3
"""
Fallback scheduler using Python's built-in sched module.
Runs main.py every day at 06:30.
Use this if cron is not available.
"""

import sched
import time
import subprocess
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [scheduler] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scheduler")

BASE_DIR = Path(__file__).parent
PYTHON = sys.executable
MAIN = str(BASE_DIR / "main.py")
TARGET_HOUR = 6
TARGET_MINUTE = 30


def _next_run_time() -> float:
    now = datetime.now()
    target = now.replace(hour=TARGET_HOUR, minute=TARGET_MINUTE, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target.timestamp()


def _run_post():
    log.info("=== Running daily post ===")
    result = subprocess.run([PYTHON, MAIN], capture_output=False)
    if result.returncode != 0:
        log.error(f"main.py exited with code {result.returncode}")
    else:
        log.info("Daily post completed successfully")


def main():
    s = sched.scheduler(time.time, time.sleep)

    def schedule_next():
        run_at = _next_run_time()
        run_dt = datetime.fromtimestamp(run_at)
        log.info(f"Next run scheduled for: {run_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        s.enterabs(run_at, 1, run_and_reschedule)

    def run_and_reschedule():
        _run_post()
        schedule_next()

    schedule_next()
    log.info("Scheduler running. Press Ctrl+C to stop.")
    s.run()


if __name__ == "__main__":
    main()
