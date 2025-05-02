from yt_dlp import YoutubeDL

def fetch_sc_playlist_full(url):
    ydl_opts = {
        'extract_flat': False,   # recurse into each track
        'skip_download': True,   # metadata only
        'quiet': False,          # so you’ll see errors if any
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    tracks = []
    for entry in info.get('entries', []):
        tracks.append({
            'title':     entry.get('title'),
            'artist':    entry.get('uploader'),
            'thumbnail': entry.get('thumbnail'),
            'duration':  entry.get('duration'),
        })
    return tracks

if __name__ == "__main__":
    playlist_url = "https://soundcloud.com/srikar-nadella/sets/luh-playground"
    tracks = fetch_sc_playlist_full(playlist_url)
    for i, t in enumerate(tracks, 1):
        print(f"{i:2d}. {t['title']!r} — {t['artist']!r} — {t['thumbnail']!r}")
