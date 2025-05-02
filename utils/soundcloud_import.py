from yt_dlp import YoutubeDL

"fetch_sc_playlist_full imports and returns full track metadata"

def fetch_sc_playlist_full(url):
    ydl_opts = {
        'extract_flat': False,
        'skip_download': True,
        'quiet': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    tracks = []
    for entry in info.get('entries', []):
        tracks.append({
            'title': entry.get('title'),
            'artist': entry.get('uploader'),
            'thumbnail': entry.get('thumbnail'),
            'duration': entry.get('duration'),
            'bpm': entry.get('bpm'),
            'key': entry.get('key'),
        })
    return tracks