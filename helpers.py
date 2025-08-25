import subprocess
import os
import glob
import random
import sys
from pathlib import Path

from process_utils import spawn_process
import os
import sys
import subprocess

def get_app_base_dir():
    if getattr(sys, 'frozen', False):  
        # App đang chạy ở dạng .exe build từ PyInstaller
        return os.path.dirname(sys.executable)
    else:
        # Chạy ở dạng source .py
        return os.path.dirname(os.path.abspath(__file__))

def get_duration_ffmpeg(file_path):
    try:
        base_dir = get_app_base_dir()

        # Nếu có _internal thì lấy assets trong đó
        if "_internal" in os.listdir(base_dir):
            asset_dir = os.path.join(base_dir, "_internal", "assets")
        else:
            asset_dir = os.path.join(base_dir, "assets")

        ffprobe_path = os.path.join(asset_dir, "ffmpeg", "ffprobe.exe")

        result = subprocess.run(
            [
                ffprobe_path, '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return float(result.stdout.strip())
    except Exception as e:
        return 0.0

def get_go_file_path(file_name):
    try:
        base_dir = get_app_base_dir()
        # Nếu có _internal thì lấy assets trong đó
        if "_internal" in os.listdir(base_dir):
            bin_dir = os.path.join(base_dir, "_internal", "bin")
        else:
            bin_dir = os.path.join(base_dir, "bin")
        return os.path.join(bin_dir, file_name)
    except Exception as e:
        return ""

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

def run_go_rename(worker, input_path, start_number=1, padding=3, ext="", prefix="", suffix="", remove_chars=""):
    try:
        # Lấy tất cả file trong thư mục input_path với đuôi mở rộng đã cho
        if ext:
            input_files = glob.glob(os.path.join(input_path, f"*{ext.lower()}"))
        else:
            input_files = [f for f in glob.glob(os.path.join(input_path, "*")) if os.path.isfile(f)]

        total = len(input_files)
        if total == 0:
            worker.log.emit("⚠ Không tìm thấy file để đổi tên.")
            return False

        exe_path = get_go_file_path("go_rename.exe")
        if not os.path.exists(exe_path):
            worker.log.emit(f"❌ Không tìm thấy executable: {exe_path}")
            return False

        for idx, file_path in enumerate(input_files):
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng đổi tên theo yêu cầu.")
                return False

            filename = Path(file_path).stem

            # Tạo prefix/suffix từ pattern (nếu dùng {num}, {name})
            seq = str(start_number + idx).zfill(padding)
            dynamic_prefix = prefix.replace("{num}", seq).replace("{name}", filename)
            dynamic_suffix = suffix.replace("{num}", seq).replace("{name}", filename)

            # Lệnh gọi go_rename
            cmd = [exe_path, file_path, dynamic_prefix, dynamic_suffix, remove_chars]

            # Spawn + stream (stderr gộp vào stdout); cho phép Stop dừng ngay
            p = spawn_process(worker, cmd)
            stdout_lines = []

            if p.stdout:
                for raw in p.stdout:
                    if worker.is_stopped():
                        # cố gắng thoát êm; BaseWorker.stop() vẫn terminate/kill cả cây
                        try:
                            if p.stdin and not p.stdin.closed:
                                p.stdin.write("q\n"); p.stdin.flush()
                        except Exception:
                            pass
                        break
                    line = (raw or "").rstrip()
                    if line:
                        stdout_lines.append(line)
                        worker.log.emit(line)

            rc = p.wait() if not worker.is_stopped() else p.poll()
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng đổi tên theo yêu cầu.")
                return False

            if rc != 0:
                worker.log.emit(f"❌ Lỗi đổi tên: {Path(file_path).name}")
                if stdout_lines:
                    worker.log.emit("📄 STDOUT:\n" + "\n".join(stdout_lines))
                # STDERR đã gộp vào STDOUT trong spawn_process
                continue

            # Lấy tên mới từ stdout (Go in ra newName ở dòng cuối)
            new_name = stdout_lines[-1] if stdout_lines else "(không rõ)"
            worker.log.emit(f"✅ Đã đổi tên: {Path(file_path).name} ➜ {new_name}")

            # Cập nhật tiến độ
            worker.progress.emit(int((idx + 1) / total * 100))

        return True

    except Exception as e:
        worker.log.emit(f"❌ Exception: {e}")
        return False


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
        video_exts = ('*.mp4', '*.mov', '*.avi', '*.mkv', '*.flv')
        input_files = [f for ext in video_exts for f in glob.glob(os.path.join(input_path, ext))]

        total = len(input_files)
        if total == 0:
            worker.log.emit("⚠ Không tìm thấy file video cần scale.")
            return False

        os.makedirs(output_path, exist_ok=True)

        exe_path = get_go_file_path("go_videoScale.exe")
        if not os.path.exists(exe_path):
            worker.log.emit(f"❌ Không tìm thấy executable: {exe_path}")
            return False

        for idx, file_path in enumerate(input_files):
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng scale theo yêu cầu.")
                return False

            # Tên file đầu ra
            filename = Path(file_path).stem
            output_file = os.path.join(output_path, f"{filename}_scaled{ext}")

            # Log đang xử lý
            worker.log.emit(f"📼 Scaling: {Path(file_path).name}")

            # Lệnh gọi go_videoScale
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

            # Spawn + stream để có thể stop ngay
            p = spawn_process(worker, cmd)
            buf_out = []

            if p.stdout:
                for raw in p.stdout:
                    if worker.is_stopped():
                        # cố gắng thoát êm; BaseWorker.stop() sẽ terminate/kill cả cây
                        try:
                            if p.stdin and not p.stdin.closed:
                                p.stdin.write("q\n"); p.stdin.flush()
                        except Exception:
                            pass
                        break
                    line = (raw or "").rstrip()
                    if line:
                        buf_out.append(line)
                        worker.log.emit(line)

            rc = p.wait() if not worker.is_stopped() else p.poll()

            if worker.is_stopped():
                worker.log.emit("🛑 Dừng scale theo yêu cầu.")
                return False

            if rc != 0:
                worker.log.emit(f"❌ Lỗi scale: {Path(file_path).name}")
                if buf_out:
                    worker.log.emit("📄 STDOUT:\n" + "\n".join(buf_out))
                # STDERR đã được gộp vào STDOUT trong spawn_process
                continue

            worker.log.emit(f"✅ Đã scale: {Path(file_path).name} ➜ {Path(output_file).name}")

            # Cập nhật tiến độ
            worker.progress.emit(int((idx + 1) / total * 100))

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

        os.makedirs(output_folder, exist_ok=True)

        input_exts = ('.mp4', '.mkv', '.avi', '.mov', '.flv')
        input_files = [f for f in glob.glob(os.path.join(input_folder, "*"))
                       if os.path.isfile(f) and f.lower().endswith(input_exts)]
        total = len(input_files)

        if total == 0:
            worker.log.emit("⚠ Không tìm thấy file video nào để trích xuất audio.")
            return False

        exe_path = get_go_file_path("go_extractAudio.exe")
        if not os.path.exists(exe_path):
            worker.log.emit(f"❌ Không tìm thấy executable: {exe_path}")
            return False

        for idx, file_path in enumerate(input_files):
            if worker.is_stopped():
                worker.log.emit("🛑 Đã dừng extract audio theo yêu cầu.")
                return False

            filename = Path(file_path).stem
            output_file = os.path.join(output_folder, f"{filename}{output_ext}")

            worker.log.emit(f"🎧 Đang xử lý: {Path(file_path).name}")

            cmd = [exe_path, file_path, output_file]

            # Spawn + stream (stderr gộp vào stdout), đã đăng ký để BaseWorker.stop() kill ngay
            p = spawn_process(worker, cmd)
            buf_out = []

            if p.stdout:
                for raw in p.stdout:
                    if worker.is_stopped():
                        # cố gắng thoát êm (nếu tool hỗ trợ), BaseWorker.stop() vẫn terminate/kill cả cây
                        try:
                            if p.stdin and not p.stdin.closed:
                                p.stdin.write("q\n"); p.stdin.flush()
                        except Exception:
                            pass
                        break
                    line = (raw or "").rstrip()
                    if line:
                        buf_out.append(line)
                        worker.log.emit(line)

            rc = p.wait() if not worker.is_stopped() else p.poll()

            if worker.is_stopped():
                worker.log.emit("🛑 Đã dừng extract audio theo yêu cầu.")
                return False

            if rc != 0:
                combined = "\n".join(buf_out)
                if ("Stream specifier 'a'" in combined) or ("Stream map 'a'" in combined):
                    worker.log.emit(f"⚠ Không có audio: {Path(file_path).name} → Bỏ qua.")
                else:
                    worker.log.emit(f"❌ Lỗi extract: {Path(file_path).name}")
                    if combined.strip():
                        worker.log.emit("📄 STDOUT:\n" + combined)
                    # STDERR đã gộp vào STDOUT để an toàn
                continue

            worker.log.emit(f"✅ Extract thành công: {Path(output_file).name}")
            worker.progress.emit(int((idx + 1) / total * 100))

        worker.log.emit("🎉 Hoàn tất extract audio.")
        return True

    except Exception as e:
        worker.log.emit(f"Error: {e}")
        return False

    
def run_go_random_merge(worker, input_path, output_path, files_per_group="0", num_outputs="1"):
    try:
        files_per_group = int(files_per_group)
        num_outputs_int = int(num_outputs)

        # gom media vào list
        video_exts = ('*.mp4', '*.avi', '*.mkv', '*.mov', '*.flv')
        audio_exts = ('*.mp3', '*.wav', '*.aac')
        media_exts = video_exts + audio_exts

        input_files = [f for ext in media_exts for f in glob.glob(os.path.join(input_path, ext))]
        worker.log.emit(f"📂 Tìm thấy {len(input_files)} file media hợp lệ.")

        if files_per_group != 0 and len(input_files) < files_per_group:
            worker.log.emit("⚠ Không đủ file để ghép.")
            return False

        os.makedirs(output_path, exist_ok=True)

        exe_path = get_go_file_path("go_randomMerge.exe")
        if not os.path.exists(exe_path):
            worker.log.emit(f"❌ Không tìm thấy executable: {exe_path}")
            return False

        for i in range(num_outputs_int):
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng merge ngẫu nhiên theo yêu cầu.")
                return False

            worker.log.emit(f"🚀 Ghép ngẫu nhiên nhóm {i+1}/{num_outputs_int}...")

            cmd = [exe_path, input_path, output_path, str(files_per_group)]
            worker.log.emit(f"🔧 Lệnh: {' '.join(cmd)}")

            # --- spawn + stream (stderr gộp vào stdout để tránh deadlock)
            p = spawn_process(worker, cmd)
            buf_out = []

            if p.stdout:
                for raw in p.stdout:
                    if worker.is_stopped():
                        # cố gắng thoát êm; BaseWorker.stop() sẽ terminate/kill cả cây
                        try:
                            if p.stdin and not p.stdin.closed:
                                p.stdin.write("q\n"); p.stdin.flush()
                        except Exception:
                            pass
                        break
                    line = (raw or "").rstrip()
                    if line:
                        buf_out.append(line)
                        worker.log.emit(line)

            rc = p.wait() if not worker.is_stopped() else p.poll()
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng merge ngẫu nhiên theo yêu cầu.")
                return False

            if rc != 0:
                worker.log.emit(f"❌ Lỗi randomMerge nhóm {i+1}:")
                if buf_out:
                    worker.log.emit("📄 STDOUT:\n" + "\n".join(buf_out))
                # STDERR đã gộp vào STDOUT để an toàn
                continue

            worker.log.emit(f"✅ Đã ghép nhóm {i+1}/{num_outputs_int}")
            worker.progress.emit(int((i + 1) / num_outputs_int * 100))

        return True

    except Exception as e:
        worker.log.emit(f"Error: {e}")
        return False


def run_go_merge(worker, input_video_image, input_audio, output_path,
                 resolution="1080", mode="gpu", duration="0",
                 bitrate="2000k", fps="0", ext=".mp4"):
    try:
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

        exe_path = get_go_file_path("go_mergeMedia.exe")

        for idx, file_path in enumerate(input_files):
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng merge theo yêu cầu.")
                return False

            selected_audio = random.choice(audio_files)
            filename = Path(file_path).stem
            output_file = os.path.join(output_path, f"{filename}_merged{ext}")

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

            worker.log.emit(f"🔧 Merging {Path(file_path).name} + {Path(selected_audio).name}")

            # --- spawn + stream (stderr gộp vào stdout để tránh deadlock)
            p = spawn_process(worker, cmd)  # đã đăng ký để BaseWorker.stop() có thể kill ngay
            buf_out = []

            if p.stdout:
                for raw in p.stdout:
                    if worker.is_stopped():
                        # cố gắng thoát êm; BaseWorker.stop() sẽ terminate/kill cả cây
                        try:
                            if p.stdin and not p.stdin.closed:
                                p.stdin.write("q\n"); p.stdin.flush()
                        except Exception:
                            pass
                        break
                    line = (raw or "").rstrip()
                    if line:
                        buf_out.append(line)
                        worker.log.emit(line)

            rc = p.wait() if not worker.is_stopped() else p.poll()

            if worker.is_stopped():
                worker.log.emit("🛑 Dừng merge theo yêu cầu.")
                return False

            if rc != 0:
                worker.log.emit(f"❌ Lỗi Merge: {Path(file_path).as_posix()}")
                if buf_out:
                    worker.log.emit("📄 STDOUT:\n" + "\n".join(buf_out))
                # stderr đã gộp vào stdout; giữ log “STDERR” để không lệch cấu trúc thông báo
                worker.log.emit("🐛 STDERR:\n")
                continue

            worker.log.emit(f"✅ Đã xử lý: {Path(file_path).name} ➜ {Path(output_file).name}")
            worker.progress.emit(int((idx + 1) / total * 100))

        return True

    except Exception as e:
        worker.log.emit(f"Error: {e}")
        return False


MEDIA_EXTS = {'.mp4', '.mkv', '.mov', '.avi', '.flv', '.mp3', '.wav', '.aac'}

def run_go_loop(worker, input_path, output_path, loop_value="1", mode="default"):
    try:
        p = Path(input_path)
        if p.is_file():
            input_files = [str(p)]
        elif p.is_dir():
            input_files = [str(x) for x in sorted(p.iterdir()) if x.is_file() and x.suffix.lower() in MEDIA_EXTS]
        else:
            worker.log.emit(f"❌ Input không tồn tại: {input_path}")
            return False

        total = len(input_files)
        if total == 0:
            worker.log.emit("⚠ Không tìm thấy file media trong thư mục.")
            return False

        os.makedirs(output_path, exist_ok=True)

        exe_path = get_go_file_path("go_loop.exe")
        if not os.path.exists(exe_path):
            worker.log.emit(f"❌ Không tìm thấy executable: {exe_path}")
            return False

        for idx, file_path in enumerate(input_files):
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng loop theo yêu cầu.")
                return False

            pfile = Path(file_path)
            if not pfile.is_file():
                worker.log.emit(f"⚠ Bỏ qua (không phải file): {file_path}")
                continue

            ext = pfile.suffix or ".mp4"
            output_file = os.path.join(output_path, f"{pfile.stem}_looped{ext}")
            worker.log.emit(f"🔄 Đang xử lý: {pfile.name}")

            cmd = [exe_path, str(file_path), str(output_file), str(loop_value), str(mode)]

            # --- Parse dòng log ngay trong stream_process
            has_error = False
            def handle_line(line: str):
                nonlocal has_error
                line = (line or "").rstrip()
                if not line: 
                    return
                if line.startswith("ERROR:"):
                    has_error = True
                    worker.log.emit(f"❌ Lỗi Loop: {pfile.name}")
                    worker.log.emit(f"🐛 GO Output: {line}")
                elif line.startswith("WARN:"):
                    worker.log.emit(f"⚠ {line[5:].strip()}")
                elif line.startswith("INFO:"):
                    worker.log.emit(line[5:].strip())
                else:
                    worker.log.emit(line)

            # spawn + stream
            proc = spawn_process(worker, cmd)
            # tùy bạn: nếu stream_process hỗ trợ handler, dùng bản có handler; 
            # còn nếu không, lặp thủ công giống sau:
            if proc.stdout:
                for raw in proc.stdout:
                    if worker.is_stopped():
                        # cố gắng thoát êm, BaseWorker.stop() cũng sẽ kill cứng
                        try:
                            if proc.stdin and not proc.stdin.closed:
                                proc.stdin.write("q\n"); proc.stdin.flush()
                        except Exception:
                            pass
                        break
                    handle_line(raw)
            rc = proc.wait() if not worker.is_stopped() else proc.poll()

            if worker.is_stopped():
                worker.log.emit("🛑 Dừng tiến trình hiện tại.")
                return False

            # Kiểm tra kết quả
            if rc != 0:
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    worker.log.emit(f"⚠ Tiến trình trả mã {rc} nhưng file đã tạo: {output_file}")
                else:
                    worker.log.emit(f"❌ Thất bại (rc={rc}). Bỏ qua: {file_path}")
                    continue

            if has_error:
                # đã thấy ERROR trong log → coi là fail của file này
                continue

            worker.log.emit(f"✅ Đã xử lý: {pfile.as_posix()} ➜ {Path(output_file).as_posix()}")
            worker.progress.emit(int((idx + 1) / total * 100))

        return True

    except Exception as e:
        worker.log.emit(f"Error: {e}")
        return False

def run_go_convert(worker, input_path, output_path, input_ext, output_ext):
    try:
        # Chuẩn hoá ext: đảm bảo có dấu chấm
        if input_ext and not input_ext.startswith("."):
            input_ext = "." + input_ext
        if output_ext and not output_ext.startswith("."):
            output_ext = "." + output_ext

        os.makedirs(output_path, exist_ok=True)

        # Lấy danh sách file cần convert (case-insensitive)
        all_entries = [os.path.join(input_path, name) for name in os.listdir(input_path)]
        input_files = [f for f in all_entries
                       if os.path.isfile(f) and f.lower().endswith((input_ext or "").lower())]

        total = len(input_files)
        if total == 0:
            worker.log.emit("⚠ Không tìm thấy file cần convert.")
            return False

        exe_path = get_go_file_path("go_convert.exe")
        if not os.path.exists(exe_path):
            worker.log.emit(f"❌ Không tìm thấy executable: {exe_path}")
            return False

        for idx, file_path in enumerate(input_files):
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng convert theo yêu cầu.")
                return False

            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_file = os.path.join(output_path, base_name + (output_ext or ""))

            cmd = [exe_path, file_path, output_file]
            worker.log.emit(f"🔧 Converting: {Path(file_path).name} → {Path(output_file).name}")

            # Spawn + stream (dừng ngay khi Stop)
            p = spawn_process(worker, cmd)
            if p.stdout:
                for raw in p.stdout:
                    if worker.is_stopped():
                        # cố gắng thoát êm; BaseWorker.stop() cũng sẽ terminate/kill cả cây
                        try:
                            if p.stdin and not p.stdin.closed:
                                p.stdin.write("q\n"); p.stdin.flush()
                        except Exception:
                            pass
                        break
                    line = (raw or "").rstrip()
                    if line:
                        worker.log.emit(line)

            rc = p.wait() if not worker.is_stopped() else p.poll()
            if worker.is_stopped():
                worker.log.emit("🛑 Đã dừng convert theo yêu cầu.")
                return False

            if rc != 0:
                # Nếu binary Go in log sang stdout, ta đã thấy ở trên
                worker.log.emit(f"❌ Lỗi convert: {Path(file_path).as_posix()} (rc={rc})")
                # tiếp tục file khác
                continue

            # Thành công
            worker.log.emit(f"✅ {Path(file_path).as_posix()} ➜ {Path(output_file).as_posix()}")
            worker.progress.emit(int((idx + 1) / total * 100))

        return True

    except Exception as e:
        worker.log.emit(f"❌ Exception: {e}")
        return False

