import os
import subprocess
import sys
import re

# تابع خواندن و افزایش نسخه (کپی شده از build.py)
# این تابع فقط مسئول افزایش نسخه در version_info.py است
def read_and_increment_version():
    """
    نسخه را از version_info.py خوانده، افزایش داده و دوباره در همان فایل ذخیره می‌کند.
    """
    version_file_path = "version_info.py"
    current_version = "v1.00.00" 

    if not os.path.exists(version_file_path):
        with open(version_file_path, "w") as f:
            f.write(f'__version__ = "{current_version}"\n')
    else:
        try:
            with open(version_file_path, "r") as f:
                lines = f.readlines()
            for line in lines:
                if line.startswith('__version__'):
                    match = re.search(r'__version__\s*=\s*["\']v?(\d+\.\d+\.\d+)["\']', line)
                    if match:
                        current_version = "v" + match.group(1) 
                        break
            else: 
                current_version = "v1.00.00"
        except Exception as e:
            print(f"Error reading version_info.py: {e}")
            current_version = "v1.00.00" 

    parts = [int(p) for p in current_version[1:].split(".")]
    
    if len(parts) == 2:
        major, minor = parts
        patch = 0
    elif len(parts) == 3:
        major, minor, patch = parts
    else:
        print(f"Warning: Unexpected version format: {current_version}. Resetting to v1.00.00")
        major, minor, patch = 1, 0, 0
        current_version = "v1.00.00" 

    patch += 1
    if patch >= 100:
        patch = 0
        minor += 1
        if minor >= 100:
            minor = 0
            major += 1

    new_version = f"v{major}.{minor:02d}.{patch:02d}" 

    with open(version_file_path, "w") as f:
        f.write(f'__version__ = "{new_version}"\n')

    print(f"Version incremented to: {new_version}")
    return new_version


if __name__ == "__main__":
    # مرحله 1: افزایش نسخه در version_info.py
    print("--- در حال افزایش شماره نسخه ---")
    new_version = read_and_increment_version()
    print(f"نسخه جدید: {new_version}\n")

    # مرحله 2: اجرای build.py برای بیلد برنامه اصلی
    print("--- در حال اجرای build.py برای برنامه اصلی ---")
    try:
        # subprocess.run را مستقیما به فایل پایتون هدایت می کنیم
        # و از capture_output=True برای دیدن خروجی استفاده می کنیم
        result_main = subprocess.run([sys.executable, "build.py"], capture_output=True, text=True, check=True)
        print("خروجی build.py:")
        print(result_main.stdout)
        if result_main.stderr:
            print("خطاهای build.py:")
            print(result_main.stderr)
        print("--- build.py با موفقیت اجرا شد ---")
    except subprocess.CalledProcessError as e:
        print(f"!!! خطا در اجرای build.py: {e} !!!")
        print("خروجی استاندارد خطا (stderr):")
        print(e.stderr)
        print("خروجی استاندارد (stdout):")
        print(e.stdout)
        sys.exit(1) # در صورت خطا، اسکریپت را متوقف کن

    print("\n")

    # مرحله 3: اجرای build_widget.py برای بیلد ویجت مستقل
    print("--- در حال اجرای build_widget.py برای ویجت مستقل ---")
    try:
        result_widget = subprocess.run([sys.executable, "build_widget.py"], capture_output=True, text=True, check=True)
        print("خروجی build_widget.py:")
        print(result_widget.stdout)
        if result_widget.stderr:
            print("خطاهای build_widget.py:")
            print(result_widget.stderr)
        print("--- build_widget.py با موفقیت اجرا شد ---")
    except subprocess.CalledProcessError as e:
        print(f"!!! خطا در اجرای build_widget.py: {e} !!!")
        print("خروجی استاندارد خطا (stderr):")
        print(e.stderr)
        print("خروجی استاندارد (stdout):")
        print(e.stdout)
        sys.exit(1) # در صورت خطا، اسکریپت را متوقف کن

    print("\n--- All Done...! ---")