# Publish Episode Workflow

Publish a podcast episode to YouTube, Spotify, and Apple Podcasts.

## Usage

```bash
# Full pipeline
python -m tools.publish episodes/ep001-my-topic/

# Individual steps
python -m tools.publish episodes/ep001-my-topic/ --steps audio
python -m tools.publish episodes/ep001-my-topic/ --steps transcript
python -m tools.publish episodes/ep001-my-topic/ --steps show_notes
python -m tools.publish episodes/ep001-my-topic/ --steps youtube
python -m tools.publish episodes/ep001-my-topic/ --steps rss
```

## New Episode Checklist

1. Create episode directory:
   ```bash
   cp -r episodes/.template episodes/ep001-my-topic
   ```

2. Place your video file:
   ```bash
   cp /path/to/recording.mp4 episodes/ep001-my-topic/video.mp4
   ```

3. Edit metadata:
   ```bash
   $EDITOR episodes/ep001-my-topic/metadata.toml
   ```

4. Publish:
   ```bash
   python -m tools.publish episodes/ep001-my-topic/
   ```

## What Happens

| Step | Tool | Output |
|------|------|--------|
| Extract audio | ffmpeg | `audio.mp3` |
| Transcribe | Whisper API | `transcript.md` |
| Show notes | Claude API | `show-notes.md` |
| YouTube | YouTube Data API v3 | Video URL in `publish.log` |
| RSS feed | feedgen | `feed/podcast.xml` |

Spotify and Apple Podcasts auto-poll the RSS feed - no API needed.

## One-Time Setup

### YouTube API
1. Go to https://console.cloud.google.com/
2. Create project, enable YouTube Data API v3
3. Create OAuth 2.0 credentials (Desktop app)
4. Download `client_secrets.json` to project root
5. Run `python tools/youtube_upload.py --auth`

### RSS Feed Hosting
1. Edit `podcast.toml` with your podcast info
2. Host the `feed/` directory on your CDN/server
3. Host episode `audio.mp3` files at the `media_base_url`
4. Submit feed URL once to:
   - Spotify: https://podcasters.spotify.com/
   - Apple: https://podcastsconnect.apple.com/

### API Keys (Vault)
- OpenAI (Whisper): `vault kv get secret/agent/openai`
- Anthropic (show notes): `vault kv get secret/agent/anthropic`
