# ui/main_window.py

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QSizePolicy,
    QDockWidget, QListWidget, QListWidgetItem,
    QLineEdit, QMessageBox, QCompleter, QAbstractItemView
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from widgets.cover_carousel import CoverCarousel
from utils.soundcloud_import import fetch_sc_playlist_full
from utils.track_db import (
    get_track_info, get_all_track_titles, get_all_tracks
)
from utils.setlist_order import hybrid_order, camelot_distance

# Matplotlib for energy curve
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

MAX_LOOKAHEAD = 10


class MainWindow(QMainWindow):
    def __init__(self, playlist_url):
        super().__init__()
        self.setWindowTitle("DJ Sidecar")
        self.setMinimumSize(820, 600)

        # Main container
        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # Header
        hdr = QLabel("DJ Sidecar")
        hdr.setFont(QFont("Arial", 24, QFont.Bold))
        hdr.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(hdr)

        # 1) Load full DB as library
        db_tracks = get_all_tracks()
        self.library_items = [
            {**t, "thumbnail": None, "duration": 0.0}
            for t in db_tracks
        ]

        # 2) Fetch current playlist & build active setlist
        raw = fetch_sc_playlist_full(playlist_url)
        playlist_items = []
        for t in raw:
            title = t.get("title", "")
            rec = next((x for x in self.library_items if x["title"] == title), None)
            bpm = rec["bpm"] if rec else None
            key = rec["key"] if rec else ""
            playlist_items.append({
                "thumbnail": t.get("thumbnail"),
                "title":     title,
                "artist":    t.get("artist", ""),
                "bpm":       bpm or 0,
                "key":       key or "",
                "duration":  t.get("duration", 0) / 1000.0
            })

        self.ordered_items = hybrid_order(playlist_items)

        # Carousel
        self.carousel = CoverCarousel(self.ordered_items)
        self.carousel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_layout.addWidget(self.carousel)

        # Energy curve (hidden)
        bpm_vals = [it["bpm"] for it in self.ordered_items]
        fig, ax = plt.subplots(figsize=(6,2), dpi=100)
        ax.plot(range(1, len(bpm_vals)+1), bpm_vals, marker="o")
        ax.set_title("Energy Curve (BPM)")
        ax.set_xlabel("Track Position")
        ax.set_ylabel("BPM")
        fig.tight_layout()
        self.energy_canvas = FigureCanvas(fig)
        self.energy_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.energy_canvas.setMinimumHeight(200)
        self.energy_canvas.setVisible(False)
        self.main_layout.addWidget(self.energy_canvas)

        # Bottom split: notes | request
        bottom = QWidget()
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(0,0,0,0)
        bl.setSpacing(20)

        # Transition Notes
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0,0,0,0)
        ll.setSpacing(10)
        lbln = QLabel("Transition Notes")
        lbln.setFont(QFont("Arial", 16, QFont.Bold))
        ll.addWidget(lbln)
        self.transition_notes = QTextEdit()
        self.transition_notes.setPlaceholderText("Write transition notes here…")
        self.transition_notes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        ll.addWidget(self.transition_notes)
        bl.addWidget(left, stretch=3)

        # Song Request
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0,0,0,0)
        rl.setSpacing(10)
        lblr = QLabel("Song Request")
        lblr.setFont(QFont("Arial", 16, QFont.Bold))
        rl.addWidget(lblr)

        # Autocomplete
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
        bl.addWidget(right, stretch=2)

        self.main_layout.addWidget(bottom)

        # Navigation buttons
        nav = QHBoxLayout()
        nav.addStretch()
        bprev = QPushButton("⟵ Previous")
        bnext = QPushButton("Next ⟶")
        bprev.clicked.connect(self.carousel.previous)
        bnext.clicked.connect(self.carousel.next)
        nav.addWidget(bprev)
        nav.addWidget(bnext)
        nav.addStretch()
        self.main_layout.addLayout(nav)

        self.setCentralWidget(container)
        self._init_queue_dock()

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

        # Queue search
        self.queue_search = QLineEdit()
        self.queue_search.setPlaceholderText("Search queue…")
        self.queue_search.textChanged.connect(self.filter_queue_list)
        l.addWidget(self.queue_search)

        # Numbered queue
        self.lst = QListWidget()
        self.lst.setFont(QFont("Arial", 14, QFont.Bold))
        self.lst.setAlternatingRowColors(True)
        self.lst.setStyleSheet("""
            QListWidget{background:#2e2e2e;color:white;border:none;}
            QListWidget::item{margin:8px;padding:10px;}
            QListWidget::item:alternate{background:#2a2e2e;}
            QListWidget::item:selected{background:#5e5e5e;}
            QListWidget::item:hover{background:#444444;}
        """)
        self.lst.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        l.addWidget(self.lst)

        dock.setWidget(w)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        dock.setVisible(False)

        toggle = dock.toggleViewAction()
        toggle.setText("Show/Hide Queue")
        tb = self.addToolBar("View")
        tb.addAction(toggle)

        self.filter_queue_list("")

    def filter_queue_list(self, text: str):
        self.lst.clear()
        q = text.lower()
        for idx, tr in enumerate(self.ordered_items):
            title = tr["title"]
            if q and q not in title.lower():
                continue
            item = QListWidgetItem(f"{idx+1}. {title}")
            item.setSizeHint(QSize(0,50))
            self.lst.addItem(item)
        # center current
        cur = self.carousel.current_index
        hits = self.lst.findItems(f"{cur+1}.", Qt.MatchStartsWith)
        if hits:
            self.lst.setCurrentItem(hits[0])
            self.lst.scrollToItem(hits[0], QAbstractItemView.PositionAtCenter)

    def handle_request(self):
        raw = self.req_input.text().strip().lower()
        if not raw:
            return
        # find in DB-library
        match = next((t for t in self.library_items
                      if raw in t["title"].lower()), None)
        if not match:
            QMessageBox.warning(self, "Not found",
                                f"No track matching '{self.req_input.text()}'.")
            return

        curr = self.carousel.current_index
        new_bpm, new_key = match["bpm"], match["key"]

        # 1) global best
        global_idx, global_cost = None, float('inf')
        for i in range(curr+1, len(self.ordered_items)+1):
            prev = self.ordered_items[i-1]
            cost = abs(new_bpm - prev["bpm"]) + camelot_distance(new_key, prev["key"])
            if i < len(self.ordered_items):
                nxt = self.ordered_items[i]
                cost += abs(new_bpm - nxt["bpm"]) + camelot_distance(new_key, nxt["key"])
            if cost < global_cost:
                global_cost, global_idx = cost, i

        # 2) local best within next MAX_LOOKAHEAD
        local_idx, local_cost = None, float('inf')
        for i in range(curr+1, min(curr+1+MAX_LOOKAHEAD, len(self.ordered_items))+1):
            prev = self.ordered_items[i-1]
            cost = abs(new_bpm - prev["bpm"]) + camelot_distance(new_key, prev["key"])
            if i < len(self.ordered_items):
                nxt = self.ordered_items[i]
                cost += abs(new_bpm - nxt["bpm"]) + camelot_distance(new_key, nxt["key"])
            if cost < local_cost:
                local_cost, local_idx = cost, i

        # times/distances
        g_dist = global_idx - curr
        g_secs = sum(t["duration"] for t in self.ordered_items[curr+1:global_idx+1])
        g_m, g_s = divmod(int(g_secs), 60)
        l_dist = local_idx - curr
        l_secs = sum(t["duration"] for t in self.ordered_items[curr+1:local_idx+1])
        l_m, l_s = divmod(int(l_secs), 60)

        # Prompt with two buttons
        msg = QMessageBox(self)
        msg.setWindowTitle("Choose insertion spot")
        msg.setText(
            f"Optimal spot for '{match['title']}' is in {g_dist} songs (≈{g_m}m{g_s}s).\n"
            f"Best within next {MAX_LOOKAHEAD} is in {l_dist} songs (≈{l_m}m{l_s}s)."
        )
        btn_local = msg.addButton(f"Insert in {l_dist}", QMessageBox.ActionRole)
        btn_global = msg.addButton(f"Insert in {g_dist}", QMessageBox.ActionRole)
        msg.addButton(QMessageBox.Cancel)
        msg.exec()

        choice = msg.clickedButton()
        if choice == btn_local:
            insert_idx = local_idx
            dist, mins, secs = l_dist, l_m, l_s
        elif choice == btn_global:
            insert_idx = global_idx
            dist, mins, secs = g_dist, g_m, g_s
        else:
            return  # canceled

        # Final confirmation
        final = QMessageBox.question(
            self, "Confirm",
            f"Insert '{match['title']}' in {dist} songs (≈{mins}m{secs}s)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if final != QMessageBox.Yes:
            return

        # Insert and refresh
        self.ordered_items.insert(insert_idx, match)
        self.carousel.set_items(self.ordered_items)
        self.filter_queue_list(self.queue_search.text())
