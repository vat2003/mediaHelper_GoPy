# ui/main.py
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout,
    QPushButton, QLabel, QFileDialog, QLineEdit, QGridLayout, QComboBox, QMessageBox
)
from helpers import run_go_convert

class ConvertTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QGridLayout()

        # Input Folder
        input_label = QLabel("🎬 Input Folder:")
        self.input_path = QLineEdit()
        input_browse_btn = QPushButton("Browse")
        input_browse_btn.clicked.connect(self.input_browse_folder)

        layout.addWidget(input_label, 0, 0)
        layout.addWidget(self.input_path, 0, 1)
        layout.addWidget(input_browse_btn, 0, 2)

        # Input Format ComboBox
        input_format_label = QLabel("🎞 Input Format:")
        self.input_format_combo = QComboBox()
        self.input_format_combo.addItems([".mp4", ".mkv", ".avi", ".mov", ".mp3", ".wav", ".aac", ".flac"])
        layout.addWidget(input_format_label, 1, 0)
        layout.addWidget(self.input_format_combo, 1, 1, 1, 2)

        # Output Folder
        output_label = QLabel("📁 Output Folder:")
        self.output_path = QLineEdit()
        output_browse_btn = QPushButton("Browse")
        output_browse_btn.clicked.connect(self.output_browse_folder)

        layout.addWidget(output_label, 2, 0)
        layout.addWidget(self.output_path, 2, 1)
        layout.addWidget(output_browse_btn, 2, 2)

        # Output Format ComboBox
        output_format_label = QLabel("🎯 Output Format:")
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems([".mp4", ".avi", ".mkv", ".mp3", ".aac", ".wav", ".flv"])
        layout.addWidget(output_format_label, 3, 0)
        layout.addWidget(self.output_format_combo, 3, 1, 1, 2)

        # Convert button
        self.convert_btn = QPushButton("🚀 Convert Now")
        self.convert_btn.clicked.connect(self.convert_file)
        layout.addWidget(self.convert_btn, 4, 0, 1, 3)

        self.setLayout(layout)

    def input_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.input_path.setText(folder)

    def output_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path.setText(folder)

    def convert_file(self):
        input_folder = self.input_path.text()
        output_folder = self.output_path.text()
        input_ext = self.input_format_combo.currentText()
        output_ext = self.output_format_combo.currentText()
        try:
            success = run_go_convert(input_folder, output_folder, input_ext, output_ext)
            if success:
                QMessageBox.information(self, "Success", "Convert thành công!")
            else:
                QMessageBox.critical(self, "Failed", "Convert thất bại! Kiểm tra lại đầu vào hoặc định dạng.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Đã xảy ra lỗi: {str(e)}")

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
