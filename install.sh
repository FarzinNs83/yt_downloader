#!/usr/bin/env sh

set -u

FFMPEG_REPO="https://github.com/FFmpeg/FFmpeg.git"
FFMPEG_ZIP_URL="https://github.com/FFmpeg/FFmpeg/archive/refs/heads/master.zip"
FFMPEG_DIR="${HOME}/.flutter_stuff/ffmpeg-source"

ensure_python_dependencies() {
    printf 'Checking Python dependencies and updates...\n'
    if [ ! -f "requirements.txt" ]; then
        printf '[WARN] requirements.txt was not found.\n'
        return 1
    fi

    printf '[INFO] Running dependency update check:\n'
    printf '       %s\n' "$PYTHON -m pip install --upgrade -r requirements.txt"
    if ! "$PYTHON" -m pip install --upgrade -r requirements.txt; then
        printf '[WARN] Python dependency installation/update failed.\n'
        printf '       Check your Python and pip installation, then run this installer again.\n'
        return 1
    fi
    printf '[OK] Python dependencies are installed and checked for updates.\n'
}

ensure_ffmpeg() {
    printf 'Checking FFmpeg...\n'
    if command -v ffmpeg >/dev/null 2>&1; then
        printf '[OK] FFmpeg already available: %s\n' "$(command -v ffmpeg)"
        ffmpeg -version 2>/dev/null | sed -n '1p'
        update_existing_ffmpeg_source
        return 0
    fi

    printf '[WARN] FFmpeg is not available in PATH.\n'
    printf '       The downloader needs FFmpeg for merging video/audio and converting audio.\n\n'

    if [ -d "${FFMPEG_DIR}/.git" ]; then
        printf '[INFO] FFmpeg source already exists. Checking for source updates...\n'
        if ! git -C "$FFMPEG_DIR" pull --ff-only; then
            printf '[WARN] Could not update FFmpeg source with Git. Continuing with existing source.\n'
        fi
    elif [ -f "${FFMPEG_DIR}/configure" ]; then
        printf '[INFO] FFmpeg source already exists, but it is not a Git checkout.\n'
        printf '[INFO] Downloading the latest source ZIP to refresh it.\n'
        download_ffmpeg_source || return 1
    else
        mkdir -p "$(dirname "$FFMPEG_DIR")" || return 1
        if command -v git >/dev/null 2>&1; then
            printf '[INFO] Cloning FFmpeg source from:\n'
            printf '       %s\n' "$FFMPEG_REPO"
            printf '[INFO] Download progress will be shown below.\n'
            if ! git clone --progress "$FFMPEG_REPO" "$FFMPEG_DIR"; then
                printf '[WARN] FFmpeg clone failed. Trying source ZIP download instead.\n'
                download_ffmpeg_source || return 1
            fi
        else
            printf '[WARN] Git is not installed or not available in PATH.\n'
            printf '[INFO] Downloading FFmpeg source ZIP instead.\n'
            download_ffmpeg_source || return 1
        fi
    fi

    ffmpeg_bin_dir="$(find_ffmpeg_binary_dir)"
    if [ -n "$ffmpeg_bin_dir" ]; then
        add_to_user_path "$ffmpeg_bin_dir"
        if command -v ffmpeg >/dev/null 2>&1; then
            printf '[OK] FFmpeg has been installed and is available in PATH.\n'
        else
            printf '[WARN] FFmpeg path was added, but this shell cannot find it yet.\n'
            printf '       Open a new terminal and run ./run.sh again.\n'
        fi
    else
        add_to_user_path "$FFMPEG_DIR"
        printf '[WARN] The GitHub FFmpeg repository contains source code, not a prebuilt ffmpeg binary.\n'
        printf '       The source folder was downloaded and added to your PATH as requested:\n'
        printf '       %s\n' "$FFMPEG_DIR"
        printf '       FFmpeg is still not runnable until you build it or install a binary package.\n'
    fi
}

update_existing_ffmpeg_source() {
    if [ -d "${FFMPEG_DIR}/.git" ]; then
        printf '[INFO] Existing FFmpeg source checkout found. Checking for source updates...\n'
        if git -C "$FFMPEG_DIR" pull --ff-only; then
            printf '[OK] FFmpeg source checkout is up to date or updated.\n'
        else
            printf '[WARN] Could not check FFmpeg source updates.\n'
        fi
    else
        printf '[INFO] FFmpeg is already satisfied. No managed source checkout was found to update.\n'
    fi
}

download_ffmpeg_source() {
    tmp_zip="${TMPDIR:-/tmp}/ffmpeg-source.zip"
    extract_dir="${TMPDIR:-/tmp}/ffmpeg-source-$$"

    printf '[INFO] Downloading FFmpeg source from:\n'
    printf '       %s\n' "$FFMPEG_ZIP_URL"
    printf '[INFO] Download progress will be shown below.\n'

    rm -rf "$extract_dir"
    mkdir -p "$extract_dir" || return 1

    if command -v curl >/dev/null 2>&1; then
        curl -L --progress-bar -o "$tmp_zip" "$FFMPEG_ZIP_URL" || return 1
    elif command -v wget >/dev/null 2>&1; then
        wget --progress=bar:force -O "$tmp_zip" "$FFMPEG_ZIP_URL" || return 1
    else
        printf '[WARN] Neither curl nor wget is installed. Cannot download FFmpeg source.\n'
        return 1
    fi

    printf '[INFO] Extracting FFmpeg source...\n'
    if command -v unzip >/dev/null 2>&1; then
        unzip -q "$tmp_zip" -d "$extract_dir" || return 1
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$tmp_zip" "$extract_dir" || return 1
    elif command -v python >/dev/null 2>&1; then
        python -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$tmp_zip" "$extract_dir" || return 1
    else
        printf '[WARN] unzip or Python is required to extract the downloaded source ZIP.\n'
        return 1
    fi

    source_dir="$(find "$extract_dir" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
    if [ -z "$source_dir" ]; then
        printf '[WARN] Downloaded archive did not contain a source folder.\n'
        return 1
    fi

    rm -rf "$FFMPEG_DIR"
    mv "$source_dir" "$FFMPEG_DIR" || return 1
    rm -f "$tmp_zip"
    rm -rf "$extract_dir"
    printf '[OK] FFmpeg source downloaded and extracted.\n'
}

find_ffmpeg_binary_dir() {
    if [ ! -d "$FFMPEG_DIR" ]; then
        return 0
    fi
    find "$FFMPEG_DIR" -type f -name ffmpeg -perm -111 -print 2>/dev/null | while IFS= read -r ffmpeg_path; do
        dirname "$ffmpeg_path"
        break
    done
}

add_to_user_path() {
    path_to_add="$1"
    profile_file="${HOME}/.profile"

    printf '[INFO] Adding to PATH permanently:\n'
    printf '       %s\n' "$path_to_add"

    case ":$PATH:" in
        *":$path_to_add:"*) ;;
        *) PATH="${PATH}:$path_to_add"; export PATH ;;
    esac

    mkdir -p "$(dirname "$profile_file")" || return 1
    if [ -f "$profile_file" ] && grep -F "$path_to_add" "$profile_file" >/dev/null 2>&1; then
        printf '[OK] Profile already contains this folder.\n'
    else
        {
            printf '\n# Flutter Stuff YouTube Downloader FFmpeg path\n'
            printf 'export PATH="$PATH:%s"\n' "$path_to_add"
        } >> "$profile_file"
        printf '[OK] Added to %s for future shells.\n' "$profile_file"
    fi
}

cd "$(dirname "$0")" || exit 1

PYTHON="python3"
if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
fi

printf 'Flutter Stuff YouTube Downloader installer\n\n'

ensure_python_dependencies || exit 1
printf '\n'

ensure_ffmpeg || exit 1
printf '\n'

printf '[OK] Install/update check finished.\n'
