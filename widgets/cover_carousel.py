# widgets/cover_carousel.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, QPropertyAnimation
from PySide6.QtGui import QPixmap, QFont
import requests

class CarouselItem(QWidget):
    """
    A square cover + metadata widget for a single track.
    Long titles/artists will wrap and push everything below.
    """
    def __init__(self, data, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        # fix the column width; height will expand
        self.setMaximumWidth(200)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # --- Cover image ---
        self.label_img = QLabel()
        self.label_img.setAlignment(Qt.AlignCenter)
        self.pixmap = QPixmap()
        try:
            resp = requests.get(data.get("thumbnail", ""), timeout=5)
            self.pixmap.loadFromData(resp.content)
        except Exception:
            pass
        # scaled square
        self.label_img.setPixmap(
            self.pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.label_img.setFixedSize(160, 160)
        layout.addWidget(self.label_img, alignment=Qt.AlignHCenter)

        # --- Title ---
        title_lbl = QLabel(data.get("title", ""))
        title_lbl.setFont(QFont("Arial", 18, QFont.Bold))
        title_lbl.setWordWrap(True)
        title_lbl.setAlignment(Qt.AlignCenter)
        # constrain to the same max width
        title_lbl.setMaximumWidth(200)
        layout.addWidget(title_lbl)

        # --- Artist ---
        artist_lbl = QLabel(data.get("artist", ""))
        artist_lbl.setFont(QFont("Arial", 14))
        artist_lbl.setWordWrap(True)
        artist_lbl.setAlignment(Qt.AlignCenter)
        artist_lbl.setMaximumWidth(200)
        layout.addWidget(artist_lbl)

        # --- BPM & Key ---
        meta_lbl = QLabel(f"{data.get('bpm')} BPM | {data.get('key')}")
        meta_lbl.setFont(QFont("Arial", 18, QFont.Bold))
        meta_lbl.setWordWrap(True)
        meta_lbl.setAlignment(Qt.AlignCenter)
        meta_lbl.setMaximumWidth(200)
        layout.addWidget(meta_lbl)

class CoverCarousel(QWidget):
    """
    Horizontal carousel that highlights both current and next tracks.
    """
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items
        self.current_index = 0

        self.setStyleSheet("background: transparent;")
        # scroll area setup
        self.scroll = QScrollArea()
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        # container for items
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.h_layout = QHBoxLayout(self.container)
        self.h_layout.setContentsMargins(20, 20, 20, 20)
        self.h_layout.setSpacing(40)

        # add items
        for d in items:
            self.h_layout.addWidget(CarouselItem(d))

        self.scroll.setWidget(self.container)

        # main layout
        main_l = QHBoxLayout(self)
        main_l.addWidget(self.scroll)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(260)

        # smooth-scroll animation
        self.anim = QPropertyAnimation(self.scroll.horizontalScrollBar(), b"value", self)
        self.anim.setDuration(300)

        # initial focus
        self.update_focus()

    def next(self):
        if self.current_index < len(self.items) - 1:
            self.current_index += 1
            self.update_focus()

    def previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_focus()

    def update_focus(self):
        count = self.h_layout.count()
        curr = self.current_index
        nxt = curr + 1 if curr + 1 < count else curr

        # resize covers
        for i in range(count):
            item = self.h_layout.itemAt(i).widget()
            side = 240 if i in (curr, nxt) else 160
            item.label_img.setPixmap(
                item.pixmap.scaled(side, side, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            item.label_img.setFixedSize(side, side)

        # center current+next
        w1 = self.h_layout.itemAt(curr).widget()
        w2 = self.h_layout.itemAt(nxt).widget()
        mid = (w1.x() + w2.x() + w2.width()) / 2
        vpw = self.scroll.viewport().width()
        tgt = int(mid - vpw / 2)

        start = self.scroll.horizontalScrollBar().value()
        self.anim.stop()
        self.anim.setStartValue(start)
        self.anim.setEndValue(max(0, tgt))
        self.anim.start()
    def set_items(self, items):
        """Replace the carousel’s items and refresh focus."""
        self.items = items
        # remove old widgets
        for i in reversed(range(self.h_layout.count())):
            w = self.h_layout.takeAt(i).widget()
            if w:
                w.setParent(None)
        # add new items
        for data in items:
            self.h_layout.addWidget(CarouselItem(data))
        # adjust current index if out of range
        self.current_index = min(self.current_index, len(items) - 1)
        self.update_focus()