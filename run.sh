#!/usr/bin/env sh

set -u

cd "$(dirname "$0")" || exit 1

PYTHON="python3"
if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
fi

if [ "$#" -eq 0 ]; then
    "$PYTHON" yt_downloader.py
    exit_code=$?
    printf '\n'
    if [ -t 0 ]; then
        printf 'Press Enter to exit...'
        read -r _
    fi
else
    "$PYTHON" yt_downloader.py "$@"
    exit_code=$?
fi

exit "$exit_code"
