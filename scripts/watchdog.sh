#!/bin/bash
# watchdog.sh — Vigila los procesos de descarga y los reinicia si se caen.
# Diseñado para correr toda la noche sin supervisión.

BASE_DIR="/home/apolo/A/CorupCol"
SCRIPTS_DIR="$BASE_DIR/scripts"
LOGS_DIR="$BASE_DIR/logs"
PIDS_DIR="$BASE_DIR/logs/pids"
WATCHDOG_LOG="$LOGS_DIR/watchdog.log"

mkdir -p "$PIDS_DIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WATCHDOG] $1" | tee -a "$WATCHDOG_LOG"
}

# Todos los datasets a descargar
DATASETS=(
    "secop_integrado"
    "secop2_contratos"
    "secop2_procesos"
    "secop2_bpin"
    "sgr_ingresos"
    "sgr_giros"
    "chip_presupuesto"
    "cgr_funcionarios"
)

is_done() {
    local name=$1
    local progress="$BASE_DIR/data/$name/progress.json"
    if [ -f "$progress" ]; then
        python3 -c "import json; d=json.load(open('$progress')); print('yes' if d.get('done') else 'no')" 2>/dev/null
    else
        echo "no"
    fi
}

get_pid() {
    local name=$1
    local pidfile="$PIDS_DIR/$name.pid"
    if [ -f "$pidfile" ]; then
        cat "$pidfile"
    fi
}

is_alive() {
    local pid=$1
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    return 1
}

start_dataset() {
    local name=$1
    local logfile="$LOGS_DIR/${name}.log"
    local pidfile="$PIDS_DIR/$name.pid"

    log "Iniciando descarga: $name"
    nohup python3 "$SCRIPTS_DIR/download.py" "$name" >> "$logfile" 2>&1 &
    local pid=$!
    echo "$pid" > "$pidfile"
    log "$name iniciado con PID=$pid"
}

log "============================================"
log "WATCHDOG INICIADO — modo nocturno"
log "Datasets a vigilar: ${DATASETS[*]}"
log "============================================"

CHECK_INTERVAL=60  # revisar cada 60 segundos

while true; do
    all_done=true

    for name in "${DATASETS[@]}"; do
        done=$(is_done "$name")

        if [ "$done" = "yes" ]; then
            log "$name: COMPLETO ✓ — skipping"
            continue
        fi

        all_done=false
        pid=$(get_pid "$name")

        if is_alive "$pid"; then
            # Proceso vivo — mostrar progreso del log
            last_line=$(tail -1 "$LOGS_DIR/${name}.log" 2>/dev/null)
            log "$name [PID=$pid]: $last_line"
        else
            # Proceso muerto — reiniciar
            log "⚠ $name está CAÍDO (PID=$pid). Reiniciando en 5s..."
            sleep 5
            start_dataset "$name"
            sleep 3
        fi
    done

    if $all_done; then
        log "============================================"
        log "TODOS LOS DATASETS DESCARGADOS. WATCHDOG TERMINANDO."
        log "============================================"
        break
    fi

    sleep "$CHECK_INTERVAL"
done
