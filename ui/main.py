# ui/main.py
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout,
    QPushButton, QLabel, QFileDialog, QLineEdit, QGridLayout, QComboBox, QMessageBox, QProgressBar, QTextEdit, QHBoxLayout
)
from helpers import run_go_convert, run_go_loop, run_go_merge
from workers import BaseWorker
from functools import partial

class MergeMediaTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        layout = QGridLayout()

        # Input Video/Image Folder
        input_label = QLabel("🎬 Input Videos/Image Folder:")
        self.video_image_input_path = QLineEdit()
        video_image_input_browse_btn = QPushButton("Browse")
        video_image_input_browse_btn.clicked.connect(self.video_image_input_browse_folder)
        layout.addWidget(input_label, 0, 0)
        layout.addWidget(self.video_image_input_path, 0, 1)
        layout.addWidget(video_image_input_browse_btn, 0, 2)

        # Input Audio Folder
        audio_label = QLabel("🎵 Input Audio Folder:")
        self.audio_input_path = QLineEdit()
        audio_input_browse_btn = QPushButton("Browse")
        audio_input_browse_btn.clicked.connect(self.audio_input_browse_folder)
        layout.addWidget(audio_label, 1, 0)
        layout.addWidget(self.audio_input_path, 1, 1)
        layout.addWidget(audio_input_browse_btn, 1, 2)

        # Output Folder
        output_label = QLabel("📁 Output Folder:")
        self.output_path = QLineEdit()
        output_browse_btn = QPushButton("Browse")
        output_browse_btn.clicked.connect(self.output_browse_folder)
        layout.addWidget(output_label, 2, 0)
        layout.addWidget(self.output_path, 2, 1)
        layout.addWidget(output_browse_btn, 2, 2)

        # Duration and Format
        duration_label = QLabel("⏲️ Duration (sec) | 🎥 Format")
        self.duration_value_input = QLineEdit()
        self.duration_value_input.setPlaceholderText("Seconds")
        self.duration_value_input.setText("0")  # Default = 0
        layout.addWidget(duration_label, 3, 0)
        layout.addWidget(self.duration_value_input, 3, 1)

        self.format_combo = QComboBox()
        self.format_combo.setEditable(False)
        self.format_combo.addItems([".mp4", ".mov", ".mkv", ".avi"])
        layout.addWidget(self.format_combo, 3, 2)

        # Resolution and Bitrate (same row)
        resolution_label = QLabel("📺 Resolution | 📊 Bitrate")
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["1920x1080", "2560x1440", "3840x2160", "1280x720"])
        layout.addWidget(resolution_label, 4, 0)
        layout.addWidget(self.resolution_combo, 4, 1)

        self.bitrate_combo = QComboBox()
        self.bitrate_combo.setEditable(True)
        self.bitrate_combo.addItems(["1500k", "2000k", "4000k", "8000k"])
        layout.addWidget(self.bitrate_combo, 4, 2)

        # FPS and Mode (same row)
        fps_label = QLabel("🎥 FPS | 🔁 Mode")
        self.fps_combo = QComboBox()
        self.fps_combo.setEditable(True)
        self.fps_combo.addItems(["0", "24", "25", "29", "30", "60", "120", "240"])
        layout.addWidget(fps_label, 5, 0)
        layout.addWidget(self.fps_combo, 5, 1)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["gpu", "cpu"])
        layout.addWidget(self.mode_combo, 5, 2)

        # Merge Button
        self.convert_btn = QPushButton("🚀 Merge Now")
        self.convert_btn.clicked.connect(self.mergeFile)
        layout.addWidget(self.convert_btn, 6, 0, 1, 4)

        # Progress and Stop Button
        self.progress_bar = QProgressBar()
        self.stop_btn = QPushButton("🛑 Stop")
        self.stop_btn.clicked.connect(self.stop_worker)

        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar, 4)
        progress_layout.addWidget(self.stop_btn, 1)
        layout.addLayout(progress_layout, 7, 0, 1, 4)

        # Log Text
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text, 8, 0, 1, 4)

        self.setLayout(layout)

    def video_image_input_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Video/Image Folder")
        if folder:
            self.video_image_input_path.setText(folder)

    def audio_input_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Audio Folder")
        if folder:
            self.audio_input_path.setText(folder)

    def output_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path.setText(folder)

    def mergeFile(self):
        self.convert_btn.setEnabled(False)  # Vô hiệu hóa nút khi đang chạy
        video_image_input_path = self.video_image_input_path.text()
        audio_input_path = self.audio_input_path.text()
        output_folder = self.output_path.text()
        duration_value = self.duration_value_input.text()
        mode = self.mode_combo.currentText()
        
        self.worker = BaseWorker(
            partial(
                    run_go_merge,
                    input_video_image=video_image_input_path,
                    input_audio=audio_input_path,
                    output_path=output_folder,
                    resolution=self.resolution_combo.currentText(),
                    mode=mode,
                    duration=duration_value,
                    bitrate=self.bitrate_combo.currentText(),
                    fps=self.fps_combo.currentText(),
                )
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.on_merge_finished)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def append_log(self, message):
        self.log_text.append(message)

    def on_merge_finished(self, success):
        self.convert_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Thành công", "Đã Merge xong!")
        else:
            QMessageBox.warning(self, "Dừng / Lỗi", "Merge đã bị dừng hoặc có lỗi.")

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()

class LoopTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None  # Khởi tạo worker là None
        layout = QGridLayout()

        # Input Folder
        input_label = QLabel("🎬 Input Folder:")
        self.input_path = QLineEdit()
        input_browse_btn = QPushButton("Browse")
        input_browse_btn.clicked.connect(self.input_browse_folder)

        layout.addWidget(input_label, 0, 0)
        layout.addWidget(self.input_path, 0, 1)
        layout.addWidget(input_browse_btn, 0, 2)

        # Output Folder
        output_label = QLabel("📁 Output Folder:")
        self.output_path = QLineEdit()
        output_browse_btn = QPushButton("Browse")
        output_browse_btn.clicked.connect(self.output_browse_folder)

        layout.addWidget(output_label, 2, 0)
        layout.addWidget(self.output_path, 2, 1)
        layout.addWidget(output_browse_btn, 2, 2)

        # Loop Options (duration or count)
        loop_value_label = QLabel("🔁 Loop:")
        self.loop_value_input = QLineEdit()
        self.loop_value_input.setPlaceholderText("Số phút hoặc số lần")

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["duration", "count"])

        # Layout con cho input và combobox (50% - 50%)
        loop_layout = QHBoxLayout()
        loop_layout.addWidget(self.loop_value_input)
        loop_layout.addWidget(self.mode_combo)

        layout.addWidget(loop_value_label, 3, 0)
        layout.addLayout(loop_layout, 3, 1, 1, 2)

        # Loop button
        self.convert_btn = QPushButton("🚀 Loop Now")
        self.convert_btn.clicked.connect(self.loop_file)
        layout.addWidget(self.convert_btn, 4, 0, 1, 3)
        
        self.progress_bar = QProgressBar()
        self.stop_btn = QPushButton("🛑 Stop")
        self.stop_btn.clicked.connect(self.stop_worker)

        # Layout con chứa progress bar và stop button
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar, 4)  # 80%
        progress_layout.addWidget(self.stop_btn, 1)       # 20%
        layout.addLayout(progress_layout, 5, 0, 1, 3)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text, 6, 0, 1, 3)

        self.setLayout(layout)

    def input_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.input_path.setText(folder)

    def output_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path.setText(folder)

    def loop_file(self):
        self.convert_btn.setEnabled(False)  # Vô hiệu hóa nút khi đang chạy
        input_folder = self.input_path.text()
        output_folder = self.output_path.text()
        loop_value = self.loop_value_input.text()
        mode = self.mode_combo.currentText()
        
        self.worker = BaseWorker(
            partial(run_go_loop, 
                    input_path=input_folder, 
                    output_path=output_folder,
                    loop_value=loop_value,
                    mode=mode
                )
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.on_loop_finished)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def append_log(self, message):
        self.log_text.append(message)

    def on_loop_finished(self, success):
        self.convert_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Thành công", "Đã Loop xong!")
        else:
            QMessageBox.warning(self, "Dừng / Lỗi", "Loop đã bị dừng hoặc có lỗi.")

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()

class ConvertTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None  # Khởi tạo worker là None
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
        
        self.progress_bar = QProgressBar()
        self.stop_btn = QPushButton("🛑 Stop")
        self.stop_btn.clicked.connect(self.stop_worker)

        # Layout con chứa progress bar và stop button
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar, 4)  # 80%
        progress_layout.addWidget(self.stop_btn, 1)       # 20%
        layout.addLayout(progress_layout, 5, 0, 1, 3)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text, 6, 0, 1, 3)


        self.input_format_combo.currentTextChanged.connect(self.update_output_format)
        self.update_output_format()  # Initialize output formats based on default input format
        self.setLayout(layout)

    def update_output_format(self):
        video_formats = [".mp4", ".avi", ".mkv", ".mov", ".flv"]
        audio_formats = [".mp3", ".aac", ".wav", ".flac", ".m4a"]

        current_input = self.input_format_combo.currentText()

        if current_input in video_formats:
            formats = video_formats # if input is a video format
        elif current_input in audio_formats:
            formats = audio_formats # fallback to audio formats
        else:
            formats = video_formats + audio_formats # fallback to all formats

        # Update output format combo box
        self.output_format_combo.clear()
        self.output_format_combo.addItems(formats)

    def input_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.input_path.setText(folder)

    def output_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path.setText(folder)

    def convert_file(self):
        self.convert_btn.setEnabled(False)  # Vô hiệu hóa nút khi đang chạy
        input_folder = self.input_path.text()
        output_folder = self.output_path.text()
        input_ext = self.input_format_combo.currentText()
        output_ext = self.output_format_combo.currentText()
        
        self.worker = BaseWorker(
            partial(run_go_convert, input_path=input_folder, output_path=output_folder,
            input_ext=input_ext, output_ext=output_ext)
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.on_convert_finished)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def append_log(self, message):
        self.log_text.append(message)

    def on_convert_finished(self, success):
        self.convert_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Thành công", "Đã convert xong!")
        else:
            QMessageBox.warning(self, "Dừng / Lỗi", "Convert đã bị dừng hoặc có lỗi.")

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()

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
        self.tabs.addTab(LoopTab(), "Loop")
        self.tabs.addTab(MergeMediaTab(), "Merge Media")
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
