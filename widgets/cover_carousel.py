# widgets/cover_carousel.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, QPropertyAnimation
from PySide6.QtGui import QPixmap, QFont
import requests

NEON_GREEN = "#39FF14"


class CarouselItem(QWidget):
    """
    A cover + metadata widget for a single track.
    If no thumbnail URL is provided, shows a neon-green box.
    """
    def __init__(self, data, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        self.setMaximumWidth(200)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # Cover image or placeholder
        self.label_img = QLabel()
        self.label_img.setAlignment(Qt.AlignCenter)
        thumb = data.get("thumbnail")
        if thumb:
            self.pixmap = QPixmap()
            try:
                resp = requests.get(thumb, timeout=5)
                self.pixmap.loadFromData(resp.content)
            except Exception:
                self.pixmap = QPixmap()
            self.label_img.setPixmap(
                self.pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.label_img.setFixedSize(160, 160)
            self.label_img.setStyleSheet("background: transparent;")
        else:
            # neon-green placeholder
            self.pixmap = None
            self.label_img.setFixedSize(160, 160)
            self.label_img.setStyleSheet(
                f"background-color: {NEON_GREEN}; border-radius: 8px;"
            )
        layout.addWidget(self.label_img, alignment=Qt.AlignHCenter)

        # Title
        title_lbl = QLabel(data.get("title", ""))
        title_lbl.setFont(QFont("Arial", 16, QFont.Bold))
        title_lbl.setWordWrap(True)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setMaximumWidth(200)
        layout.addWidget(title_lbl)

        # Artist
        artist_lbl = QLabel(data.get("artist", ""))
        artist_lbl.setFont(QFont("Arial", 14))
        artist_lbl.setWordWrap(True)
        artist_lbl.setAlignment(Qt.AlignCenter)
        artist_lbl.setMaximumWidth(200)
        layout.addWidget(artist_lbl)

        # BPM & Key
        meta_lbl = QLabel(f"{data.get('bpm')} BPM | {data.get('key')}")
        meta_lbl.setFont(QFont("Arial", 14, QFont.Bold))
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

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        # Container & layout
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.h_layout = QHBoxLayout(self.container)
        self.h_layout.setContentsMargins(20, 20, 20, 20)
        self.h_layout.setSpacing(40)

        # Populate initial items
        for d in items:
            self.h_layout.addWidget(CarouselItem(d))

        self.scroll.setWidget(self.container)

        # Main layout
        main_l = QHBoxLayout(self)
        main_l.addWidget(self.scroll)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(260)

        # Smooth-scroll animation
        self.anim = QPropertyAnimation(self.scroll.horizontalScrollBar(), b"value", self)
        self.anim.setDuration(300)

        # Initial focus
        self.update_focus()

    def set_items(self, items):
        """
        Replace carousel contents with a new list of items.
        """
        self.items = items
        # Remove old widgets
        for i in reversed(range(self.h_layout.count())):
            w = self.h_layout.takeAt(i).widget()
            if w:
                w.setParent(None)
        # Add new widgets
        for d in items:
            self.h_layout.addWidget(CarouselItem(d))
        # Clamp current index
        self.current_index = min(self.current_index, len(items) - 1)
        # Refresh view
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

        # Resize covers
        for i in range(count):
            item = self.h_layout.itemAt(i).widget()
            size = 240 if i in (curr, nxt) else 160
            if item.pixmap:
                item.label_img.setPixmap(
                    item.pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            item.label_img.setFixedSize(size, size)

        # Center current+next
        w1 = self.h_layout.itemAt(curr).widget()
        w2 = self.h_layout.itemAt(nxt).widget()
        mid = (w1.x() + w2.x() + w2.width()) / 2
        vpw = self.scroll.viewport().width()
        target = int(mid - vpw / 2)

        start = self.scroll.horizontalScrollBar().value()
        self.anim.stop()
        self.anim.setStartValue(start)
        self.anim.setEndValue(max(0, target))
        self.anim.start()
