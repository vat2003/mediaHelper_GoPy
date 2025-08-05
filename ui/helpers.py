import subprocess
import os
import glob
import random
import sys
from pathlib import Path

def get_duration_ffmpeg(file_path):
    try:
        project_dir = os.getcwd()
        ffprobe_path = os.path.join(project_dir, "assets", "ffmpeg", "ffprobe.exe")
        result = subprocess.run(
            [
                ffprobe_path, '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        return 0.0

def resource_path(relative_path):
    """Lấy đường dẫn tới file khi chạy .exe"""
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass is not None:
        return os.path.join(meipass, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def seconds_to_hhmmss(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02}:{m:02}:{s:02}"

def run_go_videoScale(
    worker,
    input_path,
    output_path,
    resolution="1920x1080",
    video_bitrate="4000k",
    audio_bitrate="192k",
    fps="30",
    preset="fast",
    mode="gpu",
    ext=".mp4"
):
    try:
        # Lọc các file video đầu vào
        video_exts = ('*.mp4', '*.mov', '*.avi', '*.mkv')
        input_files = [f for ext in video_exts for f in glob.glob(os.path.join(input_path, ext))]

        total = len(input_files)
        if total == 0:
            worker.log.emit("⚠ Không tìm thấy file video cần scale.")
            return False

        # Đường dẫn đến binary Go
        project_dir = os.getcwd()
        exe_path = os.path.join(project_dir, "bin", "go_videoScale.exe")

        for idx, file_path in enumerate(input_files):
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng scale theo yêu cầu.")
                return False

            # Tên file đầu ra
            filename = Path(file_path).stem
            output_file = os.path.join(output_path, f"{filename}_scaled{ext}")

            # Log đang xử lý
            worker.log.emit(f"📼 Scaling: {Path(file_path).name}")

            # Gọi file thực thi go_videoScale với các tham số
            cmd = [
                exe_path,
                file_path,
                output_file,
                resolution,
                mode,
                video_bitrate,
                fps,
                audio_bitrate,
                preset
            ]

            # Gọi subprocess
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode != 0:
                worker.log.emit(f"❌ Lỗi scale: {Path(file_path).name}")
                worker.log.emit(f"📄 STDOUT:\n{result.stdout}")
                worker.log.emit(f"🐛 STDERR:\n{result.stderr}")
                continue

            worker.log.emit(f"✅ Đã scale: {Path(file_path).name} ➜ {Path(output_file).name}")

            # Cập nhật tiến độ
            percent = int((idx + 1) / total * 100)
            worker.progress.emit(percent)

        return True

    except Exception as e:
        worker.log.emit(f"❌ Exception: {e}")
        return False

def run_go_tracklist(input_text, output_tracklist_path="tracklist.txt"):
    paths = [line.strip().strip('"') for line in input_text.strip().splitlines() if line.strip()]
    current_time = 0.0
    lines = []

    for path in paths:
        filename = os.path.splitext(os.path.basename(path))[0]
        line = f"{seconds_to_hhmmss(current_time)} {filename}"
        lines.append(line)
        current_time += get_duration_ffmpeg(path)

    with open(output_tracklist_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return '\n'.join(lines)

def run_go_extract_audio(worker, input_folder, output_folder, output_ext=".mp3"):
    try:
        worker.log.emit("🔄 Bắt đầu trích xuất audio...")
        input_exts = ('.mp4', '.mkv', '.avi', '.mov', '.flv')
        input_files = [f for f in glob.glob(os.path.join(input_folder, "*")) if f.lower().endswith(input_exts)]
        total = len(input_files)

        if total == 0:
            worker.log.emit("⚠ Không tìm thấy file video nào để trích xuất audio.")
            return False
    
        project_dir = os.getcwd()
        exe_path = os.path.join(project_dir, "bin", "go_extractAudio.exe")

        for idx, file_path in enumerate(input_files):
            if worker.is_stopped():
                worker.log.emit("🛑 Đã dừng extract audio theo yêu cầu.")
                return False
            filename = Path(file_path).stem
            output_file = os.path.join(output_folder, f"{filename}{output_ext}")

            worker.log.emit(f"🎧 Đang xử lý: {Path(file_path).name}")

            cmd = [exe_path, file_path, output_file]

            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode != 0:
                if "Stream specifier 'a'" in result.stderr or "Stream map 'a'" in result.stderr:
                    worker.log.emit(f"⚠ Không có audio: {Path(file_path).name} → Bỏ qua.")
                else:
                    worker.log.emit(f"❌ Lỗi extract: {Path(file_path).name}")
                    worker.log.emit(f"📄 STDOUT:\n{result.stdout}")
                    worker.log.emit(f"🐛 STDERR:\n{result.stderr}")
                continue

            worker.log.emit(f"✅ Extract thành công: {Path(output_file).name}")

            percent = int((idx + 1) / total * 100)
            worker.progress.emit(percent)
        worker.log.emit("🎉 Hoàn tất extract audio.")
        return True
    except Exception as e:
        worker.log.emit(f"Error: {e}")
        return False

def run_go_random_merge(worker, input_path, output_path, files_per_group="0", num_outputs="1"):
    try:
        # Lấy danh sách file đầu vào để đếm số lượng
        video_exts = ('*.mp4', '*.avi', '*.mkv', '*.mov', '*.flv')
        audio_exts = ('*.mp3', '*.wav', '*.aac')
        media_exts = video_exts + audio_exts

        input_files = [f for ext in media_exts for f in glob.glob(os.path.join(input_path, ext))]
        total = int(num_outputs)

        if len(input_files) < int(files_per_group):
            worker.log.emit("⚠ Không đủ file để ghép.")
            return False

        # Đường dẫn đến file Go đã biên dịch hoặc file .go
        project_dir = os.getcwd()
        exe_path = os.path.join(project_dir, "bin", "go_randomMerge.exe")

        for i in range(total):
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng merge ngẫu nhiên theo yêu cầu.")
                return False

            worker.log.emit(f"🚀 Ghép ngẫu nhiên nhóm {i+1}/{total}...")
            
            # Gọi lệnh: go run randomMerge.go <input_path> <output_path> <files_per_group> <num_outputs>
            cmd = [
                "go", "run", exe_path,
                input_path,
                output_path,
                str(files_per_group),
                "1"  # chỉ sinh ra 1 output mỗi vòng để xử lý tuần tự và cập nhật tiến độ
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode != 0:
                worker.log.emit(f"❌ Lỗi randomMerge nhóm {i+1}:")
                worker.log.emit(f"📄 STDOUT:\n{result.stdout}")
                worker.log.emit(f"🐛 STDERR:\n{result.stderr}")
                continue

            worker.log.emit(f"✅ Đã ghép nhóm {i+1}/{total}")

            percent = int((i + 1) / total * 100)
            worker.progress.emit(percent)

        return True

    except Exception as e:
        worker.log.emit(f"Error: {e}")
        return False

def run_go_merge(worker, input_video_image, input_audio, output_path, resolution="1080", mode="gpu", duration="0", bitrate="2000k", fps="0", ext=".mp4"):
    try:
        # Lấy tất cả file video/image đầu vào
        video_image_exts = ('*.mp4', '*.mov', '*.avi', '*.mkv', '*.jpg', '*.jpeg', '*.png', '*.bmp', '*.webp')
        audio_exts = ('*.mp3', '*.wav', '*.aac', '*.flac', '*.ogg', '*.m4a')

        input_files = [f for ext in video_image_exts for f in glob.glob(os.path.join(input_video_image, ext))]
        audio_files = [f for ext in audio_exts for f in glob.glob(os.path.join(input_audio, ext))]

        total = len(input_files)

        if total == 0:
            worker.log.emit("⚠ Không tìm thấy file video/image cần merge.")
            return False
        
        if len(audio_files) == 0:
            worker.log.emit("⚠ Không tìm thấy file audio.")
            return False
        
        # Đường dẫn tới file thư thi go_mergeMedia
        project_dir = os.getcwd()
        exe_path = os.path.join(project_dir, "bin", "go_mergeMedia.exe")

        for idx, file_path in enumerate(input_files):
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng merge theo yêu cầu.")
                return False
            
            # Chọn 1 file audio ngẫu nhiên
            selected_audio = random.choice(audio_files)

            # Tên file đầu ra
            filename = Path(file_path).stem
            output_file = os.path.join(output_path, f"{filename}_merged{ext}")

            # Tạo lệnh gọi file thư thi Go
            cmd = [
                exe_path,
                file_path,
                selected_audio,
                output_file,
                resolution,
                mode,
                duration,
                bitrate,
                fps
            ]

            # Log thông tin xử lý
            worker.log.emit(f"🔧 Merging {Path(file_path).name} + {Path(selected_audio).name}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode != 0:
                worker.log.emit(f"❌ Lỗi Merge: {Path(file_path).as_posix()}")
                worker.log.emit(f"📄 STDOUT:\n{result.stdout}")
                worker.log.emit(f"🐛 STDERR:\n{result.stderr}")
                continue

            # Log thành công
            worker.log.emit(f"✅ Đã xử lý: {Path(file_path).name} ➜ {Path(output_file).name}")

            # Cập nhật tiến độ
            percent = int((idx + 1) / total * 100)
            worker.progress.emit(percent)
        return True
    except Exception as e:
        worker.log.emit(f"Error: {e}")
        return False

def run_go_loop(worker, input_path, output_path, loop_value="1", mode="default"):
    try:
        input_files = glob.glob(os.path.join(input_path, "*"))
        total = len(input_files)

        if total == 0:
            worker.log.emit("⚠ Không tìm thấy file cần loop.")
            return False
        
        project_dir = os.getcwd()
        exe_path = os.path.join(project_dir, "bin", "go_loop.exe")

        for idx, file_path in enumerate(input_files):
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng loop theo yêu cầu.")
                return False
            
            filename = Path(file_path).stem
            ext = Path(file_path).suffix
            output_file = os.path.join(output_path, f"{filename}_looped{ext}")

            cmd = [exe_path, file_path, output_file, loop_value, mode]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode != 0:
                worker.log.emit(f"❌ Lỗi Loop: {Path(file_path).as_posix()}")
                worker.log.emit(f"📄 STDOUT:\n{result.stdout}")
                worker.log.emit(f"🐛 STDERR:\n{result.stderr}")
                continue  # tiếp tục file khác

            worker.log.emit(f"✅ Đã xử lý: {Path(file_path).as_posix()} ➜ {Path(output_file).as_posix()}")
            

            percent = int((idx + 1) / total * 100)
            worker.progress.emit(percent)
        return True
    except Exception as e:
        worker.log.emit(f"Error: {e}")
        return False

def run_go_convert(worker, input_path, output_path, input_ext, output_ext):
    try:
        input_files = glob.glob(os.path.join(input_path, f"*{input_ext.lower()}"))
        total = len(input_files)

        if total == 0:
            worker.log.emit("⚠ Không tìm thấy file cần convert.")
            return False

        project_dir = os.getcwd()
        exe_path = os.path.join(project_dir, "bin", "go_convert.exe")

        for idx, file_path in enumerate(input_files):
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng convert theo yêu cầu.")
                return False

            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_file = os.path.join(output_path, base_name + output_ext)

            cmd = [exe_path, file_path, output_file]

            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode != 0:
                worker.log.emit(f"❌ Lỗi convert: {Path(file_path).as_posix()}")
                worker.log.emit(f"📄 STDOUT:\n{result.stdout}")
                worker.log.emit(f"🐛 STDERR:\n{result.stderr}")
                continue  # tiếp tục file khác

            worker.log.emit(f"✅ {Path(file_path).as_posix()} ➜ {Path(output_file).as_posix()}")

            percent = int((idx + 1) / total * 100)
            worker.progress.emit(percent)
        return True
    except Exception as e:
        worker.log.emit(f"Error: {e}")
        return False
