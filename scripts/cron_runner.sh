#!/bin/bash
# OMEGA Scheduled Task Runner
# Usage: ./scripts/cron_runner.sh [morning|results|health]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

export PYTHONPATH="$PROJECT_DIR"

TASK=${1:-morning}
LOG_DIR="$PROJECT_DIR/data/logs/scheduler"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/${TASK}_${TIMESTAMP}.log"

echo "[$TIMESTAMP] Starting $TASK task..." | tee -a "$LOG_FILE"

python -m omega.workflows.scheduler "$TASK" 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}
echo "[$TIMESTAMP] Task completed with exit code: $EXIT_CODE" | tee -a "$LOG_FILE"

exit $EXIT_CODE
