"""Generate and update podcast RSS feed for Spotify + Apple Podcasts distribution."""
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

# Podcast feed config
FEED_CONFIG_PATH = Path(__file__).parent.parent / "podcast.toml"
FEED_OUTPUT_PATH = Path(__file__).parent.parent / "feed" / "podcast.xml"


def load_podcast_config() -> dict:
    """Load podcast-level config from podcast.toml."""
    if not FEED_CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"No {FEED_CONFIG_PATH} found. Create it with your podcast info.\n"
            "See podcast.toml.example for the format."
        )
    with open(FEED_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def update_rss_feed(audio_path: Path, episode_metadata: dict) -> str:
    """
    Update the podcast RSS feed with a new episode.

    This generates a podcast.xml that Spotify and Apple Podcasts
    auto-poll for new episodes.

    Args:
        audio_path: Path to the episode audio file
        episode_metadata: Episode metadata dict (from metadata.toml)

    Returns:
        URL of the published feed
    """
    from feedgen.feed import FeedGenerator

    podcast_config = load_podcast_config()
    pc = podcast_config["podcast"]

    # Initialize feed
    fg = FeedGenerator()
    fg.load_extension("podcast")

    website = pc.get("website") or pc.get("media_base_url", "")
    fg.title(pc["title"])
    fg.link(href=website)
    fg.description(pc["description"])
    fg.language(pc.get("language", "en"))
    fg.podcast.itunes_author(pc["author"])
    fg.podcast.itunes_owner(name=pc["author"], email=pc["email"])
    fg.podcast.itunes_category(pc.get("category", "Technology"))
    fg.podcast.itunes_explicit("no")

    cover_url = pc.get("cover_url", "")
    if cover_url:
        fg.podcast.itunes_image(cover_url)

    # Load existing episodes from episodes/ directory
    episodes_dir = Path(__file__).parent.parent / "episodes"
    episode_dirs = sorted(
        [d for d in episodes_dir.iterdir() if d.is_dir() and not d.name.startswith(".")],
        key=lambda d: d.name
    )

    published_count = 0
    for ep_dir in episode_dirs:
        meta_path = ep_dir / "metadata.toml"
        if not meta_path.exists():
            continue

        with open(meta_path, "rb") as f:
            meta = tomllib.load(f)

        ep = meta["episode"]
        ep_audio = ep_dir / "audio.mp3"

        if not ep_audio.exists():
            continue

        # Build audio URL from base_url + episode slug
        base_url = pc.get("media_base_url", pc["website"])
        audio_url = f"{base_url}/episodes/{ep_dir.name}/audio.mp3"
        file_size = str(ep_audio.stat().st_size)

        fe = fg.add_entry()
        fe.id(f"{ep_dir.name}")
        fe.title(ep["title"])
        fe.description(ep.get("description", ""))
        fe.enclosure(audio_url, file_size, "audio/mpeg")
        if ep.get("number") is not None:
            fe.podcast.itunes_episode(str(ep["number"]))

        # Get duration
        try:
            from tools.audio import get_duration, format_duration
            duration = format_duration(get_duration(ep_audio))
            fe.podcast.itunes_duration(duration)
        except Exception:
            pass

        # Show notes as content
        show_notes = ep_dir / "show-notes.md"
        if show_notes.exists():
            fe.content(show_notes.read_text(), type="text")

        # Publication date
        pub_date = meta.get("publish", {}).get("date")
        if pub_date:
            fe.published(pub_date)
        else:
            fe.published(datetime.now(timezone.utc))

        # Podcast-specific
        podcast_meta = meta.get("podcast", {})
        if podcast_meta.get("season"):
            fe.podcast.itunes_season(str(podcast_meta["season"]))
        if podcast_meta.get("episode_type"):
            fe.podcast.itunes_episode_type(podcast_meta["episode_type"])
        published_count += 1

    # Write feed
    FEED_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fg.rss_file(str(FEED_OUTPUT_PATH), pretty=True)

    feed_url = f"{website}/feed/podcast.xml"
    print(f"  RSS feed updated: {FEED_OUTPUT_PATH}")
    print(f"  Feed URL: {feed_url}")
    print(f"  Episodes in feed: {published_count}")

    return feed_url
