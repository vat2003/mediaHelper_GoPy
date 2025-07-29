# ui/main.py
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout,
    QPushButton, QLabel, QFileDialog, QLineEdit, QGridLayout
)
from helpers import run_go_convert

class ConvertTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QGridLayout()

        # Input
        input_label = QLabel("🎬 Input File:")
        self.input_path = QLineEdit()
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_file)

        layout.addWidget(input_label, 0, 0)
        layout.addWidget(self.input_path, 0, 1)
        layout.addWidget(browse_btn, 0, 2)

        # Output
        output_label = QLabel("📁 Output File:")
        self.output_path = QLineEdit("output.flv")
        layout.addWidget(output_label, 1, 0)
        layout.addWidget(self.output_path, 1, 1, 1, 2)

        # Convert button
        self.convert_btn = QPushButton("🚀 Convert Now")
        self.convert_btn.clicked.connect(self.convert_file)
        layout.addWidget(self.convert_btn, 2, 0, 1, 3)

        self.setLayout(layout)

    def browse_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file:
            self.input_path.setText(file)

    def convert_file(self):
        run_go_convert(self.input_path.text(), self.output_path.text())

class TracklistTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("👉 Đây là tab tạo Tracklist"))
        self.setLayout(layout)


class DownloadTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("📥 Đây là tab Download (sử dụng gdown)"))
        self.setLayout(layout)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎧 MediaHelper")
        # self.resize(600, 400)

        self.tabs = QTabWidget()
        self.tabs.addTab(ConvertTab(), "Convert")
        self.tabs.addTab(TracklistTab(), "Tracklist")
        self.tabs.addTab(DownloadTab(), "Download")

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
