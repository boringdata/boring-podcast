"""Generate transcript from audio using OpenAI Whisper API."""

import subprocess
from pathlib import Path


def get_openai_key() -> str:
    """Get OpenAI API key from Vault."""
    result = subprocess.run(
        ["vault", "kv", "get", "-field=api_key", "secret/agent/openai"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get OpenAI key from Vault: {result.stderr}")
    return result.stdout.strip()


def generate_transcript(audio_path: Path, output_path: Path, language: str = "en"):
    """
    Transcribe audio file using OpenAI Whisper API.

    Args:
        audio_path: Path to audio file (mp3, wav, etc.)
        output_path: Path to write transcript markdown
        language: Language code (default: en)
    """
    from openai import OpenAI

    audio_path = Path(audio_path)
    output_path = Path(output_path)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    client = OpenAI(api_key=get_openai_key())

    # Whisper has a 25MB limit - split large files if needed
    file_size = audio_path.stat().st_size
    if file_size > 24 * 1024 * 1024:
        transcript_text = _transcribe_chunked(client, audio_path, language)
    else:
        transcript_text = _transcribe_single(client, audio_path, language)

    # Write as markdown
    with open(output_path, "w") as f:
        f.write(f"# Transcript\n\n")
        f.write(f"*Auto-generated from {audio_path.name}*\n\n")
        f.write(transcript_text)

    return output_path


def _transcribe_single(client, audio_path: Path, language: str) -> str:
    """Transcribe a single audio file."""
    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language,
            response_format="text"
        )
    return response


def _transcribe_chunked(client, audio_path: Path, language: str) -> str:
    """Split large audio and transcribe in chunks."""
    import tempfile
    import os

    chunk_dir = Path(tempfile.mkdtemp())
    chunk_duration = 600  # 10 min chunks

    # Split with ffmpeg
    cmd = [
        "ffmpeg", "-i", str(audio_path),
        "-f", "segment",
        "-segment_time", str(chunk_duration),
        "-c", "copy",
        "-y",
        str(chunk_dir / "chunk_%03d.mp3")
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg split failed: {result.stderr[:500]}")

    # Transcribe each chunk
    chunks = sorted(chunk_dir.glob("chunk_*.mp3"))
    transcript_parts = []
    for i, chunk in enumerate(chunks):
        print(f"  Transcribing chunk {i+1}/{len(chunks)}...")
        text = _transcribe_single(client, chunk, language)
        transcript_parts.append(text)

    # Cleanup
    for chunk in chunks:
        os.unlink(chunk)
    os.rmdir(chunk_dir)

    return "\n\n".join(transcript_parts)
