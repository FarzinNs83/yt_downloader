from __future__ import annotations

import argparse
import concurrent.futures
import math
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


Console: Any = None
Live: Any = None
Confirm: Any = None
IntPrompt: Any = None
Prompt: Any = None
Align: Any = None
Group: Any = None
Panel: Any = None
Table: Any = None
Text: Any = None
YoutubeDL: Any = None
box: Any = None
escape: Any = None
console: Any = None


class DownloadCancelled(RuntimeError):
    """Raised from yt-dlp progress hooks when the user cancels."""


@dataclass
class DownloadItem:
    index: int
    title: str
    url: str


@dataclass
class ProgressState:
    title: str
    status: str = "queued"
    downloaded: int = 0
    total: int | None = None
    speed: float | None = None
    eta: int | None = None
    percent: float | None = None
    error: str | None = None
    filename: str | None = None
    updated_at: float = field(default_factory=time.time)


class DownloadController:
    def __init__(self, items: list[DownloadItem]) -> None:
        self.pause_event = threading.Event()
        self.cancel_event = threading.Event()
        self.done_event = threading.Event()
        self.lock = threading.Lock()
        self.states: dict[int, ProgressState] = {
            item.index: ProgressState(title=item.title) for item in items
        }

    @property
    def paused(self) -> bool:
        return self.pause_event.is_set()

    @property
    def cancelled(self) -> bool:
        return self.cancel_event.is_set()

    @property
    def done(self) -> bool:
        return self.done_event.is_set()

    def toggle_pause(self) -> bool:
        if self.pause_event.is_set():
            self.pause_event.clear()
            return False
        self.pause_event.set()
        return True

    def cancel(self) -> None:
        self.cancel_event.set()
        self.pause_event.clear()

    def finish(self) -> None:
        self.done_event.set()
        self.pause_event.clear()

    def wait_if_paused(self) -> None:
        while self.pause_event.is_set() and not self.cancel_event.is_set():
            time.sleep(0.2)
        if self.cancel_event.is_set():
            raise DownloadCancelled("Download cancelled by user.")

    def update(self, index: int, **values: Any) -> None:
        with self.lock:
            state = self.states[index]
            for key, value in values.items():
                setattr(state, key, value)
            state.updated_at = time.time()

    def snapshot(self) -> dict[int, ProgressState]:
        with self.lock:
            return {
                index: ProgressState(**state.__dict__)
                for index, state in self.states.items()
            }


def main() -> int:
    args = parse_args()
    load_dependencies()
    exit_code = 0

    while True:
        try:
            exit_code = run(args)
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled by user.[/yellow]")
            return 130
        except Exception as exc:
            console.print(f"[red]Error:[/red] {exc}")
            exit_code = 1

        if not choose_next_action():
            return exit_code

        args = argparse.Namespace(**vars(args))
        args.url = None


def load_dependencies() -> None:
    global Console, Live, Confirm, IntPrompt, Prompt, Align, Group, Panel, Table
    global Text, YoutubeDL, box, escape, console

    try:
        from rich import box as RichBox
        from rich.align import Align as RichAlign
        from rich.console import Console as RichConsole
        from rich.console import Group as RichGroup
        from rich.live import Live as RichLive
        from rich.markup import escape as RichEscape
        from rich.panel import Panel as RichPanel
        from rich.prompt import Confirm as RichConfirm
        from rich.prompt import IntPrompt as RichIntPrompt
        from rich.prompt import Prompt as RichPrompt
        from rich.table import Table as RichTable
        from rich.text import Text as RichText
        from yt_dlp import YoutubeDL as YtDlp
    except ModuleNotFoundError as exc:
        missing = exc.name or "a required dependency"
        print(f"Missing dependency: {missing}")
        print("Install dependencies with: python -m pip install -r requirements.txt")
        raise SystemExit(1) from exc

    Console = RichConsole
    Live = RichLive
    Confirm = RichConfirm
    IntPrompt = RichIntPrompt
    Prompt = RichPrompt
    Align = RichAlign
    Group = RichGroup
    Panel = RichPanel
    Table = RichTable
    Text = RichText
    YoutubeDL = YtDlp
    box = RichBox
    escape = RichEscape
    console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a YouTube video or playlist with quality selection."
    )
    parser.add_argument("url", nargs="?", help="YouTube video or playlist URL")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "Base download directory. Default: "
            "your Downloads folder under yt_downloader."
        ),
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        type=int,
        default=None,
        help="Number of files to download at the same time for playlists.",
    )
    parser.add_argument(
        "--no-playlist",
        action="store_true",
        help="Download only the video from a playlist URL.",
    )
    parser.add_argument(
        "--audio",
        action="store_true",
        help="Skip the media type prompt and download audio only.",
    )
    return parser.parse_args()


def render_app_header():
    logo = Text(
        "\n".join(
            [
                " _____ _       _   _              ____  _          __  __ ",
                "|  ___| |_   _| |_| |_ ___ _ __  / ___|| |_ _   _ / _|/ _|",
                "| |_  | | | | | __| __/ _ \\ '__| \\___ \\| __| | | | |_| |_ ",
                "|  _| | | |_| | |_| ||  __/ |     ___) | |_| |_| |  _|  _|",
                "|_|   |_|\\__,_|\\__|\\__\\___|_|    |____/ \\__|\\__,_|_| |_|  ",
            ]
        ),
        style="bold cyan",
    )
    byline = Text("By Farzin", style="bold white")
    title = Text("YouTube Downloader", style="white")
    subtitle = Text(
        "Selectable quality, playlist queues, audio export, and live progress",
        style="dim cyan",
    )
    return Panel(
        Align.center(Group(logo, byline, title, subtitle)),
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )


def print_status(title: str, message: str, style: str = "cyan") -> None:
    console.print(
        Panel(
            message,
            title=f"[bold {style}]{title}[/bold {style}]",
            border_style=style,
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )


def saved_location_message(output_dir: Path, lead: str) -> str:
    return f"{lead}\n\nSaved to: {path_link(output_dir)}"


def path_link(path: Path) -> str:
    display_path = escape(str(path))
    try:
        uri = path.resolve().as_uri()
    except ValueError:
        return display_path
    return f"[link={uri}]{display_path}[/link]"


def render_source_panel(items: list[DownloadItem], is_playlist: bool):
    kind = "Playlist" if is_playlist else "Single video"
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()
    table.add_row("Source", kind)
    table.add_row("Items", str(len(items)))
    table.add_row("First", escape(trim(items[0].title, 72)))
    if len(items) > 1:
        table.add_row("Last", escape(trim(items[-1].title, 72)))

    return Panel(
        table,
        title="[bold cyan]Source ready[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 1),
    )


def render_download_summary(
    output_dir: Path,
    download_plan: dict[str, Any],
    concurrency: int,
    item_count: int,
):
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold green", no_wrap=True)
    table.add_column()
    table.add_row("Output", escape(str(output_dir)))
    table.add_row("Mode", download_plan["label"])
    table.add_row("Queue", f"{item_count} {'item' if item_count == 1 else 'items'}")
    table.add_row(
        "Concurrent",
        f"{concurrency} {'file' if concurrency == 1 else 'files'}",
    )

    return Panel(
        table,
        title="[bold green]Ready to download[/bold green]",
        border_style="green",
        box=box.ROUNDED,
        padding=(0, 1),
    )


def print_option_table(
    title: str,
    rows: list[tuple[int, str, str]],
    border_style: str = "cyan",
) -> None:
    table = Table(
        title=title,
        box=box.ROUNDED,
        border_style=border_style,
        header_style=f"bold {border_style}",
        expand=False,
    )
    table.add_column("#", justify="right", style="bold", no_wrap=True)
    table.add_column("Option", style="bold white", no_wrap=True)
    table.add_column("Details", style="dim")

    for number, label, detail in rows:
        table.add_row(str(number), label, detail)

    console.print(table)


def run(args: argparse.Namespace) -> int:
    console.print(render_app_header())

    url = args.url or Prompt.ask("Video or playlist URL").strip()
    if not url:
        raise ValueError("A YouTube URL is required.")

    print_status("Inspecting source", "Reading playlist and video metadata.")
    source_info = extract_source_info(url, no_playlist=args.no_playlist)
    items = build_download_items(source_info, no_playlist=args.no_playlist)
    if not items:
        raise ValueError("No downloadable videos were found.")

    is_playlist = len(items) > 1
    console.print(render_source_panel(items, is_playlist))

    first_video_info = get_first_video_info(items[0].url)
    download_plan = choose_download_plan(args, first_video_info)
    output_dir = prepare_output_dir(args.output, download_plan["kind"])
    concurrency = choose_concurrency(args.concurrency, len(items))

    console.print(
        render_download_summary(output_dir, download_plan, concurrency, len(items))
    )
    if not Confirm.ask("Start download?", default=True):
        print_status("Skipped", "Nothing downloaded.", "yellow")
        return 0

    controller = DownloadController(items)
    input_thread = threading.Thread(
        target=command_listener, args=(controller,), daemon=True
    )
    input_thread.start()

    try:
        failures = download_all(
            items, output_dir, download_plan, concurrency, controller
        )
    finally:
        controller.finish()

    if controller.cancelled:
        print_status(
            "Cancelled",
            saved_location_message(
                output_dir,
                "Download cancelled by user. Partial files may be in this folder.",
            ),
            "yellow",
        )
        return 1
    elif failures:
        print_status(
            "Finished with errors",
            saved_location_message(
                output_dir,
                f"{failures} download(s) failed. Check the progress table above.",
            ),
            "yellow",
        )
        return 1
    else:
        print_status(
            "Complete",
            saved_location_message(output_dir, "All downloads finished."),
            "green",
        )
        return 0


def extract_source_info(url: str, no_playlist: bool) -> dict[str, Any]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "noplaylist": no_playlist,
        "ignoreerrors": True,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise ValueError("Could not read the supplied URL.")
    return info


def build_download_items(info: dict[str, Any], no_playlist: bool) -> list[DownloadItem]:
    if info.get("_type") == "playlist" and not no_playlist:
        items: list[DownloadItem] = []
        for position, entry in enumerate(info.get("entries") or [], start=1):
            if not entry:
                continue
            url = entry_url(entry)
            if not url:
                continue
            title = clean_title(entry.get("title") or f"Video {position}")
            playlist_index = entry.get("playlist_index") or position
            items.append(DownloadItem(index=int(playlist_index), title=title, url=url))
        return items

    return [
        DownloadItem(
            index=1,
            title=clean_title(info.get("title") or "Video"),
            url=entry_url(info) or info.get("original_url") or info.get("webpage_url"),
        )
    ]


def entry_url(entry: dict[str, Any]) -> str | None:
    if entry.get("webpage_url"):
        return entry["webpage_url"]
    if entry.get("url") and str(entry["url"]).startswith(("http://", "https://")):
        return entry["url"]
    video_id = entry.get("id") or entry.get("url")
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return None


def get_first_video_info(url: str) -> dict[str, Any]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "ignoreerrors": False,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise ValueError("Could not inspect the first video.")
    return info


def choose_download_plan(
    args: argparse.Namespace, first_video_info: dict[str, Any]
) -> dict[str, Any]:
    if args.audio:
        audio_format = choose_audio_format()
        return audio_plan(audio_format)

    print_option_table(
        "Download type",
        [
            (1, "Video", "Keep video and audio, with quality selection."),
            (2, "Audio", "Extract audio only as MP3, M4A, or original."),
        ],
    )
    mode = IntPrompt.ask(
        "Choose download type",
        choices=["1", "2"],
        default=1,
    )
    if mode == 2:
        audio_format = choose_audio_format()
        return audio_plan(audio_format)

    return video_plan(first_video_info)


def choose_audio_format() -> str:
    choices = [
        ("MP3", "mp3"),
        ("M4A", "m4a"),
        ("Original container", "original"),
    ]
    print_option_table(
        "Audio format",
        [
            (idx, label, audio_format_detail(value))
            for idx, (label, value) in enumerate(choices, start=1)
        ],
    )

    selected = IntPrompt.ask(
        "Choose audio format",
        choices=[str(idx) for idx in range(1, len(choices) + 1)],
        default=1,
    )
    return choices[selected - 1][1]


def audio_format_detail(value: str) -> str:
    if value == "mp3":
        return "Best compatibility."
    if value == "m4a":
        return "Efficient AAC container."
    return "No conversion after download."


def audio_plan(audio_format: str) -> dict[str, Any]:
    if audio_format == "original":
        return {
            "kind": "audio",
            "label": "Audio only, original container",
            "format": "bestaudio/best",
            "postprocessors": [],
        }

    return {
        "kind": "audio",
        "label": f"Audio only, {audio_format}",
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "0",
            }
        ],
    }


def video_plan(first_video_info: dict[str, Any]) -> dict[str, Any]:
    available_heights = sorted(
        {
            int(fmt["height"])
            for fmt in first_video_info.get("formats") or []
            if fmt.get("height") and fmt.get("vcodec") != "none"
        },
        reverse=True,
    )
    choices = build_quality_choices(available_heights)
    print_option_table(
        "Video quality",
        [
            (idx, label, quality_detail(value))
            for idx, (label, value) in enumerate(choices, start=1)
        ],
    )

    selected = IntPrompt.ask(
        "Choose quality",
        default=1,
        choices=[str(idx) for idx in range(1, len(choices) + 1)],
    )
    label, value = choices[selected - 1]
    return {
        "kind": "video",
        "label": label,
        "format": video_format_selector(value),
        "postprocessors": [],
    }


def quality_detail(value: str) -> str:
    if value == "best":
        return "Highest quality yt-dlp can combine."
    if value == "worst":
        return "Smallest fallback format."
    return "Prefer exact height, then fall back below it."


def build_quality_choices(available_heights: list[int]) -> list[tuple[str, str]]:
    choices: list[tuple[str, str]] = [("Best available", "best")]
    for height in available_heights:
        choices.append((f"{height}p", str(height)))
    choices.append(("Worst available", "worst"))
    return choices


def video_format_selector(value: str) -> str:
    if value == "best":
        return "bestvideo*+bestaudio/best"
    if value == "worst":
        return "worst/worstvideo*+worstaudio"
    return (
        f"best[height={value}]/"
        f"bestvideo*[height={value}]+bestaudio/"
        f"best[height<={value}]/"
        f"bestvideo*[height<={value}]+bestaudio"
    )


def prepare_output_dir(base_output: str | None, kind: str) -> Path:
    root = default_download_root() if base_output is None else Path(base_output)
    root = root.expanduser().resolve()
    if root.name.lower() != "yt_downloader":
        root = root / "yt_downloader"

    audio_dir = root / "audio"
    video_dir = root / "video"
    audio_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)

    if kind == "audio":
        return audio_dir
    if kind == "video":
        return video_dir
    raise ValueError(f"Unknown download type: {kind}")


def default_download_root() -> Path:
    return Path.home() / "Downloads" / "yt_downloader"


def choose_next_action() -> bool:
    if not sys.stdin.isatty():
        return False

    console.print()
    print_option_table(
        "Next action",
        [
            (1, "Try again", "Start another download with the same settings."),
            (2, "Exit", "Close the downloader."),
        ],
        "magenta",
    )
    action = IntPrompt.ask(
        "Choose next action",
        choices=["1", "2"],
        default=2,
    )
    return action == 1


def choose_concurrency(requested: int | None, item_count: int) -> int:
    if requested is not None:
        return max(1, min(requested, item_count))
    max_concurrent = max(1, item_count)
    print_option_table(
        "Concurrent downloads",
        [
            (
                value,
                f"{value} {'file' if value == 1 else 'files'}",
                concurrency_detail(value, max_concurrent),
            )
            for value in range(1, max_concurrent + 1)
        ],
        "green",
    )
    return IntPrompt.ask(
        "Choose concurrent downloads",
        default=1,
        choices=[str(value) for value in range(1, max_concurrent + 1)],
    )


def concurrency_detail(value: int, max_concurrent: int) -> str:
    if value == 1:
        return "Most reliable for slow or unstable networks."
    if value == max_concurrent:
        return "Fastest queue processing."
    return "Balanced throughput."


def command_listener(controller: DownloadController) -> None:
    if not sys.stdin.isatty():
        return

    try:
        import msvcrt
    except ImportError:
        listen_for_posix_commands(controller)
        return

    while not controller.cancelled and not controller.done:
        if not msvcrt.kbhit():
            time.sleep(0.05)
            continue

        command = msvcrt.getwch().lower()
        if handle_download_command(command, controller):
            return


def listen_for_posix_commands(controller: DownloadController) -> None:
    try:
        import select
        import termios
        import tty
    except ImportError:
        return

    file_descriptor = sys.stdin.fileno()
    old_settings = termios.tcgetattr(file_descriptor)
    try:
        tty.setcbreak(file_descriptor)
        while not controller.cancelled and not controller.done:
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if not ready:
                continue
            command = sys.stdin.read(1).lower()
            if handle_download_command(command, controller):
                return
    finally:
        termios.tcsetattr(file_descriptor, termios.TCSADRAIN, old_settings)


def handle_download_command(command: str, controller: DownloadController) -> bool:
    if command in {"\r", "\n"}:
        return False
    if command == "p":
        paused = controller.toggle_pause()
        console.print(
            "[yellow]Paused.[/yellow]" if paused else "[green]Resumed.[/green]"
        )
        return False
    if command in {"c", "q"}:
        controller.cancel()
        console.print("[yellow]Cancelling...[/yellow]")
        return True
    return False


def download_all(
    items: list[DownloadItem],
    output_dir: Path,
    plan: dict[str, Any],
    concurrency: int,
    controller: DownloadController,
) -> int:
    failures = 0
    with Live(
        render_progress_view(controller),
        console=console,
        refresh_per_second=4,
        transient=False,
    ) as live:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {
                executor.submit(download_one, item, output_dir, plan, controller): item
                for item in items
            }
            while futures:
                done, _ = concurrent.futures.wait(
                    futures,
                    timeout=0.25,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                live.update(render_progress_view(controller))

                if controller.cancelled:
                    for future in futures:
                        if future.cancel():
                            item = futures[future]
                            controller.update(item.index, status="cancelled")

                for future in done:
                    item = futures.pop(future)
                    try:
                        future.result()
                    except DownloadCancelled:
                        controller.update(item.index, status="cancelled")
                    except concurrent.futures.CancelledError:
                        controller.update(item.index, status="cancelled")
                    except Exception as exc:
                        failures += 1
                        controller.update(
                            item.index,
                            status="failed",
                            error=short_error(exc),
                        )

                if controller.cancelled and all(f.done() for f in futures):
                    break

            live.update(render_progress_view(controller))
    return failures


def download_one(
    item: DownloadItem,
    output_dir: Path,
    plan: dict[str, Any],
    controller: DownloadController,
) -> None:
    if controller.cancelled:
        raise DownloadCancelled("Download cancelled before start.")

    controller.wait_if_paused()
    controller.update(item.index, status="starting")

    progress_hook = make_progress_hook(item.index, controller)
    opts = {
        "format": plan["format"],
        "outtmpl": str(output_dir / "%(title).180B [%(id)s].%(ext)s"),
        "continuedl": True,
        "overwrites": False,
        "noplaylist": True,
        "ignoreerrors": False,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "progress_hooks": [progress_hook],
        "postprocessors": plan["postprocessors"],
        "merge_output_format": "mp4",
        "windowsfilenames": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
    }

    try:
        with YoutubeDL(opts) as ydl:
            ydl.download([item.url])
    except DownloadCancelled:
        controller.update(item.index, status="cancelled")
        raise
    except KeyboardInterrupt as exc:
        controller.update(item.index, status="cancelled")
        raise DownloadCancelled("Download cancelled by user.") from exc

    if not controller.cancelled:
        controller.update(item.index, status="finished", percent=100.0)


def make_progress_hook(index: int, controller: DownloadController):
    def hook(data: dict[str, Any]) -> None:
        controller.wait_if_paused()
        status = data.get("status")
        if status == "downloading":
            downloaded = int(data.get("downloaded_bytes") or 0)
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            total = int(total) if total else None
            percent = (downloaded / total * 100) if total else None
            controller.update(
                index,
                status="downloading",
                downloaded=downloaded,
                total=total,
                speed=data.get("speed"),
                eta=data.get("eta"),
                percent=percent,
                filename=data.get("filename"),
            )
        elif status == "finished":
            controller.update(
                index,
                status="processing",
                downloaded=int(data.get("downloaded_bytes") or 0),
                total=int(data.get("total_bytes") or data.get("downloaded_bytes") or 0),
                percent=100.0,
                filename=data.get("filename"),
            )

    return hook


def render_progress_view(controller: DownloadController):
    footer = Text(
        "Controls: p pause/resume   c cancel   q cancel",
        style="dim",
    )
    return Panel(
        Group(render_progress_table(controller), footer),
        title=f"[bold]{status_title(controller)}[/bold]",
        border_style=status_border_style(controller),
        box=box.ROUNDED,
        padding=(0, 1),
    )


def render_progress_table(controller: DownloadController) -> Table:
    table = Table(
        expand=True,
        box=box.SIMPLE,
        border_style="bright_black",
        header_style="bold cyan",
        pad_edge=False,
    )
    table.add_column("#", justify="right", no_wrap=True, width=3)
    table.add_column("Title", overflow="fold", ratio=1, min_width=28)
    table.add_column("State", no_wrap=True, width=11)
    table.add_column("Progress", no_wrap=True, width=22)

    for index, state in sorted(controller.snapshot().items()):
        table.add_row(
            str(index),
            format_title_cell(state),
            state_label(state),
            format_progress_cell(state.percent),
        )
    return table


def status_title(controller: DownloadController) -> str:
    if controller.cancelled:
        return "Cancelling downloads"
    if controller.paused:
        return "Downloads paused"
    return "Downloads"


def status_border_style(controller: DownloadController) -> str:
    if controller.cancelled:
        return "yellow"
    if controller.paused:
        return "yellow"
    return "cyan"


def state_label(state: ProgressState) -> str:
    if state.status == "failed":
        return "[bold red]FAILED[/bold red]"
    if state.status == "finished":
        return "[bold green]DONE[/bold green]"
    if state.status == "cancelled":
        return "[bold yellow]CANCELLED[/bold yellow]"
    if state.status == "processing":
        return "[cyan]PROCESSING[/cyan]"
    if state.status == "downloading":
        return "[blue]DOWNLOADING[/blue]"
    if state.status == "starting":
        return "[cyan]STARTING[/cyan]"
    if state.status == "queued":
        return "[dim]QUEUED[/dim]"
    return state.status.upper()


def format_progress_cell(value: float | None) -> str:
    width = 12
    if value is None or math.isnan(value):
        return "[dim]------------[/dim]   -"
    bounded = max(0.0, min(100.0, value))
    filled = int(round(width * bounded / 100.0))
    bar = f"[cyan]{'#' * filled}[/cyan][dim]{'-' * (width - filled)}[/dim]"
    return f"{bar} {bounded:5.1f}%"


def format_title_cell(state: ProgressState) -> str:
    title = escape(trim(state.title, 64))
    detail = format_progress_detail(state)
    if detail == "-":
        return title
    if state.status == "failed" and state.error:
        return f"{title}\n{detail}"
    return f"{title}\n[dim]{detail}[/dim]"


def format_progress_detail(state: ProgressState) -> str:
    if state.status == "failed" and state.error:
        return f"[red]{escape(trim(state.error, 56))}[/red]"

    details = [format_compact_size_pair(state.downloaded, state.total)]
    speed = format_compact_speed(state.speed)
    eta = format_eta(state.eta)
    if speed != "-":
        details.append(speed)
    if eta != "-":
        details.append(eta)
    return "  ".join(details)


def format_compact_size_pair(downloaded: int, total: int | None) -> str:
    if total:
        downloaded_text = format_bytes(downloaded)
        total_text = format_bytes(total)
        downloaded_parts = downloaded_text.split(" ", 1)
        total_parts = total_text.split(" ", 1)
        if (
            len(downloaded_parts) == 2
            and len(total_parts) == 2
            and downloaded_parts[1] == total_parts[1]
        ):
            return f"{downloaded_parts[0]}/{total_parts[0]}{total_parts[1]}"
        return f"{compact_unit_text(downloaded_text)}/{compact_unit_text(total_text)}"
    if downloaded:
        return compact_unit_text(format_bytes(downloaded))
    return "-"


def format_compact_speed(speed: float | None) -> str:
    if not speed:
        return "-"
    return f"{compact_unit_text(format_bytes(speed))}/s"


def compact_unit_text(value: str) -> str:
    return value.replace(" ", "")


def format_percent(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "-"
    return f"{value:5.1f}%"


def format_size_pair(downloaded: int, total: int | None) -> str:
    if total:
        return f"{format_bytes(downloaded)} / {format_bytes(total)}"
    if downloaded:
        return format_bytes(downloaded)
    return "-"


def format_speed(speed: float | None) -> str:
    if not speed:
        return "-"
    return f"{format_bytes(speed)}/s"


def format_eta(eta: int | None) -> str:
    if eta is None:
        return "-"
    minutes, seconds = divmod(int(eta), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:d}:{seconds:02d}"


def format_bytes(value: float | int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = float(value)
    for unit in units:
        if abs(size) < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{size:.0f} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TiB"


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    return title or "Untitled"


def trim(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 1] + "..."


def short_error(exc: Exception) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    return re.sub(r"\s+", " ", text)


if __name__ == "__main__":
    raise SystemExit(main())
