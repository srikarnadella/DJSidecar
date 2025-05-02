# utils/track_db.py

import sqlite3
import glob
import csv
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH   = BASE_DIR / "data" / "track_info.db"
DATA_DIR  = BASE_DIR / "data"

def create_track_db(db_path=DB_PATH, data_dir=DATA_DIR):
    """Read all .txt files, dedupe in Python, then populate SQLite."""
    os.makedirs(db_path.parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
      CREATE TABLE IF NOT EXISTS track_info (
        id INTEGER PRIMARY KEY,
        track_title TEXT,
        artist TEXT,
        bpm REAL,
        key TEXT,
        album TEXT,
        genre TEXT,
        rating TEXT,
        time TEXT,
        date_added TEXT,
        UNIQUE(track_title, artist)
      );
    ''')
    c.execute('DELETE FROM track_info;')

    unique = {}
    for txt_file in glob.glob(str(data_dir / "*.txt")):
        # adjust encoding if needed
        with open(txt_file, newline="", encoding="utf-16") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                title  = row.get("Track Title", "").strip()
                artist = row.get("Artist", "").strip()
                if not title or not artist:
                    continue
                key_ = (title.lower(), artist.lower())
                if key_ in unique:
                    continue
                unique[key_] = {
                    "track_title": title,
                    "artist":      artist,
                    "bpm":         float(row["BPM"]) if row.get("BPM") else None,
                    "key":         row.get("Key","").strip(),
                    "album":       row.get("Album","").strip(),
                    "genre":       row.get("Genre","").strip(),
                    "rating":      row.get("Rating","").strip(),
                    "time":        row.get("Time","").strip(),
                    "date_added":  row.get("Date Added","").strip()
                }

    inserted = 0
    for entry in unique.values():
        c.execute('''
          INSERT OR IGNORE INTO track_info
            (track_title, artist, bpm, key, album, genre, rating, time, date_added)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
          entry["track_title"],
          entry["artist"],
          entry["bpm"],
          entry["key"],
          entry["album"],
          entry["genre"],
          entry["rating"],
          entry["time"],
          entry["date_added"]
        ))
        inserted += c.rowcount

    conn.commit()
    conn.close()
    print(f"Inserted {inserted} unique records into {db_path}")

def get_track_info(title, db_path=DB_PATH):
    """Return (bpm, key) for a given track title, or (None, None)."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT bpm, key FROM track_info WHERE track_title = ?', (title,))
    row = c.fetchone()
    conn.close()
    if row:
        return row
    return (None, None)

def get_all_track_titles(db_path=DB_PATH):
    """Return a list of all track titles in the DB (for autocomplete)."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT DISTINCT track_title FROM track_info')
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_all_tracks(db_path=DB_PATH):
    """
    Return a list of dicts for every track in track_info,
    with keys: title, artist, bpm, key.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT track_title, artist, bpm, key FROM track_info')
    rows = c.fetchall()
    conn.close()
    return [
        {"title": t, "artist": a, "bpm": b or 0, "key": k or ""}
        for (t, a, b, k) in rows
    ]


if __name__ == "__main__":
    create_track_db()
