# ui/main.py
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout,
    QPushButton, QLabel, QFileDialog, QLineEdit, QGridLayout, QComboBox, QMessageBox, QProgressBar, QTextEdit, QHBoxLayout, QSpinBox, QWidget, QGridLayout
)
import requests
import zipfile
import json
from PyQt6.QtGui import QIcon
import pyperclip
from helpers import run_go_convert, run_go_loop, run_go_merge, run_go_random_merge, run_go_extract_audio, run_go_videoScale, get_duration_ffmpeg, run_go_rename, run_go_concatFromPaths
from ui.workers import BaseWorker
from functools import partial

import requests, json, zipfile, os, sys, subprocess
from packaging import version
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox, QProgressDialog

APP_VERSION = "1.2.4"  # Phiên bản hiện tại

class UpdateTab(QWidget):
    def __init__(self):
        super().__init__()
        self.vlayout = QVBoxLayout()

        self.info_label = QLabel(f"Phiên bản hiện tại: {APP_VERSION}")
        self.vlayout.addWidget(self.info_label)

        self.changelog = QTextEdit()
        self.changelog.setReadOnly(True)
        self.vlayout.addWidget(self.changelog)

        self.check_btn = QPushButton("🔍 Kiểm tra cập nhật")
        self.check_btn.clicked.connect(self.check_update)
        self.vlayout.addWidget(self.check_btn)

        self.setLayout(self.vlayout)

    def check_update(self):
        try:
            url = "https://www.dropbox.com/scl/fi/yarg0yov0vduaxnyeld1g/version.json?rlkey=drpnxt1rurxl9fg45wpg7uyye&st=9kvrskqz&dl=1"
            resp = requests.get(url, timeout=5)
            data = json.loads(resp.text)

            latest_version = data["version"]
            download_url = data["url"]
            changelog = data.get("changelog", "")

            self.changelog.setPlainText(changelog)

            if version.parse(latest_version) > version.parse(APP_VERSION):
                reply = QMessageBox.question(
                    self.window(),
                    "Có bản cập nhật mới",
                    f"Phiên bản mới: {latest_version}\nBạn có muốn tải và cập nhật không?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.download_and_update(download_url)
            else:
                QMessageBox.information(self.window(), "Thông báo", "Bạn đang dùng phiên bản mới nhất.")
        except Exception as e:
            QMessageBox.warning(self.window(), "Lỗi", f"Không thể kiểm tra cập nhật:\n{e}")

    def download_and_update(self, url):
        try:
            zip_path = "update.zip"

            # Hiển thị tiến trình tải
            resp = requests.get(url, stream=True)
            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0

            progress = QProgressDialog("Đang tải bản cập nhật...", "Hủy", 0, 100, self)
            progress.setWindowTitle("Cập nhật")
            progress.setValue(0)
            progress.show()

            with open(zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress.setValue(int(downloaded / total_size * 100))
                        if progress.wasCanceled():
                            return

            # Giải nén vào thư mục tạm
            extract_dir = "update_temp"
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            os.remove(zip_path)

            # Tạo file batch để ghi đè sau khi thoát
            batch_content = f"""
                @echo off
                timeout /t 2 /nobreak >nul
                xcopy "{extract_dir}" "{os.getcwd()}" /E /H /Y
                rmdir /S /Q "{extract_dir}"
                start "" "{sys.executable}"
                            """

            batch_file = "update.bat"
            with open(batch_file, "w", encoding="utf-8") as f:
                f.write(batch_content)

            QMessageBox.information(self.window(), "Hoàn tất", "Ứng dụng sẽ tự cập nhật khi bạn đóng.")
            subprocess.Popen(["cmd", "/c", batch_file])
            sys.exit(0)

        except Exception as e:
            QMessageBox.warning(self.window(), "Lỗi", f"Cập nhật thất bại:\n{e}")


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
        self.format_combo.addItems([".mp4", ".mov", ".avi", ".flv", ".mkv"])
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
            QMessageBox.information(self.window(), "Thành công", "Đã Scale xong!")
        else:
            QMessageBox.warning(self.window(), "Dừng / Lỗi", "Scale đã bị dừng hoặc có lỗi.")

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
        self.format_combo.addItems([".mp4", ".mov", ".avi"])
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
            QMessageBox.information(self.window(), "Thành công", "Đã Merge xong!")
        else:
            QMessageBox.warning(self.window(), "Dừng / Lỗi", "Merge đã bị dừng hoặc có lỗi.")

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
        self.input_count_input.setMaximum(999999)
        layout.addWidget(self.input_count_input, 2, 1, 1, 2)

        # Output Count
        layout.addWidget(QLabel("📄 Output File Count:"), 3, 0)
        self.output_count_input = QSpinBox()
        self.output_count_input.setMinimum(1)
        self.output_count_input.setMaximum(999999)
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
            QMessageBox.warning(self.window(), "Lỗi", "Hãy chọn thư mục hợp lệ.")
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
            QMessageBox.information(self.window(), "✅ Thành công", "Đã merge xong!")
        else:
            QMessageBox.warning(self.window(), "⚠️ Dừng / Lỗi", "Merge đã bị dừng hoặc xảy ra lỗi.")


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

        # Concurrent Files
        concurrent_label = QLabel("📂 Số file xử lý đồng thời:")
        self.concurrent_input = QSpinBox()
        self.concurrent_input.setMinimum(1)
        self.concurrent_input.setMaximum(3)
        

        layout.addWidget(concurrent_label, 4, 0)
        layout.addWidget(self.concurrent_input, 4, 1, 1, 2)

        # Loop button
        self.convert_btn = QPushButton("🚀 Loop Now")
        self.convert_btn.clicked.connect(self.loop_file)
        layout.addWidget(self.convert_btn, 5, 0, 1, 3)
        
        self.progress_bar = QProgressBar()
        self.stop_btn = QPushButton("🛑 Stop")
        self.stop_btn.clicked.connect(self.stop_worker)

        # Layout con chứa progress bar và stop button
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar, 4)  # 80%
        progress_layout.addWidget(self.stop_btn, 1)       # 20%
        layout.addLayout(progress_layout, 6, 0, 1, 3)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text, 7, 0, 1, 3)

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
        concurrent_files = self.concurrent_input.text()
        
        self.worker = BaseWorker(
            partial(run_go_loop, 
                    input_path=input_folder, 
                    output_path=output_folder,
                    loop_value=loop_value,
                    mode=mode,
                    concurrency=int(concurrent_files)
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
            QMessageBox.information(self.window(), "Thành công", "Đã Loop xong!")
        else:
            QMessageBox.warning(self.window(), "Dừng / Lỗi", "Loop đã bị dừng hoặc có lỗi.")

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
        self.input_format_combo.addItems([".mp4", ".avi", ".mov", ".mp3", ".wav", ".aac", ".flac"])
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
        self.output_format_combo.addItems([".mp4", ".avi", ".mp3", ".aac", ".wav", ".flv", ".m4a", ".flac"])
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
        video_formats = [".mp4", ".avi", ".mov", ".flv"]
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
            QMessageBox.information(self.window(), "Thành công", "Đã convert xong!")
        else:
            QMessageBox.warning(self.window(), "Dừng / Lỗi", "Convert đã bị dừng hoặc có lỗi.")

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()

class TracklistTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None

        layout = QGridLayout()
        
        # ========== Input ==========
        input_label = QLabel("📜 Input Tracklist (mỗi dòng là 1 file):")
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText(
            "Nhập đường dẫn các file (mỗi dòng 1 file)\n"
            "Mẹo: Ctrl + Shift + C để copy đường dẫn từ File Explorer"
        )

        input_button_layout = QHBoxLayout()
        copy_input_btn = QPushButton("📋 Copy Input")
        copy_input_btn.clicked.connect(self.copy_input)
        input_button_layout.addWidget(copy_input_btn)

        layout.addWidget(input_label, 0, 0)
        layout.addWidget(self.input_text, 1, 0)
        layout.addLayout(input_button_layout, 2, 0)

        # ========== Output (tracklist preview) ==========
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

        # ========== Concat controls ==========
        # concat_label = QLabel("🧩 Concat từ Input Tracklist")
        # layout.addWidget(concat_label, 3, 0, 1, 2)

        # Output folder cho concat
        of_label = QLabel("📁 Output Folder:")
        self.concat_output_dir = QLineEdit()
        of_browse = QPushButton("Browse")
        of_browse.clicked.connect(self.browse_concat_output)

        of_row = QHBoxLayout()
        of_row.addWidget(self.concat_output_dir, 1)
        of_row.addWidget(of_browse)

        layout.addWidget(of_label, 3, 0)
        layout.addLayout(of_row, 3, 1)

        # Nút Concat
        self.concat_btn = QPushButton("🧩 Concat từ Input Tracklist")
        self.concat_btn.clicked.connect(self.concat_from_input)
        layout.addWidget(self.concat_btn, 4, 0, 1, 2)

        # ========== Generate tracklist (HH:MM:SS) ==========
        self.generate_btn = QPushButton("🚀 Generate Tracklist (HH:MM:SS)")
        self.generate_btn.clicked.connect(self.generate_tracklist)
        layout.addWidget(self.generate_btn, 5, 0, 1, 2)

        self.setLayout(layout)

    # ---------- Helpers ----------
    def _get_input_paths(self):
        raw_text = self.input_text.toPlainText()
        paths = [line.strip().strip('"') for line in raw_text.splitlines() if line.strip()]
        return paths

    # ---------- Buttons ----------
    def copy_input(self):
        pyperclip.copy(self.input_text.toPlainText())

    def copy_output(self):
        pyperclip.copy(self.output_text.toPlainText())
    
    def export_output(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Lưu file tracklist", "", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.output_text.toPlainText())
                QMessageBox.information(self.window(), "Thành công", "Đã lưu file tracklist!")
            except Exception as e:
                QMessageBox.warning(self.window(), "Lỗi", f"Không thể lưu file: {e}")

    def browse_concat_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục xuất concat")
        if folder:
            self.concat_output_dir.setText(folder)

    # ---------- Generate Tracklist ----------
    def generate_tracklist(self):
        paths = self._get_input_paths()
        if not paths:
            QMessageBox.warning(self.window(), "Thiếu dữ liệu", "Vui lòng nhập ít nhất 1 đường dẫn.")
            return

        try:
            tracklist = self.build_tracklist(paths)
            self.output_text.setPlainText(tracklist)
        except Exception as e:
            QMessageBox.critical(self.window(), "Lỗi", f"Lỗi khi tạo tracklist:\n{e}")

    def build_tracklist(self, paths):
        lines = []
        current_time = 0.0
        for path in paths:
            duration = get_duration_ffmpeg(path)
            start_time = self.seconds_to_hhmmss(current_time)
            filename = os.path.basename(path)
            name, _ = os.path.splitext(filename)
            lines.append(f"[{start_time}] {name}")
            current_time += duration
        return "\n".join(lines)

    def seconds_to_hhmmss(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    # ---------- Concat ----------
    def concat_from_input(self):
        self.output_text.clear()  # Xoá output text cũ (nếu có)
         # Lấy danh sách đường dẫn từ input
        paths = self._get_input_paths()
        if not paths:
            QMessageBox.warning(self.window(), "Thiếu dữ liệu", "Vui lòng nhập ít nhất 1 đường dẫn.")
            return

        out_dir = self.concat_output_dir.text().strip()
        if not out_dir:
            QMessageBox.warning(self.window(), "Thiếu Output", "Vui lòng chọn Output Folder để xuất file concat.")
            return

        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self.window(), "Lỗi", f"Không tạo được thư mục output:\n{e}")
            return

        # Disable button khi đang chạy
        self.concat_btn.setEnabled(False)

        # Gọi worker chạy go_concatPaths.exe qua helpers
        self.worker = BaseWorker(partial(run_go_concatFromPaths, output_folder=out_dir, paths=paths))
        self.worker.finished.connect(self.on_concat_finished)
        # Nếu muốn xem log concat đổ vào output_text:
        self.worker.log.connect(self._append_concat_log)
        self.worker.start()

    def _append_concat_log(self, msg: str):
        # Đẩy log concat vào cuối ô output (không ghi đè tracklist sẵn có)
        cur = self.output_text.toPlainText()
        self.output_text.setPlainText((cur + ("\n" if cur else "") + msg).strip())

    def on_concat_finished(self, success: bool):
        self.concat_btn.setEnabled(True)
        if success:
            QMessageBox.information(self.window(), "✅ Thành công", "Đã concat xong!")
        else:
            QMessageBox.warning(self.window(), "⚠️ Dừng / Lỗi", "Concat đã bị dừng hoặc xảy ra lỗi.")

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
            QMessageBox.information(self.window(), "Thành công", "Đã extract xong!")
        else:
            QMessageBox.warning(self.window(), "Dừng / Lỗi", "extract đã bị dừng hoặc có lỗi.")

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()

class RenameTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        layout = QGridLayout()

        # Input Folder
        input_label = QLabel("🎬 Input Folder:")
        self.input_path = QLineEdit()
        input_browse_btn = QPushButton("Browse")
        input_browse_btn.clicked.connect(self.input_browse_folder)
        layout.addWidget(input_label, 0, 0)
        layout.addWidget(self.input_path, 0, 1)
        layout.addWidget(input_browse_btn, 0, 2)

        # Prefix | Suffix
        layout.addWidget(QLabel("🔤 Prefix:"), 2, 0)
        self.prefix_input = QLineEdit()
        layout.addWidget(self.prefix_input, 2, 1, 1, 2)

        layout.addWidget(QLabel("🔤 Suffix:"), 3, 0)
        self.suffix_input = QLineEdit()
        layout.addWidget(self.suffix_input, 3, 1, 1, 2)

        # Remove Characters
        layout.addWidget(QLabel("❌ Remove Characters:"), 4, 0)
        self.remove_input = QLineEdit()
        self.remove_input.setPlaceholderText("Ví dụ: t,s,a")
        layout.addWidget(self.remove_input, 4, 1, 1, 2)

        # Rename Button
        self.convert_btn = QPushButton("🚀 Rename Now")
        self.convert_btn.clicked.connect(self.rename_files)
        layout.addWidget(self.convert_btn, 5, 0, 1, 3)

        # Progress + Stop
        self.progress_bar = QProgressBar()
        self.stop_btn = QPushButton("🛑 Stop")
        self.stop_btn.setEnabled(False)  # mặc định disable
        self.stop_btn.clicked.connect(self.stop_worker)

        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar, 4)
        progress_layout.addWidget(self.stop_btn, 1)
        layout.addLayout(progress_layout, 6, 0, 1, 3)

        # Log Output
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text, 7, 0, 1, 3)

        self.setLayout(layout)

    def input_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.input_path.setText(folder)

    def rename_files(self):
        self.convert_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        input_folder = self.input_path.text().strip()
        prefix = self.prefix_input.text().strip()
        suffix = self.suffix_input.text().strip()
        remove_chars = self.remove_input.text().strip()

        if not os.path.isdir(input_folder):
            QMessageBox.warning(self.window(), "Lỗi", "Input folder không hợp lệ.")
            self.convert_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            return

        # chuẩn hóa remove_chars: "t,s,a" -> "tsa"
        if "," in remove_chars:
            remove_chars = remove_chars.replace(",", "")

        self.progress_bar.setValue(0)
        self.log_text.clear()

        self.worker = BaseWorker(
            partial(
                run_go_rename,
                input_path=input_folder,
                prefix=prefix,
                suffix=suffix,
                remove_chars=remove_chars,
            )
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.on_rename_finished)
        self.worker.start()

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def append_log(self, message):
        self.log_text.append(message)

    def on_rename_finished(self, success):
        self.convert_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if success:
            QMessageBox.information(self.window(), "✅ Thành công", "Đã rename xong!")
        else:
            QMessageBox.warning(self.window(), "⚠️ Dừng / Lỗi", "Rename đã bị dừng hoặc có lỗi.")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(800, 400)
        self.setWindowTitle("Media Tools")
        # Kiểm tra đường dẫn tới file icon
        if os.path.exists("assets/icon.ico"):
            icon_path = "assets/icon.ico"
        elif os.path.exists("_internal/assets/icon.ico"):
            icon_path = "_internal/assets/icon.ico"
        else:
            icon_path = None  # Hoặc đặt một icon mặc định, hoặc không đặt icon
        self.setWindowIcon(QIcon(icon_path))

        self.tabs = QTabWidget()
        self.tabs.addTab(LoopTab(), "Loop")
        self.tabs.addTab(ConvertTab(), "Convert")
        self.tabs.addTab(VideoScaleTab(), "Video Scale")
        self.tabs.addTab(ExtractAudioTab(), "Extract Audio")
        self.tabs.addTab(MergeMediaTab(), "Merge Media")
        self.tabs.addTab(MergeRandomTab(), "Merge Random")
        self.tabs.addTab(TracklistTab(), "Tracklist/Concat")
        self.tabs.addTab(RenameTab(), "Rename")

        # Layout chính
        self.tabs.addTab(UpdateTab(), "Update")
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
