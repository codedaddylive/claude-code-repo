#!/usr/bin/env bash
# Retries the full integration test every 30 minutes for up to 9 hours.
# Runs immediately on start, then waits.
# Exits 0 (and stops looping) when Claude vision test passes.
# Usage: ANTHROPIC_API_KEY=sk-... bash tests/wait_and_test.sh

set -euo pipefail

MAX_HOURS=9
INTERVAL=1800   # 30 minutes
DEADLINE=$(( $(date +%s) + MAX_HOURS * 3600 ))
ATTEMPT=0

cd "$(dirname "$0")/.."

run_test() {
    ATTEMPT=$(( ATTEMPT + 1 ))
    echo ""
    echo "=================================================="
    echo "Attempt $ATTEMPT at $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=================================================="
    python3 tests/integration_test.py
}

while true; do
    if run_test; then
        echo ""
        echo "All tests PASSED on attempt $ATTEMPT."
        exit 0
    fi

    NOW=$(date +%s)
    if (( NOW >= DEADLINE )); then
        echo ""
        echo "9-hour window expired after $ATTEMPT attempt(s). Exiting."
        exit 1
    fi

    REMAINING=$(( (DEADLINE - NOW) / 60 ))
    echo ""
    echo "Waiting 30 minutes before retry. (~${REMAINING}m remaining in window)"
    sleep $INTERVAL
done
