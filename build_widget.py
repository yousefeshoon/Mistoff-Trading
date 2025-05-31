import os
import subprocess
import shutil
import re # این رو اضافه کن
import sys # این رو اضافه کن

# تابع کمکی برای پیدا کردن مسیر فایل‌ها (از build.py کپی شده)
def get_resource_path(relative_path):
    """
    مسیر صحیح یک فایل را در محیط توسعه یا پس از کامپایل با PyInstaller برمی‌گرداند.
    """
    if hasattr(sys, '_MEIPASS'): # اگر برنامه با PyInstaller کامپایل شده باشد
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# تابع خواندن نسخه (از build.py کپی شده)
def get_current_version_from_file():
    """
    نسخه فعلی را از version_info.py می‌خواند.
    """
    version_file_path = "version_info.py"
    current_version = "v1.00.00" # پیش‌فرض

    if not os.path.exists(version_file_path):
        # اگر فایل وجود ندارد، با نسخه پیش‌فرض برگرد
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
            print(f"Error reading version_info.py for widget build: {e}")
            # در صورت خطا، با نسخه پیش‌فرض ادامه می‌دهد
        return current_version


# مسیر فایل اصلی ویجت
WIDGET_SCRIPT = "error_widget.py"
WIDGET_ICON = "icon.ico" # از همان آیکون اصلی استفاده می‌کنیم

def build_widget():
    """
    ویجت error_widget.py را به صورت یک فایل اجرایی مستقل (exe) بیلد می‌کند.
    """
    # نسخه فعلی را می‌خوانیم (بدون افزایش دادن، چون build.py این کار را می‌کند)
    current_version = get_current_version_from_file()

    print(f"Building {WIDGET_SCRIPT} as standalone widget (Version: {current_version})...")

    # نام فایل اجرایی خروجی - اینجا تغییر اعمال می‌شود!
    widget_exe_name = f"dist/Trade_Journal_Error_Widget_{current_version}.exe" # نام جدید با اضافه شدن ورژن

    # دستور PyInstaller برای بیلد یک فایل مستقل، بدون پنجره کنسول و با آیکون
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",       # فقط یک فایل اجرایی
        "--noconsole",     # پنجره کنسول سیاه رنگ را نشان نده
        f"--icon={WIDGET_ICON}", # آیکون ویجت
        f"--add-data={WIDGET_ICON};.", # آیکون را در پکیج بسته‌بندی کند
        f"--add-data=trades.db;.",     # دیتابیس را در پکیج بسته‌بندی کند
        f"--add-data=db_manager.py;.", # db_manager.py را هم بسته‌بندی کند (هرچند ایمپورت می‌شود)
        f"--add-data=version_info.py;.", # version_info.py را هم بسته‌بندی کند
        WIDGET_SCRIPT      # فایل اصلی که باید بیلد شود
    ]

    # اجرای PyInstaller
    subprocess.run(pyinstaller_cmd)

    # جابه‌جایی و نامگذاری فایل exe
    original_exe_path = f"dist/{os.path.splitext(WIDGET_SCRIPT)[0]}.exe" # معمولا error_widget.exe
    
    if os.path.exists(original_exe_path):
        # اگر دایرکتوری dist وجود نداشت، ایجادش کن
        if not os.path.exists("dist"):
            os.makedirs("dist")
        shutil.move(original_exe_path, widget_exe_name)
        print(f"Widget build complete: {widget_exe_name}")
    else:
        print(f"Error: Could not find {original_exe_path}. PyInstaller might have failed.")
        print("Please check the PyInstaller output above for errors.")

    # تمیزکاری فایل‌های اضافی pyinstaller
    print("Cleaning up PyInstaller temporary files...")
    shutil.rmtree("build", ignore_errors=True)
    spec_file = f"{os.path.splitext(WIDGET_SCRIPT)[0]}.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)
    print("Cleanup complete.")

if __name__ == "__main__":
    build_widget()