"""Podcast workspace plugin – API routes for episode management.

Mounted automatically by boring-ui's workspace plugin system at ``/api/x/podcast/``.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["podcast"])

# Workspace root is the parent of kurt/ (i.e. the boring-podcast repo)
_WORKSPACE = Path(os.environ.get("BORING_UI_WORKSPACE_ROOT", Path(__file__).resolve().parents[2]))


def _podcast_config() -> dict:
    """Load podcast.toml from workspace root."""
    conf_path = _WORKSPACE / "podcast.toml"
    if not conf_path.exists():
        return {}
    return tomllib.loads(conf_path.read_text())


def _episode_dirs() -> list[Path]:
    """Return sorted list of episode directories."""
    ep_root = _WORKSPACE / "episodes"
    if not ep_root.is_dir():
        return []
    return sorted(
        [d for d in ep_root.iterdir() if d.is_dir() and not d.name.startswith(".")],
        key=lambda d: d.name,
    )


def _load_episode(ep_dir: Path) -> dict:
    """Load episode metadata from its directory."""
    meta_path = ep_dir / "metadata.toml"
    if not meta_path.exists():
        return {"slug": ep_dir.name, "dir": str(ep_dir)}

    meta = tomllib.loads(meta_path.read_text())
    ep = meta.get("episode", {})
    publish = meta.get("publish", {})
    files_section = meta.get("files", {})

    # Determine which assets exist
    has_audio = (ep_dir / "audio.mp3").exists()
    has_video = (ep_dir / files_section.get("video", "video.mp4")).exists()
    has_transcript = (ep_dir / "transcript.md").exists()
    has_show_notes = (ep_dir / "show-notes.md").exists()

    # Parse publish log for pipeline status
    log_path = ep_dir / "publish.log"
    steps: dict[str, str] = {}
    if log_path.exists():
        for line in log_path.read_text().splitlines():
            m = re.match(r"\[.*?\]\s+(\w+)\s+(START|DONE|FAIL)\s*(.*)", line)
            if m:
                steps[m.group(1)] = m.group(2).lower()

    return {
        "slug": ep_dir.name,
        "number": ep.get("number"),
        "title": ep.get("title", ep_dir.name),
        "description": ep.get("description", ""),
        "tags": ep.get("tags", []),
        "assets": {
            "audio": has_audio,
            "video": has_video,
            "transcript": has_transcript,
            "show_notes": has_show_notes,
        },
        "publish_targets": publish,
        "pipeline_steps": steps,
    }


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@router.get("/episodes")
async def list_episodes():
    """List all episodes with metadata and pipeline status."""
    episodes = [_load_episode(d) for d in _episode_dirs()]
    config = _podcast_config()
    return {
        "podcast": config.get("podcast", {}),
        "episodes": episodes,
    }


@router.get("/episodes/{slug}")
async def get_episode(slug: str):
    """Get a single episode by slug."""
    for d in _episode_dirs():
        if d.name == slug:
            return _load_episode(d)
    raise HTTPException(status_code=404, detail=f"Episode '{slug}' not found")


@router.get("/status")
async def pipeline_status():
    """Overall pipeline status summary."""
    episodes = [_load_episode(d) for d in _episode_dirs()]
    return {
        "total_episodes": len(episodes),
        "with_audio": sum(1 for e in episodes if e["assets"]["audio"]),
        "with_transcript": sum(1 for e in episodes if e["assets"]["transcript"]),
        "with_show_notes": sum(1 for e in episodes if e["assets"]["show_notes"]),
    }


class PublishRequest(BaseModel):
    slug: str
    steps: list[str] | None = None  # e.g. ["audio", "transcript", "rss"]


@router.post("/publish")
async def publish(req: PublishRequest):
    """Trigger publish pipeline for an episode.

    This is a placeholder – the actual pipeline execution will be wired
    to the existing boring-podcast workflow scripts.
    """
    ep_dir = _WORKSPACE / "episodes" / req.slug
    if not ep_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Episode '{req.slug}' not found")

    # Check if the workflow publish script exists
    publish_script = _WORKSPACE / "workflows" / "publish.py"
    if not publish_script.exists():
        return {
            "status": "pending",
            "message": "Publish script not found – pipeline not yet configured",
            "slug": req.slug,
        }

    return {
        "status": "queued",
        "message": f"Publish pipeline queued for {req.slug}",
        "slug": req.slug,
        "steps": req.steps or ["audio", "transcript", "show_notes", "rss"],
    }
