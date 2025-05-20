import requests
import os
import json
from dotenv import load_dotenv
import re

load_dotenv(override=False)
API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UCq6VFHwMzcMXbuKyG7SQYIg" 
BASE_URL = "https://www.googleapis.com/youtube/v3"
OUTPUT_FILE = "output/phrases.json"
FAILED_FILE = "output/failed.json"

def get_uploads_playlist_id():
    url = f"{BASE_URL}/channels?part=contentDetails&id={CHANNEL_ID}&key={API_KEY}"
    resp = requests.get(url).json()
    return resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

def get_videos_from_playlist(playlist_id):
    videos = []
    url = f"{BASE_URL}/playlistItems?part=snippet&playlistId={playlist_id}&maxResults=50&key={API_KEY}"
    
    while True:
        resp = requests.get(url).json()
        videos.extend(resp.get("items", []))
        next_token = resp.get("nextPageToken")
        if not next_token:
            break
        url = f"{BASE_URL}/playlistItems?part=snippet&playlistId={playlist_id}&maxResults=50&pageToken={next_token}&key={API_KEY}"

    print(f"📦 Fetched {len(videos)} videos from playlist {playlist_id}")
    
    return videos

def extract_phrase(text):
    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', text).strip()

    # Match the pattern (case-insensitive)
    match = re.search(
        r"greatest (.+?) of all time",
        normalized,
        re.IGNORECASE
    )

    if match:
        return match.group(1).strip()
    return None

def load_existing_phrases():
    if not os.path.exists(OUTPUT_FILE):
        return []
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_phrases(phrases):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(phrases, f, indent=2, ensure_ascii=False)

def main():
    print("Fetching Penguinz0 videos...")
    playlist_id = get_uploads_playlist_id()
    videos = get_videos_from_playlist(playlist_id)

    existing = load_existing_phrases()
    seen_urls = {entry["video_url"] for entry in existing}
    new_entries = []
    failed = []

    for video in videos:
        snippet = video["snippet"]
        desc = snippet.get("description", "")
        phrase = extract_phrase(desc)

        if not phrase:
            failed.append({
                "video_title": snippet["title"],
                "video_url": f"https://www.youtube.com/watch?v={snippet['resourceId']['videoId']}",
                "description": desc,
            })
            continue

        video_id = snippet["resourceId"]["videoId"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        if video_url in seen_urls:
            continue

        entry = {
            "phrase": phrase,
            "description": desc,
            "video_title": snippet["title"],
            "video_url": video_url,
            "published_at": snippet["publishedAt"],
        }
        new_entries.append(entry)

    if new_entries:
        updated = existing + new_entries
        save_phrases(updated)
        print(f"Added {len(new_entries)} new entries.")
    else:
        print("No new entries found.")

    if failed:
        with open(FAILED_FILE, "w", encoding="utf-8") as f:
            json.dump(failed, f, indent=2, ensure_ascii=False)
        print(f"Failed to extract phrases from {len(failed)} videos. See {FAILED_FILE} for details.")

if __name__ == "__main__":
    if not API_KEY:
        print("Error: YOUTUBE_API_KEY not set in environment.")
    else:
        main()
