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
from utils.track_db import get_track_info, get_all_track_titles
from utils.setlist_order import hybrid_order, camelot_distance

# Optional Energy Curve imports
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

class MainWindow(QMainWindow):
    def __init__(self, playlist_url):
        super().__init__()
        self.setWindowTitle("DJ Sidecar")
        self.setMinimumSize(820, 600)

        # --- Main layout ---
        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # Header
        header = QLabel("DJ Sidecar")
        header.setFont(QFont("Arial", 24, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(header)

        # Fetch library items
        raw_tracks = fetch_sc_playlist_full(playlist_url)
        self.library_items = []
        for t in raw_tracks:
            title = t.get("title", "")
            artist = t.get("artist", "")
            bpm, key = get_track_info(title)
            duration = t.get("duration", 0) / 1000.0
            self.library_items.append({
                "thumbnail": t.get("thumbnail"),
                "title":     title,
                "artist":    artist,
                "bpm":       bpm or 0,
                "key":       key or "",
                "duration":  duration
            })

        # Hybrid ordering
        self.ordered_items = hybrid_order(self.library_items.copy())

        # Carousel
        self.carousel = CoverCarousel(self.ordered_items)
        self.carousel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_layout.addWidget(self.carousel)

        # Optional Energy Curve (hidden by default)
        bpm_vals = [item["bpm"] for item in self.ordered_items]
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

        # --- Bottom half split: Transition Notes | Song Request ---
        bottom = QWidget()
        bottom_l = QHBoxLayout(bottom)
        bottom_l.setContentsMargins(0,0,0,0)
        bottom_l.setSpacing(20)

        # Left: Transition Notes
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0,0,0,0)
        left_l.setSpacing(10)

        lbl_notes = QLabel("Transition Notes")
        lbl_notes.setFont(QFont("Arial", 16, QFont.Bold))
        left_l.addWidget(lbl_notes)

        self.transition_notes = QTextEdit()
        self.transition_notes.setPlaceholderText("Write transition notes here…")
        self.transition_notes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_l.addWidget(self.transition_notes)

        bottom_l.addWidget(left, stretch=3)

        # Right: Song Request
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0,0,0,0)
        right_l.setSpacing(10)

        lbl_req = QLabel("Song Request")
        lbl_req.setFont(QFont("Arial", 16, QFont.Bold))
        right_l.addWidget(lbl_req)

        # Autocomplete setup
        titles = get_all_track_titles()
        completer = QCompleter(titles)
        completer.setCaseSensitivity(Qt.CaseInsensitive)

        self.req_input = QLineEdit()
        self.req_input.setPlaceholderText("Type track name...")
        self.req_input.setCompleter(completer)
        right_l.addWidget(self.req_input)

        btn_add = QPushButton("Add Request")
        btn_add.clicked.connect(self.handle_request)
        right_l.addWidget(btn_add)

        right_l.addStretch()
        bottom_l.addWidget(right, stretch=2)

        self.main_layout.addWidget(bottom)

        # Navigation buttons
        nav = QHBoxLayout()
        nav.addStretch()
        btn_prev = QPushButton("⟵ Previous")
        btn_next = QPushButton("Next ⟶")
        btn_prev.clicked.connect(self.carousel.previous)
        btn_next.clicked.connect(self.carousel.next)
        nav.addWidget(btn_prev)
        nav.addWidget(btn_next)
        nav.addStretch()
        self.main_layout.addLayout(nav)

        self.setCentralWidget(container)

        # Side dock: Full Queue & Energy Toggle
        self._init_queue_dock()

    def _init_queue_dock(self):
        dock = QDockWidget("Queue & Options", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea)

        dock_w = QWidget()
        dock_l = QVBoxLayout(dock_w)
        dock_l.setContentsMargins(10,10,10,10)
        dock_l.setSpacing(15)

        # Energy toggle
        chk = QPushButton("Show Energy Curve")
        chk.setCheckable(True)
        chk.toggled.connect(self.energy_canvas.setVisible)
        dock_l.addWidget(chk)

        # Queue list
        self.lst = QListWidget()
        self.lst.setFont(QFont("Arial", 14, QFont.Bold))
        self.lst.setAlternatingRowColors(True)
        self.lst.setStyleSheet("""
            QListWidget { background: #2e2e2e; color: white; border: none; }
            QListWidget::item { margin: 8px; padding: 10px; }
            QListWidget::item:alternate { background: #2a2a2e; }
            QListWidget::item:selected { background: #5e5e5e; }
            QListWidget::item:hover { background: #444444; }
        """)
        self.lst.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        dock_l.addWidget(self.lst)

        dock.setWidget(dock_w)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        dock.setVisible(False)

        toggle = dock.toggleViewAction()
        toggle.setText("Show/Hide Queue")
        tb = self.addToolBar("View")
        tb.addAction(toggle)

        self.refresh_queue_list()

    def handle_request(self):
        query = self.req_input.text().strip().lower()
        if not query:
            return
        # 1) find the track in your library
        match = next((t for t in self.library_items
                      if query in t["title"].lower()), None)
        if not match:
            QMessageBox.warning(self, "Not found",
                                f"No track matching '{self.req_input.text()}'.")
            return

        curr = self.carousel.current_index

        # 2) score every insertion point after curr
        best_idx = None
        best_cost = float('inf')
        new_bpm = match['bpm']
        new_key = match['key']

        for i in range(curr+1, len(self.ordered_items)+1):
            # neighbor before insertion
            prev = self.ordered_items[i-1]
            cost = abs(new_bpm - prev['bpm']) + camelot_distance(new_key, prev['key'])
            # neighbor after insertion (if any)
            if i < len(self.ordered_items):
                nxt = self.ordered_items[i]
                cost += abs(new_bpm - nxt['bpm']) + camelot_distance(new_key, nxt['key'])
            if cost < best_cost:
                best_cost = cost
                best_idx = i

        # 3) compute how far away and approximate time
        dist = best_idx - curr
        secs = sum(t["duration"] for t in
                   self.ordered_items[curr+1:best_idx+1])
        mins, secs = divmod(int(secs), 60)

        # 4) confirmation dialog
        reply = QMessageBox.question(
            self, "Confirm Insertion",
            (f"Best fit for '{match['title']}' is in {dist} song(s) "
             f"(≈{mins}m {secs}s) from now.\n\nAdd it there?"),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # 5) perform insertion and refresh UI
        self.ordered_items.insert(best_idx, match)
        self.carousel.set_items(self.ordered_items)
        self.refresh_queue_list()

    def refresh_queue_list(self):
        self.lst.clear()
        for t in self.ordered_items:
            item = QListWidgetItem(t["title"])
            item.setSizeHint(QSize(0, 50))
            self.lst.addItem(item)
        # highlight & center current track
        curr_row = self.carousel.current_index
        self.lst.setCurrentRow(curr_row)
        current_item = self.lst.currentItem()
        if current_item:
            self.lst.scrollToItem(current_item, QAbstractItemView.PositionAtCenter)
