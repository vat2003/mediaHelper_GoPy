import subprocess
import os
import glob
from pathlib import Path

def run_go_convert(worker, input_path, output_path, input_ext, output_ext):
    
    try:
        
        input_folder = glob.glob(os.path.join(input_path, f"*{input_ext.lower()}"))
        total = len(input_folder)

        if total == 0:
            worker.log.emit("⚠ Không tìm thấy file cần convert.")
            return False

        exe_path = os.path.abspath("../go_modules/go_convert")  # hoặc full path chuẩn

        for idx, file_path in enumerate(input_folder):
            if worker.is_stopped():
                worker.log.emit("🛑 Dừng convert theo yêu cầu.")
                return False

            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_folder = (os.path.join(output_path, base_name + output_ext))

            cmd = [exe_path, input_path, output_path, input_ext, output_ext]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

            if result.returncode != 0:
                worker.log.emit(f"❌ Lỗi convert: {Path(file_path).as_posix()}")
            else:
                worker.log.emit(f"✅ {Path(file_path).as_posix()} ➜ {Path(output_folder).as_posix()}")

            percent = int((idx + 1) / total * 100)
            worker.progress.emit(percent)

        return True
    except Exception as e:
        print('Exception: ', e)
        worker.log.emit(f"Error: {e}")
        return False