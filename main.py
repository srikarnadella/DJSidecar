# main.py

import sys
import os
from PySide6.QtWidgets import QApplication, QInputDialog
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)

    # Load QSS if present
    qss = os.path.join(os.path.dirname(__file__), "ui", "styles.qss")
    if os.path.exists(qss):
        with open(qss) as f:
            app.setStyleSheet(f.read())

    # Prompt for SoundCloud playlist URL
    url, ok = QInputDialog.getText(None, "Load Playlist", "Paste SoundCloud playlist URL:")
    if not ok or not url.strip():
        sys.exit(0)

    window = MainWindow(url.strip())
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
