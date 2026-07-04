#!/usr/bin/env sh

set -u

cd "$(dirname "$0")" || exit 1

PYTHON="python3"
if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
fi

warn_if_setup_missing() {
    if command -v ffmpeg >/dev/null 2>&1; then
        printf '[OK] FFmpeg found: %s\n' "$(command -v ffmpeg)"
    else
        printf '[WARN] FFmpeg is not available in PATH.\n'
        printf '       Run ./install.sh to set up FFmpeg support.\n'
    fi

    if [ ! -f "requirements.txt" ]; then
        printf '[WARN] requirements.txt was not found.\n'
        return 0
    fi

    if "$PYTHON" -c "import rich, yt_dlp" >/dev/null 2>&1; then
        printf '[OK] Python dependencies found.\n'
    else
        printf '[WARN] Python dependencies are missing.\n'
        printf '       Run ./install.sh to install them.\n'
    fi
}

warn_if_setup_missing
printf '\n'

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
