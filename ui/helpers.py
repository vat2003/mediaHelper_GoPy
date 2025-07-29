# ui/helpers.py
import subprocess
import os

def run_go_convert(input_path, output_path, input_ext, output_ext):
    try:
        exe_path = os.path.abspath("../go_modules/go_convert")
        
        # Gọi Golang executable và truyền thêm định dạng vào args
        result = subprocess.run(
            [exe_path, input_path, output_path, input_ext, output_ext], capture_output = True, text = True, encoding = 'utf-8'
        )
    
        if result.returncode != 0:
            print("Error: ", result.stderr)
            return False
        else:
            print("Convert Successfully")
            print(result.stdout)
            return True
    except Exception as e:
        print("Exception: ", e)  
        return False