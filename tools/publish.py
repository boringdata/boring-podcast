#!/usr/bin/env python3
"""
Podcast episode publisher - orchestrates the full publish pipeline.

Usage:
    python tools/publish.py episodes/ep001-my-topic/

Pipeline:
    1. Extract audio from video (ffmpeg)
    2. Generate transcript (Whisper API)
    3. Generate show notes (Claude AI)
    4. Upload video to YouTube (YouTube Data API v3)
    5. Upload audio to podcast RSS feed (self-hosted or Transistor)
    6. Log progress to publish.log
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from tools.audio import extract_audio
from tools.transcript import generate_transcript
from tools.show_notes import generate_show_notes
from tools.youtube_upload import upload_to_youtube
from tools.rss_feed import update_rss_feed


def load_metadata(episode_dir: Path) -> dict:
    """Load episode metadata from metadata.toml."""
    meta_path = episode_dir / "metadata.toml"
    if not meta_path.exists():
        raise FileNotFoundError(f"No metadata.toml in {episode_dir}")
    with open(meta_path, "rb") as f:
        return tomllib.load(f)


def log_progress(episode_dir: Path, step: str, status: str, detail: str = ""):
    """Append a progress line to publish.log."""
    log_path = episode_dir / "publish.log"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {step:<20} {status:<10} {detail}\n"
    with open(log_path, "a") as f:
        f.write(line)
    print(line.strip())


def publish_episode(episode_dir: Path, steps: list[str] | None = None):
    """Run the full publish pipeline for an episode."""
    episode_dir = Path(episode_dir).resolve()
    meta = load_metadata(episode_dir)
    ep = meta["episode"]
    files = meta.get("files", {})
    publish = meta.get("publish", {})

    title = ep["title"]
    print(f"\n{'='*60}")
    print(f"Publishing: {title}")
    print(f"Directory:  {episode_dir}")
    print(f"{'='*60}\n")

    all_steps = ["audio", "transcript", "show_notes", "youtube", "rss"]
    run_steps = steps or all_steps

    video_path = episode_dir / files.get("video", "video.mp4")
    audio_path = episode_dir / "audio.mp3"
    transcript_path = episode_dir / "transcript.md"
    show_notes_path = episode_dir / "show-notes.md"

    # Step 1: Extract audio
    if "audio" in run_steps:
        if not video_path.exists():
            log_progress(episode_dir, "audio", "SKIP", f"No video file: {video_path.name}")
        elif audio_path.exists():
            log_progress(episode_dir, "audio", "SKIP", "audio.mp3 already exists")
        else:
            log_progress(episode_dir, "audio", "START", f"Extracting from {video_path.name}")
            try:
                extract_audio(video_path, audio_path)
                log_progress(episode_dir, "audio", "DONE", f"{audio_path.stat().st_size / 1_000_000:.1f} MB")
            except Exception as e:
                log_progress(episode_dir, "audio", "FAIL", str(e))
                return

    # Step 2: Generate transcript
    if "transcript" in run_steps:
        if transcript_path.exists():
            log_progress(episode_dir, "transcript", "SKIP", "transcript.md already exists")
        elif not audio_path.exists():
            log_progress(episode_dir, "transcript", "SKIP", "No audio.mp3 yet")
        else:
            log_progress(episode_dir, "transcript", "START", "Transcribing with Whisper")
            try:
                generate_transcript(audio_path, transcript_path)
                log_progress(episode_dir, "transcript", "DONE", f"{transcript_path.stat().st_size / 1_000:.0f} KB")
            except Exception as e:
                log_progress(episode_dir, "transcript", "FAIL", str(e))

    # Step 3: Generate show notes
    if "show_notes" in run_steps:
        if show_notes_path.exists():
            log_progress(episode_dir, "show_notes", "SKIP", "show-notes.md already exists")
        elif not transcript_path.exists():
            log_progress(episode_dir, "show_notes", "SKIP", "No transcript yet")
        else:
            log_progress(episode_dir, "show_notes", "START", "Generating with Claude")
            try:
                generate_show_notes(transcript_path, show_notes_path, meta)
                log_progress(episode_dir, "show_notes", "DONE", f"{show_notes_path.stat().st_size / 1_000:.0f} KB")
            except Exception as e:
                log_progress(episode_dir, "show_notes", "FAIL", str(e))

    # Step 4: Upload to YouTube
    if "youtube" in run_steps and publish.get("youtube", False):
        if not video_path.exists():
            log_progress(episode_dir, "youtube", "SKIP", "No video file")
        else:
            log_progress(episode_dir, "youtube", "START", "Uploading to YouTube")
            try:
                yt_url = upload_to_youtube(video_path, meta)
                log_progress(episode_dir, "youtube", "DONE", yt_url)
            except Exception as e:
                log_progress(episode_dir, "youtube", "FAIL", str(e))

    # Step 5: Update RSS feed (serves Spotify + Apple Podcasts)
    if "rss" in run_steps and (publish.get("spotify", False) or publish.get("apple", False)):
        if not audio_path.exists():
            log_progress(episode_dir, "rss", "SKIP", "No audio file")
        else:
            log_progress(episode_dir, "rss", "START", "Updating RSS feed")
            try:
                feed_url = update_rss_feed(audio_path, meta)
                log_progress(episode_dir, "rss", "DONE", feed_url)
            except Exception as e:
                log_progress(episode_dir, "rss", "FAIL", str(e))

    print(f"\nPublish log: {episode_dir / 'publish.log'}")


def main():
    parser = argparse.ArgumentParser(description="Publish a podcast episode")
    parser.add_argument("episode_dir", help="Path to episode directory (e.g. episodes/ep001-topic)")
    parser.add_argument("--steps", nargs="+", choices=["audio", "transcript", "show_notes", "youtube", "rss"],
                        help="Run only specific steps (default: all)")
    args = parser.parse_args()
    publish_episode(args.episode_dir, args.steps)


if __name__ == "__main__":
    main()
