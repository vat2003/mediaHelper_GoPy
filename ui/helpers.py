# ui/helpers.py
import subprocess
import os
def run_go_convert(input_path, output_path):
    try:
        exe_path = os.path.abspath("../go_modules/go_convert")
        result = subprocess.run(
            [exe_path, input_path, output_path],
            capture_output=True, text=True, encoding='utf-8'
        )
        print(result.stdout)
        if result.returncode != 0:
            print("❌ Lỗi:", result.stderr)
        else:
            print("✅ Convert thành công:")
            print(result.stdout)
    except Exception as e:
        print("❌ Exception:", e)
