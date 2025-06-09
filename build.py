import os
import subprocess
import shutil
import re
import sys

# ایمپورت کردن ماژول version_info
# import version_info # این دیگه نیازی نیست چون مستقیم فایل رو می‌خونیم

# تابع کمکی برای پیدا کردن مسیر فایل‌ها در حالت کامپایل‌شده
def get_resource_path(relative_path):
    """
    مسیر صحیح یک فایل را در محیط توسعه یا پس از کامپایل با PyInstaller برمی‌گرداند.
    """
    if hasattr(sys, '_MEIPASS'): # اگر برنامه با PyInstaller کامپایل شده باشد
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# تابع جدید برای خواندن نسخه بدون افزایش آن
def get_current_version_from_file():
    """
    نسخه فعلی را از version_info.py می‌خواند بدون اینکه آن را افزایش دهد.
    """
    version_file_path = "version_info.py"
    current_version = "v1.00.00" # مقدار پیش‌فرض اولیه با فرمت جدید

    if not os.path.exists(version_file_path):
        return current_version
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
        except Exception as e:
            print(f"Error reading version_info.py: {e}")
            current_version = "v1.00.00"
        return current_version

def build_with_version(version):
    """
    برنامه را با PyInstaller بیلد می‌کند و فایل اجرایی را نامگذاری می‌کند.
    """
    icon_file = "icon.ico"
    main_script = "app.py" # فایل اصلی برنامه که باید بیلد شود

    # اجرای pyinstaller
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        f"--icon={icon_file}",
        f"--add-data={icon_file};.", # icon.ico را در ریشه بسته‌بندی می‌کند
        f"--add-data=trades.db;.", # trades.db را در ریشه بسته‌بندی می‌کند
        f"--add-data=version_info.py;.", # version_info.py را در ریشه بسته‌بندی می‌کند
        f"--add-data=assets;assets",
        main_script
    ]

    print(f"Building {main_script} with version {version}...")
    subprocess.run(pyinstaller_cmd)

    # اطمینان از وجود دایرکتوری dist
    if not os.path.exists("dist"):
        os.makedirs("dist")

    # جابه‌جایی و نامگذاری فایل exe
    original_exe_name = f"dist/{os.path.splitext(main_script)[0]}.exe" # معمولا app.exe
    exe_name = f"dist/MistOff_Trading_{version}.exe"
    
    if os.path.exists(original_exe_name):
        shutil.move(original_exe_name, exe_name)
        print(f"Build complete: {exe_name}")
    else:
        print(f"Error: Could not find {original_exe_name}. PyInstaller might have failed.")
        print("Please check the PyInstaller output above for errors.")

    # تمیزکاری فایل‌های اضافی pyinstaller
    print("Cleaning up PyInstaller temporary files...")
    shutil.rmtree("build", ignore_errors=True)
    spec_file = f"{os.path.splitext(main_script)[0]}.spec" # نام فایل spec بر اساس main_script
    if os.path.exists(spec_file):
        os.remove(spec_file)
    print("Cleanup complete.")

if __name__ == "__main__":
    # در این بخش، build.py به تنهایی فراخوانی نمی‌شود، بلکه توسط build_total.py فراخوانی می‌شود
    # و نسخه به عنوان آرگومان به آن پاس داده می‌شود.
    # پس اینجا فقط برای تست standalone یا حالتی که بدون build_total.py اجرا شود،
    # نسخه را می‌خوانیم. در حالت عادی، build_total.py نسخه را افزایش داده و به اینجا می‌دهد.
    
    # اگر build.py به تنهایی اجرا شود، نسخه را از فایل می‌خواند (بدون افزایش)
    # و با آن بیلد می‌کند.
    current_version_for_standalone = get_current_version_from_file()
    build_with_version(current_version_for_standalone)