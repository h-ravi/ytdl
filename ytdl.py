#!/usr/bin/env python3
"""
ytdl.py — Terminal Video Downloader
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
aria2c se fast download + ffmpeg se merge
Rich library se beautiful terminal UI

Install (Termux):
    pkg install aria2 ffmpeg python
    pip install yt-dlp rich

Install (Linux/Windows):
    pip install yt-dlp rich
    sudo apt install aria2 ffmpeg   # Linux
    winget install aria2.aria2 Gyan.FFmpeg  # Windows

Usage:
    python ytdl.py <URL>
    python ytdl.py <URL> -o ~/Downloads
    python ytdl.py <URL> -r 720p
    python ytdl.py <URL> --audio-only
"""

import os
import re
import sys
import shutil
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Dict

import yt_dlp

# ── Rich imports ─────────────────────────────────────────────────────────────
from rich.console import Console
from rich.table import Table, Column
from rich.panel import Panel
from rich.text import Text
from rich.prompt import IntPrompt
from rich.progress import (
    Progress, BarColumn, TextColumn,
    TransferSpeedColumn, TimeRemainingColumn,
    SpinnerColumn, TaskProgressColumn,
)
from rich.status import Status
from rich.rule import Rule
from rich import box

# ── Single global Console — sab output yahan se ─────────────────────────────
console = Console(highlight=False)


# ════════════════════════════════════════════════════════════════════════════
#  Dependency Check
# ════════════════════════════════════════════════════════════════════════════

def check_dependencies() -> None:
    """aria2c aur ffmpeg installed hain ya nahi verify karo."""
    missing = [t for t in ("aria2c", "ffmpeg") if shutil.which(t) is None]
    if not missing:
        return

    console.print(
        Panel(
            "\n".join([
                f"[red]Missing: [bold]{', '.join(missing)}[/]\n",
                "[dim]Termux mein install karo:[/]",
                f"[yellow]  pkg install {' '.join(missing)}[/]\n",
                "[dim]Linux (apt) mein:[/]",
                f"[yellow]  sudo apt install {' '.join(missing)}[/]\n",
                "[dim]Windows (winget) mein:[/]",
                f"[yellow]  winget install aria2.aria2 Gyan.FFmpeg[/]",
            ]),
            title="[red bold]Dependencies Missing[/]",
            border_style="red",
            padding=(1, 2),
        )
    )
    sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
#  App Header
# ════════════════════════════════════════════════════════════════════════════

def print_banner() -> None:
    console.print()
    console.print(Rule(
        title="[bold cyan] ▶  ytdl [/]  [dim]aria2c + ffmpeg downloader[/]",
        style="cyan",
        characters="─",
    ))
    console.print()


# ════════════════════════════════════════════════════════════════════════════
#  yt-dlp Core Logic  (pure functions — koi UI nahi)
# ════════════════════════════════════════════════════════════════════════════

def get_resolution_label(f: dict) -> Optional[str]:
    h = f.get("height")
    if h:
        return f"{h}p"
    res = f.get("resolution")
    if res and "x" in res:
        try:
            return f"{res.split('x')[1]}p"
        except Exception:
            pass
    return None


def is_video(f: dict) -> bool:
    vcodec = f.get("vcodec")
    return bool(vcodec and vcodec != "none")


def is_audio_only(f: dict) -> bool:
    vcodec = f.get("vcodec")
    acodec = f.get("acodec")
    return (not vcodec or vcodec == "none") and bool(acodec and acodec != "none")


def get_delivery(f: dict) -> str:
    return "segmented" if f.get("fragments") else "direct"


def extract_urls(f: dict) -> List[str]:
    if f.get("fragments"):
        urls, base = [], f.get("fragment_base_url") or ""
        for frag in f["fragments"]:
            if frag.get("url"):
                urls.append(frag["url"])
            elif frag.get("path") and base:
                urls.append(base + frag["path"])
        return urls
    return [f["url"]] if f.get("url") else []


def get_headers(f: dict) -> Dict[str, str]:
    allowed = {"User-Agent", "Referer", "Cookie", "Authorization"}
    return {k: v for k, v in f.get("http_headers", {}).items() if k in allowed}


def score_video(f: dict) -> tuple:
    ext    = f.get("ext", "")
    vcodec = f.get("vcodec", "")
    return (
        2 if ext == "mp4" else (1 if ext == "webm" else 0),
        1 if ("avc" in vcodec or "h264" in vcodec) else 0,
        f.get("tbr") or 0,
        f.get("filesize") or 0,
    )


def score_audio(f: dict) -> tuple:
    ext = f.get("ext", "")
    return (
        1 if ext in ("m4a", "aac") else 0,
        f.get("abr") or 0,
        f.get("filesize") or 0,
    )


def human_size(n: Optional[int]) -> str:
    if not n:
        return "—"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def safe_filename(title: str) -> str:
    safe = "".join(c for c in title if c.isalnum() or c in " ._-()[]").strip()
    return safe[:100] or "video"


def extract_info(url: str) -> dict:
    opts = {
        "quiet":         True,
        "skip_download": True,
        "no_warnings":   True,
        "noplaylist":    True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def build_formats(info: dict) -> List[dict]:
    """
    Saare formats process karo — har resolution ke liye
    best video + best audio select karo.
    """
    res_map: Dict[str, list] = {}
    audio_pool: list = []

    for f in info.get("formats", []):
        url = (f.get("url") or "").lower()
        if (".m3u8" in url or ".mpd" in url) and not f.get("fragments"):
            continue
        if is_video(f):
            res = get_resolution_label(f)
            if res:
                res_map.setdefault(res, []).append(f)
        elif is_audio_only(f):
            audio_pool.append(f)

    best_audio = None
    if audio_pool:
        audio_pool.sort(key=score_audio, reverse=True)
        best_audio = audio_pool[0]

    result = []
    for res, candidates in res_map.items():
        candidates.sort(key=score_video, reverse=True)
        vid = candidates[0]

        has_embedded = bool(vid.get("acodec") and vid.get("acodec") != "none")
        needs_merge  = not has_embedded and best_audio is not None

        result.append({
            "resolution":  res,
            "container":   vid.get("ext", "mp4"),
            "delivery":    get_delivery(vid),
            "codec":       vid.get("vcodec", ""),
            "filesize":    vid.get("filesize"),
            "video_fmt":   vid,
            "audio_fmt":   best_audio if needs_merge else None,
            "needs_merge": needs_merge,
        })

    result.sort(
        key=lambda x: int(x["resolution"].replace("p", "")),
        reverse=True
    )

    if best_audio:
        result.append({
            "resolution":  "Audio",
            "container":   best_audio.get("ext", "m4a"),
            "delivery":    get_delivery(best_audio),
            "codec":       best_audio.get("acodec", ""),
            "filesize":    best_audio.get("filesize"),
            "video_fmt":   None,
            "audio_fmt":   best_audio,
            "needs_merge": False,
        })

    return result


# ════════════════════════════════════════════════════════════════════════════
#  Rich UI — Video Info Panel
# ════════════════════════════════════════════════════════════════════════════

def print_video_info(info: dict, fmt_count: int) -> None:
    """Video title, duration aur format count ek clean panel mein dikhao."""
    title    = info.get("title", "Unknown")
    duration = info.get("duration") or 0
    mins, sec = divmod(int(duration), 60)
    hrs,  mins = divmod(mins, 60)
    dur_str = f"{hrs}h {mins}m {sec}s" if hrs else f"{mins}m {sec}s"

    t = Text()
    t.append("  Title     ", style="dim")
    t.append(title[:72] + ("…" if len(title) > 72 else ""), style="bold white")
    t.append("\n  Duration  ", style="dim")
    t.append(dur_str, style="cyan")
    t.append("\n  Formats   ", style="dim")
    t.append(str(fmt_count), style="bold cyan")
    t.append(" available", style="dim")

    console.print(Panel(t, border_style="cyan", padding=(0, 1), expand=False))
    console.print()


# ════════════════════════════════════════════════════════════════════════════
#  Rich UI — Format Selection Table
# ════════════════════════════════════════════════════════════════════════════

def print_formats_table(formats: List[dict]) -> None:
    """
    Compact format table — phone/Termux screen (~55 chars) ke liye.

    Key design decisions:
      - Ext + Delivery ek hi "Format" column mein: "mp4 · dir"
        ext green hai, separator dim hai, delivery type colored hai
      - Bitrate column nahi — space bachata hai, user ko zarurat nahi
      - min_width values minimum rakhi hain
      - SIMPLE_HEAVY box ROUNDED se thoda kam wide hota hai
    """
    table = Table(
        Column("#",       style="bold cyan",  justify="right",  width=3),
        Column("Res",     style="bold white", justify="center", min_width=5),
        # Format column = ext + delivery type ek saath, e.g. "mp4 · dir"
        Column("Format",                      justify="left",   min_width=9),
        Column("Size",    style="white",      justify="right",  min_width=7),
        Column("Audio",                       justify="center", min_width=6),

        box=box.SIMPLE_HEAVY,
        border_style="cyan",
        header_style="bold cyan",
        show_lines=False,
        padding=(0, 1),
        expand=False,
        title="[bold cyan]Formats[/]",
        title_justify="left",
    )

    for i, fmt in enumerate(formats):
        is_audio_row = (fmt["resolution"] == "Audio")

        # ── "mp4 · dir" ya "m4a · seg" — ek Text object mein teen parts ──
        # Yeh trick hai: Text object mein alag alag styled segments append
        # karte hain, lekin woh ek hi cell mein dikhte hain.
        # Isse "mp4" green rahega aur "seg" yellow — bina alag column ke.
        ext      = fmt["container"]
        delivery = fmt["delivery"]
        fmt_text = Text()
        fmt_text.append(ext, style="green")
        fmt_text.append(" · ", style="dim")
        if delivery == "segmented":
            fmt_text.append("seg", style="yellow")
        else:
            fmt_text.append("dir", style="cyan")

        # Audio status — compact labels
        if is_audio_row:
            audio_text = Text("only🎵", style="magenta")
        elif fmt["needs_merge"]:
            audio_text = Text("+mrg", style="yellow")
        else:
            audio_text = Text("embd", style="green")

        res_text = (
            Text("Audio", style="bold magenta")
            if is_audio_row
            else Text(fmt["resolution"], style="bold white")
        )

        table.add_row(
            str(i),
            res_text,
            fmt_text,                          # combined "mp4 · dir"
            human_size(fmt.get("filesize")),
            audio_text,
        )

    console.print(table)
    console.print()


def choose_format(formats: List[dict], resolution: Optional[str]) -> Optional[dict]:
    """User se format choose karao ya -r argument se auto-select karo."""

    if resolution:
        for fmt in formats:
            if fmt["resolution"].lower() == resolution.lower():
                console.print(
                    f"  [dim]Auto-selected:[/] [green]{resolution}[/] "
                    f"[dim]({fmt['container']}, {fmt['delivery']})[/]\n"
                )
                return fmt
        console.print(f"  [yellow]⚠  '{resolution}' nahi mila.[/] Table se choose karo:\n")

    print_formats_table(formats)

    while True:
        try:
            idx = IntPrompt.ask(
                f"  [bold cyan]Format number select karo[/] "
                f"[dim](0–{len(formats) - 1})[/]"
            )
            if 0 <= idx < len(formats):
                chosen = formats[idx]
                console.print(
                    f"\n  [dim]Selected →[/] [green]{chosen['resolution']}[/]  "
                    f"[dim]{chosen['container']} | {chosen['delivery']} | "
                    f"{human_size(chosen.get('filesize'))}[/]\n"
                )
                return chosen
            console.print(f"  [yellow]0 aur {len(formats) - 1} ke beech number daalo.[/]")
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n  [dim]Cancelled.[/]")
            return None


# ════════════════════════════════════════════════════════════════════════════
#  aria2c Download Engine
# ════════════════════════════════════════════════════════════════════════════

def _make_progress() -> Progress:
    """
    Rich Progress bar banao jisme spinner, speed aur ETA sab dikhega.
    transient=False ka matlab hai complete hone ke baad bar screen par rahegi.
    """
    return Progress(
        SpinnerColumn(spinner_name="dots", style="cyan"),
        TextColumn("[bold cyan]{task.description}[/]"),
        BarColumn(bar_width=28, style="cyan", complete_style="green"),
        TaskProgressColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )


def _aria2c_header_args(headers: dict) -> List[str]:
    return [f"--header={k}: {v}" for k, v in headers.items()]


def _parse_percent(line: str) -> Optional[float]:
    """aria2c line se percentage parse karo: (10%) → 10.0"""
    m = re.search(r'\((\d+)%\)', line)
    return float(m.group(1)) if m else None


def _parse_files_progress(line: str) -> Optional[tuple]:
    """Segmented ke liye: '3/50 files' → (3, 50)"""
    m = re.search(r'(\d+)/(\d+)\s+files?', line)
    return (int(m.group(1)), int(m.group(2))) if m else None


def aria2c_direct(url: str, out_path: str, headers: dict, label: str) -> bool:
    """
    Single file ko 16 parallel connections se download karo.
    aria2c ka stdout real-time parse karke Rich progress bar update hota hai.
    """
    cmd = [
        "aria2c", url,
        "--dir",     str(Path(out_path).parent),
        "--out",     Path(out_path).name,
        "--max-connection-per-server=16",
        "--split=16",
        "--min-split-size=1M",
        "--file-allocation=none",
        "--retry-wait=3",
        "--max-tries=5",
        "--console-log-level=notice",
        "--summary-interval=1",
    ] + _aria2c_header_args(headers)

    with _make_progress() as prog:
        task = prog.add_task(label, total=100)
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        for line in proc.stdout:
            pct = _parse_percent(line.strip())
            if pct is not None:
                prog.update(task, completed=pct)
        proc.wait()
        prog.update(task, completed=100)

    return proc.returncode == 0


def aria2c_segmented(urls: List[str], out_path: str, headers: dict, label: str) -> bool:
    """
    HLS/DASH segments: 16 ek saath download karo, phir ffmpeg se concat karo.
    Progress segments count se track hoti hai (X/Total files).
    """
    seg_dir     = out_path + "_segs"
    input_file  = out_path + "_list.txt"
    concat_file = out_path + "_concat.txt"
    os.makedirs(seg_dir, exist_ok=True)
    total = len(urls)

    try:
        # aria2c batch input file banao — ek URL block per segment
        header_lines = [f"  header={k}: {v}" for k, v in headers.items()]
        with open(input_file, "w") as f:
            for i, u in enumerate(urls):
                f.write(f"{u}\n  out={i:06d}.ts\n")
                for hl in header_lines:
                    f.write(hl + "\n")

        cmd = [
            "aria2c",
            "--input-file",             input_file,
            "--dir",                    seg_dir,
            "--max-connection-per-server=4",
            "--max-concurrent-downloads=16",
            "--file-allocation=none",
            "--retry-wait=3",
            "--max-tries=5",
            "--console-log-level=notice",
            "--summary-interval=1",
        ]

        with _make_progress() as prog:
            task = prog.add_task(f"{label} ({total} segments)", total=100)
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            for line in proc.stdout:
                result = _parse_files_progress(line.strip())
                if result:
                    done, tot = result
                    prog.update(task, completed=min((done / (tot or total)) * 100, 99))
            proc.wait()
            prog.update(task, completed=99)

        if proc.returncode != 0:
            return False

        # Segments ko ek file mein join karo
        seg_files = sorted(Path(seg_dir).glob("*.ts"))
        if not seg_files:
            console.print("  [red]Koi segment file nahi mili![/]")
            return False

        with open(concat_file, "w") as f:
            for s in seg_files:
                f.write(f"file '{s.absolute()}'\n")

        with Status("[cyan]Combining segments…[/]", spinner="dots", console=console):
            r = subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                 "-i", concat_file, "-c", "copy", out_path],
                capture_output=True
            )

        if r.returncode != 0:
            console.print("[red]ffmpeg concat failed:[/]")
            console.print(r.stderr.decode()[-400:])
            return False

        return True

    finally:
        for p in (input_file, concat_file):
            if os.path.exists(p):
                os.remove(p)
        shutil.rmtree(seg_dir, ignore_errors=True)


def download_stream(fmt: dict, out_path: str, label: str) -> bool:
    """Delivery type auto-detect karke sahi download function call karo."""
    urls     = extract_urls(fmt)
    headers  = get_headers(fmt)
    delivery = get_delivery(fmt)

    if not urls:
        console.print(f"  [red]No URLs found for {label}[/]")
        return False

    if delivery == "direct":
        return aria2c_direct(urls[0], out_path, headers, label)
    else:
        return aria2c_segmented(urls, out_path, headers, label)


# ════════════════════════════════════════════════════════════════════════════
#  FFmpeg Merge
# ════════════════════════════════════════════════════════════════════════════

def ffmpeg_merge(video: str, audio: str, output: str) -> bool:
    """
    Video + Audio merge karo bina re-encode kiye (-c copy).
    Sirf container change hota hai — isliye bahut fast hota hai.
    """
    with Status("[cyan]Merging video + audio…[/]", spinner="dots", console=console):
        r = subprocess.run(
            ["ffmpeg", "-y",
             "-i", video, "-i", audio,
             "-c", "copy",
             "-map", "0:v:0", "-map", "1:a:0",
             output],
            capture_output=True
        )

    if r.returncode != 0:
        console.print("[red]Merge failed:[/]")
        console.print(r.stderr.decode()[-400:])
        return False

    return True


# ════════════════════════════════════════════════════════════════════════════
#  Main Download Orchestrator
# ════════════════════════════════════════════════════════════════════════════

def download(url: str, output_dir: str, resolution: Optional[str], audio_only: bool) -> None:

    console.print(f"  [dim]URL:[/] {url}\n")

    # ── Step 1: Info Fetch ─────────────────────────────────────────────────
    with Status("[cyan]Fetching video info…[/]", spinner="dots", console=console) as st:
        try:
            info = extract_info(url)
        except Exception as e:
            st.stop()
            console.print(f"  [red]Fetch failed:[/] {e}")
            sys.exit(1)

    formats = build_formats(info)
    if not formats:
        console.print("  [red]Koi downloadable format nahi mila.[/]")
        sys.exit(1)

    print_video_info(info, len(formats))

    # ── Step 2: Format Selection ───────────────────────────────────────────
    if audio_only:
        audio_fmts = [f for f in formats if f["resolution"] == "Audio"]
        if not audio_fmts:
            console.print("  [red]Audio format nahi mila![/]")
            sys.exit(1)
        chosen = audio_fmts[0]
        console.print(
            f"  [dim]Audio-only mode →[/] [green]{chosen['container']}[/]  "
            f"[dim]{human_size(chosen.get('filesize'))}[/]\n"
        )
    else:
        chosen = choose_format(formats, resolution)
        if not chosen:
            sys.exit(0)

    # ── Step 3: Download ───────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    safe_ttl = safe_filename(info.get("title", "video"))
    tmp_dir  = tempfile.mkdtemp(prefix="ytdl_")

    console.print(Rule(style="dim"))
    console.print()

    try:
        if chosen["resolution"] == "Audio":
            # ── Case A: Sirf Audio ─────────────────────────────────────────
            fmt        = chosen["audio_fmt"]
            ext        = fmt.get("ext", "m4a")
            tmp_audio  = os.path.join(tmp_dir, f"audio.{ext}")
            final_path = os.path.join(output_dir, f"{safe_ttl}.{ext}")

            if not download_stream(fmt, tmp_audio, f"Audio [{ext}]"):
                console.print("\n  [red]Audio download failed![/]")
                sys.exit(1)
            shutil.move(tmp_audio, final_path)

        elif chosen["needs_merge"]:
            # ── Case B: Alag video + audio → merge ────────────────────────
            vid_fmt    = chosen["video_fmt"]
            aud_fmt    = chosen["audio_fmt"]
            tmp_video  = os.path.join(tmp_dir, f"video.{vid_fmt.get('ext','mp4')}")
            tmp_audio  = os.path.join(tmp_dir, f"audio.{aud_fmt.get('ext','m4a')}")
            final_path = os.path.join(output_dir, f"{safe_ttl}_{chosen['resolution']}.mp4")

            if not download_stream(vid_fmt, tmp_video, f"Video  [{chosen['resolution']}]"):
                console.print("\n  [red]Video download failed![/]")
                sys.exit(1)

            console.print()

            if not download_stream(aud_fmt, tmp_audio, f"Audio  [{aud_fmt.get('ext','m4a')}]"):
                console.print("\n  [red]Audio download failed![/]")
                sys.exit(1)

            console.print()

            if not ffmpeg_merge(tmp_video, tmp_audio, final_path):
                sys.exit(1)

        else:
            # ── Case C: Embedded audio (Instagram etc.) — sirf ek download ─
            fmt        = chosen["video_fmt"]
            ext        = fmt.get("ext", "mp4")
            tmp_video  = os.path.join(tmp_dir, f"video.{ext}")
            final_path = os.path.join(
                output_dir,
                f"{safe_ttl}_{chosen['resolution']}.{ext}"
            )

            if not download_stream(fmt, tmp_video, f"Video  [{chosen['resolution']}]"):
                console.print("\n  [red]Download failed![/]")
                sys.exit(1)
            shutil.move(tmp_video, final_path)

        # ── Done ──────────────────────────────────────────────────────────
        final_size = human_size(os.path.getsize(final_path))
        console.print()
        console.print(
            Panel(
                f"  [green]✓  Download complete![/]\n\n"
                f"  [dim]File  [/] [bold white]{final_path}[/]\n"
                f"  [dim]Size  [/] [cyan]{final_size}[/]",
                border_style="green",
                padding=(0, 1),
                expand=False,
            )
        )

    finally:
        # Chahe success ho ya fail — temp files hamesha clean honge
        shutil.rmtree(tmp_dir, ignore_errors=True)

    console.print()


# ════════════════════════════════════════════════════════════════════════════
#  CLI Entry Point
# ════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ytdl",
        description="Terminal video downloader — aria2c + ffmpeg",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python ytdl.py "https://youtube.com/watch?v=..."
  python ytdl.py "URL" -r 720p
  python ytdl.py "URL" -o ~/storage/downloads
  python ytdl.py "URL" --audio-only
        """
    )
    parser.add_argument("url")
    parser.add_argument("-o", "--output",     default=".",  help="Output folder")
    parser.add_argument("-r", "--resolution", default=None, help="e.g. 720p, 1080p")
    parser.add_argument("--audio-only",       action="store_true")
    parser.add_argument("--no-banner",        action="store_true")
    args = parser.parse_args()

    if not args.no_banner:
        print_banner()

    check_dependencies()

    download(
        url        = args.url,
        output_dir = os.path.expanduser(args.output),
        resolution = args.resolution,
        audio_only = args.audio_only,
    )


if __name__ == "__main__":
    main()
