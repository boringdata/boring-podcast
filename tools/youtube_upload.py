"""Upload video to YouTube using YouTube Data API v3."""

import json
import time
from pathlib import Path

# Auth token paths
TOKEN_PATH = Path(__file__).parent.parent / ".youtube_token.json"
CLIENT_SECRETS_PATH = Path(__file__).parent.parent / "client_secrets.json"


def upload_to_youtube(video_path: Path, metadata: dict) -> str:
    """
    Upload a video to YouTube.

    Args:
        video_path: Path to video file
        metadata: Episode metadata dict (from metadata.toml)

    Returns:
        YouTube video URL

    Setup required (one-time):
        1. Create a Google Cloud project at https://console.cloud.google.com/
        2. Enable YouTube Data API v3
        3. Create OAuth 2.0 credentials (Desktop app)
        4. Download client_secrets.json to project root
        5. Run: python tools/youtube_upload.py --auth
           (opens browser for OAuth consent, saves refresh token)
    """
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    credentials = _get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    ep = metadata.get("episode", {})
    yt = metadata.get("youtube", {})

    # Build description from show notes if available
    description = ep.get("description", "")
    show_notes = video_path.parent / "show-notes.md"
    if show_notes.exists():
        description += "\n\n" + show_notes.read_text()

    body = {
        "snippet": {
            "title": ep.get("title", video_path.stem),
            "description": description[:5000],  # YouTube limit
            "tags": ep.get("tags", []),
            "categoryId": yt.get("category_id", "22"),
        },
        "status": {
            "privacyStatus": yt.get("privacy", "public"),
            "selfDeclaredMadeForKids": yt.get("made_for_kids", False),
        }
    }

    media = MediaFileUpload(
        str(video_path),
        chunksize=10 * 1024 * 1024,  # 10MB chunks
        resumable=True
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    # Resumable upload with progress
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  YouTube upload: {pct}%")

    video_id = response["id"]
    video_url = f"https://youtube.com/watch?v={video_id}"

    # Add to playlist if specified
    playlist = yt.get("playlist", "")
    if playlist:
        _add_to_playlist(youtube, video_id, playlist)

    return video_url


def _get_credentials():
    """Load or refresh OAuth2 credentials."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
        return creds

    raise FileNotFoundError(
        "No YouTube credentials found. Run:\n"
        "  python tools/youtube_upload.py --auth\n"
        "to authenticate (one-time setup)."
    )


def _add_to_playlist(youtube, video_id: str, playlist_name: str):
    """Add video to a playlist by name (creates playlist if needed)."""
    # Find existing playlist
    playlists = youtube.playlists().list(part="snippet", mine=True, maxResults=50).execute()
    playlist_id = None
    for pl in playlists.get("items", []):
        if pl["snippet"]["title"] == playlist_name:
            playlist_id = pl["id"]
            break

    # Create if not found
    if not playlist_id:
        resp = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {"title": playlist_name},
                "status": {"privacyStatus": "public"}
            }
        ).execute()
        playlist_id = resp["id"]

    # Add video
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id}
            }
        }
    ).execute()


def authenticate():
    """One-time OAuth setup - opens browser for consent."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CLIENT_SECRETS_PATH.exists():
        print(f"ERROR: {CLIENT_SECRETS_PATH} not found.")
        print("Download it from Google Cloud Console > APIs > Credentials > OAuth 2.0 Client IDs")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRETS_PATH),
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json())
    print(f"Authenticated! Token saved to {TOKEN_PATH}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auth", action="store_true", help="Run OAuth setup")
    args = parser.parse_args()
    if args.auth:
        authenticate()
