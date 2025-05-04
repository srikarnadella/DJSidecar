# main.py

import sys, os
from PySide6.QtWidgets import QApplication, QInputDialog
from ui.main_window import MainWindow

def load_styles(app):
    qss_path = os.path.join(os.path.dirname(__file__), "ui", "styles.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r") as f:
            app.setStyleSheet(f.read())

def main():
    app = QApplication(sys.argv)
    load_styles(app)

    # Prompt for SoundCloud playlist URL
    url, ok = QInputDialog.getText(None, "Load Playlist", "Paste SoundCloud playlist URL:")
    if not ok or not url.strip():
        sys.exit(0)

    window = MainWindow(url.strip())
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
