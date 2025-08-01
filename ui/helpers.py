import subprocess
import os
import glob
import random
from pathlib import Path

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
        exe_path = os.path.abspath("../go_modules/mergeMedia/go_mergeMedia")

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
                print("Error: ", result.stderr)
                continue

            # Log thành công
            worker.log.emit(f"✅ Đã xử lý: {Path(file_path).name} ➜ {Path(output_file).name}")
            print("Result: ", result.stdout)

            # Cập nhật tiến độ
            percent = int((idx + 1) / total * 100)
            worker.progress.emit(percent)
        return True
    except Exception as e:
        print('Exception: ', e)
        worker.log.emit(f"Error: {e}")
        return False

def run_go_loop(worker, input_path, output_path, loop_value="1", mode="default"):
    try:
        input_files = glob.glob(os.path.join(input_path, "*"))
        total = len(input_files)

        if total == 0:
            worker.log.emit("⚠ Không tìm thấy file cần loop.")
            return False
        
        exe_path = os.path.abspath("../go_modules/loop/go_loop")

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
                print("Error: ", result.stderr)
                continue  # tiếp tục file khác

            worker.log.emit(f"✅ Đã xử lý: {Path(file_path).as_posix()} ➜ {Path(output_file).as_posix()}")
            print("Result: ", result.stdout)

            percent = int((idx + 1) / total * 100)
            worker.progress.emit(percent)
        return True
    except Exception as e:
        print('Exception: ', e)
        worker.log.emit(f"Error: {e}")
        return False

def run_go_convert(worker, input_path, output_path, input_ext, output_ext):
    try:
        input_files = glob.glob(os.path.join(input_path, f"*{input_ext.lower()}"))
        total = len(input_files)

        if total == 0:
            worker.log.emit("⚠ Không tìm thấy file cần convert.")
            return False

        exe_path = os.path.abspath("../go_modules/convert/go_convert")

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
                print("Error: ", result.stderr)
                continue  # tiếp tục file khác

            worker.log.emit(f"✅ {Path(file_path).as_posix()} ➜ {Path(output_file).as_posix()}")
            print("result: ", result.stdout)

            percent = int((idx + 1) / total * 100)
            worker.progress.emit(percent)
        return True
    except Exception as e:
        print('Exception: ', e)
        worker.log.emit(f"Error: {e}")
        return False
