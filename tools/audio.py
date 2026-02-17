"""Extract audio from video using ffmpeg."""

import subprocess
from pathlib import Path


def extract_audio(video_path: Path, audio_path: Path, bitrate: str = "192k"):
    """
    Extract audio track from video file to MP3.

    Args:
        video_path: Path to source video file
        audio_path: Path to output MP3 file
        bitrate: Audio bitrate (default 192k for podcast quality)
    """
    video_path = Path(video_path)
    audio_path = Path(audio_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vn",                    # no video
        "-acodec", "libmp3lame",  # MP3 codec
        "-ab", bitrate,           # bitrate
        "-ar", "44100",           # sample rate
        "-ac", "2",               # stereo
        "-y",                     # overwrite
        str(audio_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[:500]}")

    return audio_path


def get_duration(file_path: Path) -> float:
    """Get duration of audio/video file in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[:500]}")
    return float(result.stdout.strip())


def format_duration(seconds: float) -> str:
    """Format seconds as HH:MM:SS for iTunes duration tag."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
