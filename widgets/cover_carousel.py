# widgets/cover_carousel.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, QPropertyAnimation, Signal
from PySide6.QtGui import QPixmap, QFont
import requests

NEON_GREEN = "#39FF14"

class CarouselItem(QWidget):
    """
    A cover + metadata widget for a single track.
    If no thumbnail URL is provided, shows a neon-green placeholder.
    """
    def __init__(self, data, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5,5,5,5)
        layout.setSpacing(8)

        # fix column width; let height expand
        self.setMaximumWidth(200)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # --- Cover or placeholder ---
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
                self.pixmap.scaled(160,160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.label_img.setFixedSize(160,160)
            self.label_img.setStyleSheet("background: transparent;")
        else:
            self.pixmap = None
            self.label_img.setFixedSize(160,160)
            self.label_img.setStyleSheet(
                f"background-color: {NEON_GREEN}; border-radius: 8px;"
            )
        layout.addWidget(self.label_img, alignment=Qt.AlignHCenter)

        # --- Title ---
        lbl = QLabel(data.get("title",""))
        lbl.setFont(QFont("Arial",16, QFont.Bold))
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setMaximumWidth(200)
        layout.addWidget(lbl)

        # --- Artist ---
        lbl2 = QLabel(data.get("artist",""))
        lbl2.setFont(QFont("Arial",14))
        lbl2.setWordWrap(True)
        lbl2.setAlignment(Qt.AlignCenter)
        lbl2.setMaximumWidth(200)
        layout.addWidget(lbl2)

        # --- BPM & Key ---
        meta = QLabel(f"{data.get('bpm')} BPM | {data.get('key')}")
        meta.setFont(QFont("Arial",14, QFont.Bold))
        meta.setWordWrap(True)
        meta.setAlignment(Qt.AlignCenter)
        meta.setMaximumWidth(200)
        layout.addWidget(meta)


class CoverCarousel(QWidget):
    """
    Horizontal carousel that highlights current+next tracks.
    Emits indexChanged(int) whenever current track moves.
    """
    indexChanged = Signal(int)

    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items
        self.current_index = 0

        # transparent background
        self.setStyleSheet("background: transparent;")

        # scroll area
        self.scroll = QScrollArea()
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        # container & layout
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.h_layout = QHBoxLayout(self.container)
        self.h_layout.setContentsMargins(20,20,20,20)
        self.h_layout.setSpacing(40)

        # populate
        for d in items:
            self.h_layout.addWidget(CarouselItem(d))

        self.scroll.setWidget(self.container)

        # main layout
        main_l = QHBoxLayout(self)
        main_l.addWidget(self.scroll)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(260)

        # animation for smooth scrolling
        self.anim = QPropertyAnimation(self.scroll.horizontalScrollBar(), b"value", self)
        self.anim.setDuration(300)

        # initial focus
        self.update_focus()

    def set_items(self, items):
        """Replace carousel contents and re-focus."""
        self.items = items
        # clear
        for i in reversed(range(self.h_layout.count())):
            w = self.h_layout.takeAt(i).widget()
            if w:
                w.setParent(None)
        # add new
        for d in items:
            self.h_layout.addWidget(CarouselItem(d))
        # clamp index
        self.current_index = min(self.current_index, len(items)-1)
        self.update_focus()

    def next(self):
        if self.current_index < len(self.items)-1:
            self.current_index += 1
            self.update_focus()
            self.indexChanged.emit(self.current_index)

    def previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_focus()
            self.indexChanged.emit(self.current_index)

    def update_focus(self):
        count = self.h_layout.count()
        curr = self.current_index
        nxt = curr+1 if curr+1<count else curr

        # resize covers
        for i in range(count):
            item = self.h_layout.itemAt(i).widget()
            size = 240 if i in (curr,nxt) else 160
            if item.pixmap:
                item.label_img.setPixmap(
                    item.pixmap.scaled(size,size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            item.label_img.setFixedSize(size, size)

        # center current+next
        w1 = self.h_layout.itemAt(curr).widget()
        w2 = self.h_layout.itemAt(nxt).widget()
        mid = (w1.x() + w2.x() + w2.width())/2
        vpw = self.scroll.viewport().width()
        tgt = int(mid - vpw/2)

        start = self.scroll.horizontalScrollBar().value()
        self.anim.stop()
        self.anim.setStartValue(start)
        self.anim.setEndValue(max(0,tgt))
        self.anim.start()
