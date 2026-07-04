# Flutter Stuff YouTube Downloader

By Farzin

[راهنمای فارسی](README.fa.md)

A modern terminal YouTube downloader built with Python, `yt-dlp`, and Rich. It can download single videos or playlists, lets you choose video quality or audio-only output, shows a live progress UI, and prints the final save folder as a clickable terminal link when supported.

## Features

- Modern Rich-powered CLI with a large `Flutter Stuff` header
- Single video and playlist support
- Video quality picker with best, exact height, and worst options
- Audio-only downloads as MP3, M4A, or original container
- Concurrent playlist downloads
- Live progress table with status, progress bars, speed, size, and ETA
- Pause, resume, and cancel controls during downloads
- Resume-friendly downloads through `yt-dlp`
- Windows and Linux launcher scripts
- Clickable final output folder link in terminals that support hyperlinks

## Requirements

- Python 3.10 or newer
- `ffmpeg` available on your `PATH`
- Internet access for YouTube metadata and downloads

`ffmpeg` is needed for merging video/audio streams and converting audio to MP3 or M4A.

The `install.bat` and `install.sh` scripts install or update Python dependencies and check FFmpeg. If FFmpeg is missing, they try to fetch the FFmpeg source from GitHub with visible progress. If Git is not installed, they download the source ZIP instead. The official FFmpeg GitHub repository contains source code, so the installer will warn you if no runnable `ffmpeg` binary is found after download.

The `run.bat` and `run.sh` launchers do not install anything. They only warn you if FFmpeg or Python dependencies are missing.

## Install

Windows PowerShell:

```powershell
.\install.bat
```

Linux or macOS:

```sh
chmod +x install.sh run.sh
./install.sh
```

## Run

Windows:

```powershell
.\run.bat
```

Linux or macOS:

```sh
./run.sh
```

You can also run the Python file directly:

```sh
python yt_downloader.py
```

Pass a URL and options directly:

```sh
python yt_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" --concurrency 2
```

Audio-only mode:

```sh
python yt_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" --audio
```

Download only one video from a playlist URL:

```sh
python yt_downloader.py "PLAYLIST_OR_VIDEO_URL" --no-playlist
```

## Output Location

By default, downloads are saved under:

```text
Downloads/yt_downloader/video
Downloads/yt_downloader/audio
```

Use `--output PATH` to choose a different base folder:

```sh
python yt_downloader.py "VIDEO_URL" --output ~/Videos
```

The app creates a `yt_downloader` folder inside the selected path unless the selected folder is already named `yt_downloader`.

At the end of a download, the CLI prints the exact save folder. In terminals that support hyperlinks, clicking the folder path opens it.

## Controls

During downloads:

- `p` pauses or resumes
- `c` cancels
- `q` cancels

## Notes

- Playlist downloads can run multiple files at the same time.
- A paused download resumes from the same process once unpaused.
- If a download is canceled or interrupted, running the same command again usually resumes from the partial file when YouTube and the selected format still allow it.
- Some terminals do not support clickable file links. The full folder path is still printed so you can open it manually.
