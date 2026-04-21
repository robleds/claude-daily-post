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

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "scheduler.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [scheduler] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("scheduler")

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
    log.info("=== Iniciando daily post ===")
    daily_log = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    # Redireciona stdout/stderr do main.py para o log diário
    with open(daily_log, "a", encoding="utf-8") as f:
        result = subprocess.run(
            [PYTHON, MAIN],
            stdout=f,
            stderr=f,
            cwd=str(BASE_DIR),
        )

    if result.returncode != 0:
        log.error(f"main.py encerrou com código {result.returncode} — veja {daily_log}")
    else:
        log.info(f"Daily post concluído com sucesso — log em {daily_log}")


def main():
    s = sched.scheduler(time.time, time.sleep)

    log.info(f"Scheduler iniciado. Diretório: {BASE_DIR}")
    log.info(f"Python: {PYTHON}")

    def schedule_next():
        run_at = _next_run_time()
        run_dt = datetime.fromtimestamp(run_at)
        log.info(f"Próxima execução agendada: {run_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        s.enterabs(run_at, 1, run_and_reschedule)

    def run_and_reschedule():
        _run_post()
        schedule_next()

    schedule_next()
    log.info("Aguardando... (Ctrl+C para parar)")
    try:
        s.run()
    except KeyboardInterrupt:
        log.info("Scheduler encerrado pelo usuário.")


if __name__ == "__main__":
    main()
