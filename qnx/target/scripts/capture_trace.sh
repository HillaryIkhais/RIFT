#!/bin/sh
#
# RIFT-QNX: capture a QNX kernel trace on the target.
#
# Run on the QNX 8.0 target (or via qnxrun/ssh). Produces a .kev trace file
# and normalized traceprinter output for RIFT-QNX host analysis.
#
# Usage: ./capture_trace.sh <duration_seconds> <output_prefix>
#
set -eu

DURATION="${1:-30}"
PREFIX="${2:-rift_trace}"
KEV="${PREFIX}.kev"
TP="${PREFIX}.traceprinter.txt"

echo "[capture_trace] Starting tracelogger for ${DURATION}s -> ${KEV}"

# Start tracelogger capturing thread + communication classes.
tracelogger -n1 -o "${KEV}" -c THREAD,COMMUNICATION &
TRACELOGGER_PID=$!

# Give tracelogger a moment to start.
sleep 1

# The workload/resource manager run here (orchestrated by the harness).
# This script just holds the capture window; the harness launches the RM + clients.
sleep "${DURATION}"

# Stop tracelogger.
kill "${TRACELOGGER_PID}" 2>/dev/null || true
wait "${TRACELOGGER_PID}" 2>/dev/null || true

echo "[capture_trace] Trace captured: ${KEV}"

# Normalize with traceprinter (run after capture, on host or target).
if command -v traceprinter >/dev/null 2>&1; then
    traceprinter "${KEV}" > "${TP}" 2>&1 || true
    echo "[capture_trace] Normalized output: ${TP}"
else
    echo "[capture_trace] traceprinter not found; raw .kev preserved for host parsing."
fi
