
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QSizePolicy,
    QDockWidget, QListWidget, QListWidgetItem,
    QLineEdit, QMessageBox, QCompleter, QAbstractItemView,
    QApplication, QInputDialog
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from widgets.cover_carousel import CoverCarousel
from utils.soundcloud_import import fetch_sc_playlist_full
from utils.track_db import (
    get_track_info, get_all_track_titles, get_all_tracks
)
from utils.setlist_order import hybrid_order, camelot_distance

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

MAX_LOOKAHEAD = 10


class MainWindow(QMainWindow):
    def __init__(self, playlist_url):
        super().__init__()
        self.setWindowTitle("DJ Sidecar")
        self.setMinimumSize(820, 600)

        # store notes per (current,next) pair
        self.transition_notes_store = {}

        # --- Main layout ---
        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(20,20,20,20)
        self.main_layout.setSpacing(15)

        # Header
        hdr = QLabel("DJ Sidecar")
        hdr.setFont(QFont("Arial",24, QFont.Bold))
        hdr.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(hdr)

        # Build library_items from full DB
        db_tracks = get_all_tracks()
        self.library_items = [
            {**t, "thumbnail": None, "duration": 0.0}
            for t in db_tracks
        ]

        # Fetch playlist from SoundCloud
        raw = fetch_sc_playlist_full(playlist_url)
        playlist_items = []
        for t in raw:
            title = t.get("title","")
            rec = next((x for x in self.library_items if x["title"]==title), None)
            bpm, key = (rec["bpm"], rec["key"]) if rec else (0,"")
            playlist_items.append({
                "thumbnail": t.get("thumbnail"),
                "title": title,
                "artist": t.get("artist",""),
                "bpm": bpm,
                "key": key,
                "duration": t.get("duration",0)/1000.0
            })

        # Compute initial order
        self.ordered_items = hybrid_order(playlist_items)

        # Carousel
        self.carousel = CoverCarousel(self.ordered_items)
        self.carousel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_layout.addWidget(self.carousel)

        # track index internally
        self.current_index = 0
        self.carousel.indexChanged.connect(self.on_index_changed)

        # Energy curve (hidden)
        bpm_vals = [it["bpm"] for it in self.ordered_items]
        fig, ax = plt.subplots(figsize=(6,2), dpi=100)
        ax.plot(range(1,len(bpm_vals)+1), bpm_vals, marker="o")
        ax.set_title("Energy Curve (BPM)")
        ax.set_xlabel("Track Position")
        ax.set_ylabel("BPM")
        fig.tight_layout()
        self.energy_canvas = FigureCanvas(fig)
        self.energy_canvas.setVisible(False)
        self.main_layout.addWidget(self.energy_canvas)

        # --- Bottom: notes | request ---
        bottom = QWidget()
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(0,0,0,0)
        bl.setSpacing(20)

        # Notes side
        notes_w = QWidget()
        nl = QVBoxLayout(notes_w)
        nl.setContentsMargins(0,0,0,0)
        nl.setSpacing(10)
        lbln = QLabel("Transition Notes")
        lbln.setFont(QFont("Arial",16, QFont.Bold))
        nl.addWidget(lbln)
        self.transition_notes = QTextEdit()
        self.transition_notes.setPlaceholderText("Write transition notes…")
        self.transition_notes.textChanged.connect(self.save_current_notes)
        nl.addWidget(self.transition_notes)
        bl.addWidget(notes_w, stretch=3)

        # Request side
        req_w = QWidget()
        rl = QVBoxLayout(req_w)
        rl.setContentsMargins(0,0,0,0)
        rl.setSpacing(10)
        lblr = QLabel("Song Request")
        lblr.setFont(QFont("Arial",16, QFont.Bold))
        rl.addWidget(lblr)

        titles = get_all_track_titles()
        comp = QCompleter(titles)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        self.req_input = QLineEdit()
        self.req_input.setPlaceholderText("Type track name...")
        self.req_input.setCompleter(comp)
        rl.addWidget(self.req_input)

        btn = QPushButton("Add Request")
        btn.clicked.connect(self.handle_request)
        rl.addWidget(btn)
        rl.addStretch()
        bl.addWidget(req_w, stretch=2)

        self.main_layout.addWidget(bottom)

        # Navigation buttons
        nav = QHBoxLayout()
        nav.addStretch()
        p = QPushButton("⟵ Previous")
        n = QPushButton("Next ⟶")
        p.clicked.connect(self.carousel.previous)
        n.clicked.connect(self.carousel.next)
        nav.addWidget(p)
        nav.addWidget(n)
        nav.addStretch()
        self.main_layout.addLayout(nav)

        self.setCentralWidget(container)
        self._init_queue_dock()

    def on_index_changed(self, idx: int):
        """Called whenever carousel advances."""
        self.current_index = idx
        self.update_transition_notes()

    def save_current_notes(self):
        """Save notes keyed by (current, next)."""
        curr = self.current_index
        nxt = min(curr+1, len(self.ordered_items)-1)
        key = (self.ordered_items[curr]["title"],
               self.ordered_items[nxt]["title"])
        self.transition_notes_store[key] = self.transition_notes.toPlainText()

    def update_transition_notes(self):
        """Load notes for the current→next pair."""
        curr = self.current_index
        nxt = min(curr+1, len(self.ordered_items)-1)
        key = (self.ordered_items[curr]["title"],
               self.ordered_items[nxt]["title"])
        self.transition_notes.setPlainText(
            self.transition_notes_store.get(key, "")
        )

    def _init_queue_dock(self):
        dock = QDockWidget("Queue & Options", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea)
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(10,10,10,10)
        l.setSpacing(10)

        # Energy toggle
        chk = QPushButton("Show Energy Curve")
        chk.setCheckable(True)
        chk.toggled.connect(self.energy_canvas.setVisible)
        l.addWidget(chk)

        # Queue list
        self.lst = QListWidget()
        self.lst.setFont(QFont("Arial",14, QFont.Bold))
        self.lst.setAlternatingRowColors(True)
        self.lst.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        l.addWidget(self.lst)

        dock.setWidget(w)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        dock.setVisible(False)
        toggle = dock.toggleViewAction()
        toggle.setText("Show/Hide Queue")
        tb = self.addToolBar("View")
        tb.addAction(toggle)
        self.filter_queue_list()

    def filter_queue_list(self, text=""):
        """Rebuild and highlight current track."""
        self.lst.clear()
        q = text.lower()
        for i, tr in enumerate(self.ordered_items, start=1):
            title = tr["title"]
            if q and q not in title.lower():
                continue
            item = QListWidgetItem(f"{i}. {title}")
            item.setSizeHint(QSize(0,50))
            self.lst.addItem(item)
        # highlight current
        self.lst.setCurrentRow(self.current_index)
        curr_item = self.lst.currentItem()
        if curr_item:
            self.lst.scrollToItem(curr_item, QAbstractItemView.PositionAtCenter)


    def handle_request(self):
        query = self.req_input.text().strip().lower()
        if not query:
            return
        match = next((t for t in self.library_items
                      if query in t["title"].lower()), None)
        if not match:
            QMessageBox.warning(self, "Not found",
                                f"No track matching '{self.req_input.text()}'.")
            return

        curr = self.carousel.current_index
        new_bpm, new_key = match["bpm"], match["key"]

        # find global best
        global_idx, global_cost = None, float('inf')
        for i in range(curr+1, len(self.ordered_items)+1):
            prev = self.ordered_items[i-1]
            cost = abs(new_bpm - prev["bpm"]) + camelot_distance(new_key, prev["key"])
            if i < len(self.ordered_items):
                nxt = self.ordered_items[i]
                cost += abs(new_bpm - nxt["bpm"]) + camelot_distance(new_key, nxt["key"])
            if cost < global_cost:
                global_cost, global_idx = cost, i

        # find local best within MAX_LOOKAHEAD
        local_idx, local_cost = None, float('inf')
        for i in range(curr+1, min(curr+1+MAX_LOOKAHEAD, len(self.ordered_items))+1):
            prev = self.ordered_items[i-1]
            cost = abs(new_bpm - prev["bpm"]) + camelot_distance(new_key, prev["key"])
            if i < len(self.ordered_items):
                nxt = self.ordered_items[i]
                cost += abs(new_bpm - nxt["bpm"]) + camelot_distance(new_key, nxt["key"])
            if cost < local_cost:
                local_cost, local_idx = cost, i

        # compute distances/times
        g_dist = global_idx - curr
        g_secs = sum(t["duration"] for t in self.ordered_items[curr+1:global_idx+1])
        g_m, g_s = divmod(int(g_secs), 60)
        l_dist = local_idx - curr
        l_secs = sum(t["duration"] for t in self.ordered_items[curr+1:local_idx+1])
        l_m, l_s = divmod(int(l_secs), 60)

        # prompt choice
        msg = QMessageBox(self)
        msg.setWindowTitle("Choose insertion spot")
        msg.setText(
            f"Optimal spot: {g_dist} songs (≈{g_m}m{g_s}s)\n"
            f"Best within {MAX_LOOKAHEAD}: {l_dist} songs (≈{l_m}m{l_s}s)"
        )
        btn_local = msg.addButton(f"Insert in {l_dist}", QMessageBox.ActionRole)
        btn_global = msg.addButton(f"Insert in {g_dist}", QMessageBox.ActionRole)
        msg.addButton(QMessageBox.Cancel)
        msg.exec()
        choice = msg.clickedButton()
        if choice == btn_local:
            insert_idx, dist, mins, secs = local_idx, l_dist, l_m, l_s
        elif choice == btn_global:
            insert_idx, dist, mins, secs = global_idx, g_dist, g_m, g_s
        else:
            return

        confirm = QMessageBox.question(
            self, "Confirm",
            f"Insert '{match['title']}' in {dist} songs (≈{mins}m{secs}s)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        self.ordered_items.insert(insert_idx, match)
        self.carousel.set_items(self.ordered_items)
        self.filter_queue_list(self.queue_search.text())


def main():
    app = QApplication(sys.argv)
    url, ok = QInputDialog.getText(None, "Load Playlist",
                                   "Paste SoundCloud playlist URL:")
    if not ok or not url.strip():
        sys.exit(0)
    win = MainWindow(url.strip())
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()