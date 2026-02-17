"""Generate show notes from transcript using Claude API."""

import subprocess
from pathlib import Path


def get_anthropic_key() -> str:
    """Get Anthropic API key from Vault."""
    result = subprocess.run(
        ["vault", "kv", "get", "-field=api_key", "secret/agent/anthropic"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get Anthropic key from Vault: {result.stderr}")
    return result.stdout.strip()


def generate_show_notes(transcript_path: Path, output_path: Path, metadata: dict):
    """
    Generate show notes from a transcript using Claude.

    Args:
        transcript_path: Path to transcript markdown file
        output_path: Path to write show notes
        metadata: Episode metadata dict (from metadata.toml)
    """
    import anthropic

    transcript_path = Path(transcript_path)
    output_path = Path(output_path)

    transcript = transcript_path.read_text()
    ep = metadata.get("episode", {})
    title = ep.get("title", "Untitled Episode")
    guests = ep.get("guests", {})

    guest_info = ""
    if guests:
        guest_info = "Guests: " + ", ".join(f"{name} ({role})" for name, role in guests.items())

    prompt = f"""You are a podcast show notes writer. Given the transcript below, generate professional show notes in Markdown format.

Include:
1. A concise episode summary (2-3 sentences)
2. Key topics discussed (bulleted list)
3. Notable quotes (2-3 best quotes with timestamps if available)
4. Resources/links mentioned
5. Guest bio (if applicable)

Episode title: {title}
{guest_info}

Keep it concise and engaging. Write for someone deciding whether to listen.

Transcript:
{transcript[:50000]}"""

    client = anthropic.Anthropic(api_key=get_anthropic_key())

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    show_notes = message.content[0].text

    with open(output_path, "w") as f:
        f.write(f"# {title} - Show Notes\n\n")
        f.write(show_notes)

    return output_path
