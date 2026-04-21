#!/usr/bin/env bash
# Setup daily scheduling for claude-daily-post at 06:30
# Tries systemd timer first, falls back to cron, then Python scheduler
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON=$(command -v python3 || command -v python)

echo "=== claude-daily-post setup ==="
echo ""

# Verifica se .env existe
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "⚠️  ATENÇÃO: arquivo .env não encontrado em $SCRIPT_DIR/.env"
    echo "   Copie e preencha: cp $SCRIPT_DIR/.env.example $SCRIPT_DIR/.env"
    echo "   O agendamento será instalado, mas as publicações falharão sem as credenciais."
    echo ""
fi

mkdir -p "$SCRIPT_DIR/logs"

# Option 1: systemd timer (preferred)
if command -v systemctl &>/dev/null && systemctl --user status &>/dev/null 2>&1; then
    echo "Instalando systemd user timer..."
    mkdir -p ~/.config/systemd/user/

    sed "s|/home/user/claude-daily-post|$SCRIPT_DIR|g" \
        "$SCRIPT_DIR/claude-daily-post.service" \
        > ~/.config/systemd/user/claude-daily-post.service

    sed "s|/home/user/claude-daily-post|$SCRIPT_DIR|g" \
        "$SCRIPT_DIR/claude-daily-post.timer" \
        > ~/.config/systemd/user/claude-daily-post.timer

    systemctl --user daemon-reload
    systemctl --user enable --now claude-daily-post.timer
    echo "✓ systemd timer instalado e ativo (06:30 diário)"
    systemctl --user status claude-daily-post.timer --no-pager || true

# Option 2: cron
elif command -v crontab &>/dev/null; then
    echo "Instalando cron job..."
    LOG_FILE="$SCRIPT_DIR/logs/cron.log"
    # Usa caminho absoluto do Python e executa no diretório correto
    CRON_LINE="30 6 * * * cd \"$SCRIPT_DIR\" && \"$PYTHON\" \"$SCRIPT_DIR/main.py\" >> \"$LOG_FILE\" 2>&1"
    (crontab -l 2>/dev/null | grep -v "claude-daily-post"; echo "# claude-daily-post"; echo "$CRON_LINE") | crontab -
    echo "✓ Cron job instalado (06:30 diário)"
    echo "  Log em: $LOG_FILE"

# Option 3: Python background scheduler
else
    echo "Sem cron/systemd — usando Python scheduler em background"
    nohup "$PYTHON" "$SCRIPT_DIR/scheduler.py" >> "$SCRIPT_DIR/logs/scheduler.log" 2>&1 &
    SCHED_PID=$!
    echo "$SCHED_PID" > "$SCRIPT_DIR/logs/scheduler.pid"
    echo "✓ Python scheduler iniciado (PID: $SCHED_PID)"
    echo "  Log em: $SCRIPT_DIR/logs/scheduler.log"
fi

echo ""
echo "============================================"
echo "  PRÓXIMOS PASSOS:"
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "  1. Crie o .env: cp $SCRIPT_DIR/.env.example $SCRIPT_DIR/.env"
    echo "  2. Preencha as credenciais no .env"
    echo "  3. Teste: $PYTHON $SCRIPT_DIR/main.py --seed --dry-run"
else
    echo "  1. Teste sem publicar: $PYTHON $SCRIPT_DIR/main.py --seed --dry-run"
    echo "  2. Primeira execução real: $PYTHON $SCRIPT_DIR/main.py --seed"
fi
echo ""
echo "  Logs diários em: $SCRIPT_DIR/logs/YYYY-MM-DD.log"
echo "============================================"
