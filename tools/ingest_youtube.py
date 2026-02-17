#!/usr/bin/env python3
"""
Ingest a YouTube video as a podcast episode.

Downloads the video, extracts audio, and creates the episode directory
with metadata pre-filled from the YouTube video info.

Requirements (install on your Mac):
    brew install yt-dlp ffmpeg

Usage:
    python tools/ingest_youtube.py <youtube-url> [--episode NUM] [--slug SLUG]

Examples:
    python tools/ingest_youtube.py "https://www.youtube.com/watch?v=U82J6Aenmg4"
    python tools/ingest_youtube.py "https://www.youtube.com/watch?v=U82J6Aenmg4" --episode 1 --slug "ai-eng-intro"
    python tools/ingest_youtube.py "https://www.youtube.com/watch?v=U82J6Aenmg4" --audio-only
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


REPO_ROOT = Path(__file__).resolve().parent.parent
EPISODES_DIR = REPO_ROOT / "episodes"


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:60].strip("-")


def get_next_episode_number() -> int:
    """Find the next episode number from existing directories."""
    if not EPISODES_DIR.is_dir():
        return 1
    numbers = []
    for d in EPISODES_DIR.iterdir():
        if d.is_dir() and not d.name.startswith("."):
            m = re.match(r"ep(\d+)", d.name)
            if m:
                numbers.append(int(m.group(1)))
    return max(numbers, default=0) + 1


def fetch_video_info(url: str) -> dict:
    """Get video metadata from YouTube via yt-dlp."""
    print(f"Fetching video info...")
    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-download", url],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Error fetching video info:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def download_video(url: str, output_path: Path) -> None:
    """Download the video file."""
    print(f"Downloading video to {output_path.name}...")
    subprocess.run(
        [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", str(output_path),
            url,
        ],
        check=True,
    )


def download_audio_only(url: str, output_path: Path) -> None:
    """Download audio only as MP3."""
    print(f"Downloading audio to {output_path.name}...")
    subprocess.run(
        [
            "yt-dlp",
            "-x", "--audio-format", "mp3",
            "--audio-quality", "192K",
            "-o", str(output_path),
            url,
        ],
        check=True,
    )


def extract_audio(video_path: Path, audio_path: Path) -> None:
    """Extract audio from video using ffmpeg."""
    print(f"Extracting audio...")
    subprocess.run(
        [
            "ffmpeg", "-i", str(video_path),
            "-vn", "-acodec", "libmp3lame",
            "-ab", "192k", "-ar", "44100", "-ac", "2",
            "-y", str(audio_path),
        ],
        capture_output=True, check=True,
    )


def format_duration(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def write_metadata(episode_dir: Path, info: dict, episode_num: int) -> None:
    """Write metadata.toml from YouTube video info."""
    title = info.get("title", "Untitled")
    description = info.get("description", "")
    # Truncate description for RSS — take the first non-trivial paragraph
    short_desc = ""
    if description:
        for para in description.split("\n\n"):
            stripped = para.strip()
            if len(stripped) > 20:
                short_desc = stripped[:500]
                break
        if not short_desc:
            short_desc = description.strip()[:500]
    channel = info.get("channel", "")
    tags = info.get("tags", []) or []
    # Keep only first 5 tags
    tags = [t for t in tags[:5] if t]

    slug = episode_dir.name.replace(f"ep{episode_num:03d}-", "")
    tags_str = json.dumps(tags)

    # Escape TOML strings
    title_escaped = title.replace('"', '\\"')
    short_desc_escaped = short_desc.replace('"', '\\"')

    content = f'''[episode]
number = {episode_num}
title = "{title_escaped}"
slug = "{slug}"
description = "{short_desc_escaped}"
tags = {tags_str}
category = "Technology"
language = "en"
explicit = false
youtube_url = "{info.get('webpage_url', '')}"
youtube_id = "{info.get('id', '')}"

[episode.guests]

[files]
video = "video.mp4"

[publish]
youtube = false
spotify = true
apple = true

[youtube]
privacy = "public"
category_id = "28"
playlist = ""
made_for_kids = false

[podcast]
season = 1
episode_type = "full"
'''
    (episode_dir / "metadata.toml").write_text(content)


def main():
    parser = argparse.ArgumentParser(
        description="Ingest a YouTube video as a podcast episode",
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--episode", type=int, help="Episode number (auto-detected if omitted)")
    parser.add_argument("--slug", help="Episode slug (auto-generated from title if omitted)")
    parser.add_argument("--audio-only", action="store_true", help="Download audio only (skip video)")
    parser.add_argument("--no-download", action="store_true", help="Only create metadata, don't download files")
    args = parser.parse_args()

    # Get video info
    info = fetch_video_info(args.url)
    title = info.get("title", "Untitled")
    duration = info.get("duration", 0)

    print(f"\n  Title:    {title}")
    print(f"  Duration: {format_duration(duration)}")
    print(f"  Channel:  {info.get('channel', 'N/A')}")

    # Determine episode number and slug
    ep_num = args.episode or get_next_episode_number()
    slug = args.slug or slugify(title)
    dir_name = f"ep{ep_num:03d}-{slug}"
    episode_dir = EPISODES_DIR / dir_name

    print(f"  Episode:  #{ep_num}")
    print(f"  Dir:      episodes/{dir_name}/\n")

    # Create episode directory
    episode_dir.mkdir(parents=True, exist_ok=True)

    # Write metadata
    write_metadata(episode_dir, info, ep_num)
    print(f"  Created metadata.toml")

    # Save full description as a reference file
    desc = info.get("description", "")
    if desc:
        (episode_dir / "youtube-description.md").write_text(
            f"# {title}\n\n{desc}\n"
        )
        print(f"  Saved youtube-description.md")

    if args.no_download:
        print(f"\n  Skipping download (--no-download)")
        print(f"\n  Done! Episode directory: {episode_dir}")
        return

    # Download
    video_path = episode_dir / "video.mp4"
    audio_path = episode_dir / "audio.mp3"

    if args.audio_only:
        download_audio_only(args.url, audio_path)
        size_mb = audio_path.stat().st_size / 1_000_000
        print(f"  Audio: {size_mb:.1f} MB")
    else:
        download_video(args.url, video_path)
        size_mb = video_path.stat().st_size / 1_000_000
        print(f"  Video: {size_mb:.1f} MB")

        # Extract audio from video
        extract_audio(video_path, audio_path)
        audio_mb = audio_path.stat().st_size / 1_000_000
        print(f"  Audio: {audio_mb:.1f} MB")

    print(f"\n  Done! Episode directory: {episode_dir}")
    print(f"\n  Next steps:")
    print(f"    1. git add episodes/{dir_name}/ && git commit -m 'Add ep{ep_num:03d}'")
    print(f"    2. git push")
    print(f"    3. On the server: python tools/publish.py episodes/{dir_name}/")


if __name__ == "__main__":
    main()
