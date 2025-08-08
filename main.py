# ui/main.py
import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout,
    QPushButton, QLabel, QFileDialog, QLineEdit, QGridLayout, QComboBox, QMessageBox, QProgressBar, QTextEdit, QHBoxLayout, QSpinBox, QWidget, QGridLayout
)
from PyQt6.QtGui import QIcon
import pyperclip
from ui.helpers import run_go_convert, run_go_loop, run_go_merge, run_go_random_merge, run_go_extract_audio, run_go_videoScale
from ui.workers import BaseWorker
from functools import partial

class VideoScaleTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        layout = QGridLayout()

        # 🎬 Input Folder
        input_label = QLabel("🎬 Input Folder:")
        self.video_input_path = QLineEdit()
        video_input_browse_btn = QPushButton("Browse")
        video_input_browse_btn.clicked.connect(self.video_image_input_browse_folder)
        layout.addWidget(input_label, 0, 0)
        layout.addWidget(self.video_input_path, 0, 1)
        layout.addWidget(video_input_browse_btn, 0, 2)

        # 📁 Output Folder
        output_label = QLabel("📁 Output Folder:")
        self.output_path = QLineEdit()
        output_browse_btn = QPushButton("Browse")
        output_browse_btn.clicked.connect(self.output_browse_folder)
        layout.addWidget(output_label, 1, 0)
        layout.addWidget(self.output_path, 1, 1)
        layout.addWidget(output_browse_btn, 1, 2)

        # ⚙️ Output Format
        format_label = QLabel("🎞️ Output Format:")
        self.format_combo = QComboBox()
        self.format_combo.setEditable(False)
        self.format_combo.addItems([".mp4", ".mov", ".mkv", ".avi"])
        layout.addWidget(format_label, 2, 0)
        layout.addWidget(self.format_combo, 2, 1)

        # 📺 Resolution | 📊 Video Bitrate
        resolution_label = QLabel("📺 Resolution:📊 Video Bitrate")
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["1920:1080", "2560:1440", "3840:2160", "1280:720"])
        layout.addWidget(resolution_label, 3, 0)
        layout.addWidget(self.resolution_combo, 3, 1)

        self.bitrate_combo = QComboBox()
        self.bitrate_combo.setEditable(True)
        self.bitrate_combo.addItems(["1500k", "2000k", "4000k", "8000k"])
        layout.addWidget(self.bitrate_combo, 3, 2)

        # 🎧 Audio Bitrate | 🎥 FPS
        audio_bitrate_label = QLabel("🎧 Audio Bitrate:🎥 FPS")
        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.setEditable(True)
        self.audio_bitrate_combo.addItems(["128k", "192k", "160k", "96k", "256k", "320k"])
        layout.addWidget(audio_bitrate_label, 4, 0)
        layout.addWidget(self.audio_bitrate_combo, 4, 1)

        self.fps_combo = QComboBox()
        self.fps_combo.setEditable(True)
        self.fps_combo.addItems(["30", "24", "25", "60", "120"])
        layout.addWidget(self.fps_combo, 4, 2)

        # ⚙️ Preset | 🧠 Mode
        preset_label = QLabel("⚙️ Preset:🧠 Processing")
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["fast", "superfast", "veryfast", "ultrafast", "medium", "slow"])
        layout.addWidget(preset_label, 5, 0)
        layout.addWidget(self.preset_combo, 5, 1)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["gpu", "cpu"])
        layout.addWidget(self.mode_combo, 5, 2)

        # 🚀 Scale Button
        self.convert_btn = QPushButton("🚀 Scale Now")
        self.convert_btn.clicked.connect(self.mergeFile)
        layout.addWidget(self.convert_btn, 6, 0, 1, 4)

        # 📊 Progress and 🛑 Stop
        self.progress_bar = QProgressBar()
        self.stop_btn = QPushButton("🛑 Stop")
        self.stop_btn.clicked.connect(self.stop_worker)

        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar, 4)
        progress_layout.addWidget(self.stop_btn, 1)
        layout.addLayout(progress_layout, 7, 0, 1, 4)

        # 🧾 Log Output
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text, 8, 0, 1, 4)

        self.setLayout(layout)


    def video_image_input_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Video/Image Folder")
        if folder:
            self.video_input_path.setText(folder)


    def output_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path.setText(folder)

    def mergeFile(self):
        self.convert_btn.setEnabled(False)  # Vô hiệu hóa nút khi đang chạy
        video_input_path = self.video_input_path.text()
        output_folder = self.output_path.text()
        resolution = self.resolution_combo.currentText()
        mode = self.mode_combo.currentText()
        bitrate_combo = self.bitrate_combo.currentText()
        fps = self.fps_combo.currentText()
        audio_bitrate = self.audio_bitrate_combo.currentText()
        ext = self.format_combo.currentText()
        preset = self.preset_combo.currentText()
        
        self.worker = BaseWorker(
            partial(
                    run_go_videoScale,
                    input_path=video_input_path,
                    output_path=output_folder,
                    resolution=resolution,
                    mode=mode,
                    video_bitrate=bitrate_combo,
                    fps = fps,
                    audio_bitrate=audio_bitrate,
                    ext=ext,
                    preset=preset
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
        self.resolution_combo.addItems(["1920:1080", "2560:1440", "3840:2160", "1280:720"])
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

class MergeRandomTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        layout = QGridLayout()

        # Input Folder
        layout.addWidget(QLabel("🎬 Input Folder:"), 0, 0)
        self.input_path = QLineEdit()
        layout.addWidget(self.input_path, 0, 1)
        input_browse_btn = QPushButton("Browse")
        input_browse_btn.clicked.connect(self.input_browse_folder)
        layout.addWidget(input_browse_btn, 0, 2)

        # Output Folder
        layout.addWidget(QLabel("📁 Output Folder:"), 1, 0)
        self.output_path = QLineEdit()
        layout.addWidget(self.output_path, 1, 1)
        output_browse_btn = QPushButton("Browse")
        output_browse_btn.clicked.connect(self.output_browse_folder)
        layout.addWidget(output_browse_btn, 1, 2)

        # Input Count
        layout.addWidget(QLabel("📄 Input File Count:"), 2, 0)
        self.input_count_input = QSpinBox()
        self.input_count_input.setMinimum(0)
        layout.addWidget(self.input_count_input, 2, 1, 1, 2)

        # Output Count
        layout.addWidget(QLabel("📄 Output File Count:"), 3, 0)
        self.output_count_input = QSpinBox()
        self.output_count_input.setMinimum(1)
        layout.addWidget(self.output_count_input, 3, 1, 1, 2)

        # Merge button
        self.convert_btn = QPushButton("🚀 Merge now")
        self.convert_btn.clicked.connect(self.merge_random_folder)
        layout.addWidget(self.convert_btn, 4, 0, 1, 3)

        # Progress and Stop
        self.progress_bar = QProgressBar()
        self.stop_btn = QPushButton("🛑 Stop")
        self.stop_btn.clicked.connect(self.stop_worker)
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar, 4)
        progress_layout.addWidget(self.stop_btn, 1)
        layout.addLayout(progress_layout, 5, 0, 1, 3)

        # Log output
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

    def merge_random_folder(self):
        input_folder = self.input_path.text().strip()
        output_folder = self.output_path.text().strip()
        input_count = self.input_count_input.value()
        output_count = self.output_count_input.value()

        if not os.path.isdir(input_folder) or not os.path.isdir(output_folder):
            QMessageBox.warning(self, "Lỗi", "Hãy chọn thư mục hợp lệ.")
            return

        self.convert_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_text.clear()

        self.worker = self.worker = BaseWorker(
            partial(run_go_random_merge, 
                    input_path=input_folder, 
                    output_path=output_folder,
                    files_per_group=str(input_count),
                    num_outputs=str(output_count)
                )
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.on_convert_finished)
        self.worker.start()

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def append_log(self, message):
        self.log_text.append(message)

    def on_convert_finished(self, success):
        self.convert_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "✅ Thành công", "Đã merge xong!")
        else:
            QMessageBox.warning(self, "⚠️ Dừng / Lỗi", "Merge đã bị dừng hoặc xảy ra lỗi.")


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
        layout = QGridLayout()
        
        # Input
        input_label = QLabel("📜 Input Tracklist (mỗi dòng là 1 file):")
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Nhập đường dẫn các file (mỗi dòng 1 file) / Ctrl + Shift + C để copy đuờng dẫn từ file explorer")

        input_button_layout = QHBoxLayout()
        copy_input_btn = QPushButton("📋 Copy Input")
        copy_input_btn.clicked.connect(self.copy_input)
        input_button_layout.addWidget(copy_input_btn)

        layout.addWidget(input_label, 0, 0)
        layout.addWidget(self.input_text, 1, 0)
        layout.addLayout(input_button_layout, 2, 0)

        # Output
        output_label = QLabel("📄 Tracklist Output:")
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)

        output_button_layout = QHBoxLayout()
        copy_output_btn = QPushButton("📋 Copy")
        copy_output_btn.clicked.connect(self.copy_output)
        export_output_btn = QPushButton("💾 Export .txt")
        export_output_btn.clicked.connect(self.export_output)
        output_button_layout.addWidget(copy_output_btn)
        output_button_layout.addWidget(export_output_btn)

        layout.addWidget(output_label, 0, 1)
        layout.addWidget(self.output_text, 1, 1)
        layout.addLayout(output_button_layout, 2, 1)

        # Generate
        self.generate_btn = QPushButton("🚀 Generate Tracklist (HH:MM:SS)")
        self.generate_btn.clicked.connect(self.generate_tracklist)
        layout.addWidget(self.generate_btn, 3, 0, 1, 2)

        self.setLayout(layout)

    def copy_input(self):
        text = self.input_text.toPlainText()
        pyperclip.copy(text)

    def copy_output(self):
        text = self.output_text.toPlainText()
        pyperclip.copy(text)
    
    def export_output(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Lưu file tracklist", "", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.output_text.toPlainText())
                QMessageBox.information(self, "Thành công", "Đã lưu file tracklist!")
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", f"Không thể lưu file: {e}")
    
    def generate_tracklist(self):
        raw_text = self.input_text.toPlainText()
        paths = [line.strip().strip('"') for line in raw_text.splitlines() if line.strip()]
        if not paths:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng nhập ít nhất 1 đường dẫn.")
            return

        try:
            tracklist = self.build_tracklist(paths)
            self.output_text.setPlainText(tracklist)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi tạo tracklist:\n{e}")

    def build_tracklist(self, paths):
        lines = []
        current_time = 0.0

        for path in paths:
            duration = self.get_duration(path)
            start_time = self.seconds_to_hhmmss(current_time)
            filename = os.path.basename(path)
            name, _ = os.path.splitext(filename)
            line = f"{start_time} {name}"
            lines.append(line)
            current_time += duration

        return "\n".join(lines)

    def get_duration(self, path):
        project_dir = os.getcwd()
        ffprobe_path = os.path.join(project_dir, "assets", "ffmpeg", "ffprobe.exe")
        try:
            # Use ffprobe to get duration in seconds
            result = subprocess.run(
                [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return float(result.stdout.strip())
        except Exception as e:
            raise RuntimeError(f"Lỗi đọc thời lượng file: {path}\n{e}\n{ffprobe_path}")

    def seconds_to_hhmmss(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

class ExtractAudioTab(QWidget):
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

        # Output Format ComboBox
        output_format_label = QLabel("🎯 Output Format:")
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems([".mp3", ".aac", ".wav", ".flac", ".m4a"])
        layout.addWidget(output_format_label, 3, 0)
        layout.addWidget(self.output_format_combo, 3, 1, 1, 2)

        # Convert button
        self.convert_btn = QPushButton("🚀 Extract Now")
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
        self.convert_btn.setEnabled(False)  # Vô hiệu hóa nút khi đang chạy
        input_folder = self.input_path.text()
        output_folder = self.output_path.text()
        output_ext = self.output_format_combo.currentText()
        
        self.worker = BaseWorker(
            partial(run_go_extract_audio, input_folder=input_folder, output_folder=output_folder, output_ext=output_ext)
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
            QMessageBox.information(self, "Thành công", "Đã extract xong!")
        else:
            QMessageBox.warning(self, "Dừng / Lỗi", "extract đã bị dừng hoặc có lỗi.")

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(700, 400)
        self.setWindowTitle("Media Tools")
        self.setWindowIcon(QIcon("assets/icon.ico"))

        self.tabs = QTabWidget()
        self.tabs.addTab(LoopTab(), "Loop")
        self.tabs.addTab(ConvertTab(), "Convert")
        self.tabs.addTab(VideoScaleTab(), "Video Scale")
        self.tabs.addTab(ExtractAudioTab(), "Extract Audio")
        self.tabs.addTab(MergeMediaTab(), "Merge Media")
        self.tabs.addTab(MergeRandomTab(), "Merge Random")
        self.tabs.addTab(TracklistTab(), "Tracklist")

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
