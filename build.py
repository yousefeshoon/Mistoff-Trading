import os
import subprocess
import shutil
import re
import sys

# ایمپورت کردن ماژول version_info
import version_info

# تابع کمکی برای پیدا کردن مسیر فایل‌ها در حالت کامپایل‌شده
# این تابع رو هم میتونیم اینجا اضافه کنیم اگرچه توی db_manager و app.py هم داریم
# میتونه مفید باشه اگر build.py بخواد به resource_path دسترسی پیدا کنه.
def get_resource_path(relative_path):
    """
    مسیر صحیح یک فایل را در محیط توسعه یا پس از کامپایل با PyInstaller برمی‌گرداند.
    """
    if hasattr(sys, '_MEIPASS'): # اگر برنامه با PyInstaller کامپایل شده باشد
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# ایمپورت کردن ماژول version_info
# چون این تابع فایل رو مستقیم میخونه، ایمپورت مستقیم version_info شاید لازم نباشه،
# اما نگه میداریم برای خوانایی یا اگر در آینده لازم شد.
# import version_info 

def read_and_increment_version():
    """
    نسخه را از version_info.py خوانده، افزایش داده و دوباره در همان فایل ذخیره می‌کند.
    """
    version_file_path = "version_info.py"
    current_version = "v1.00.00" # مقدار پیش‌فرض اولیه با فرمت جدید

    if not os.path.exists(version_file_path):
        with open(version_file_path, "w") as f:
            f.write(f'__version__ = "{current_version}"\n')
    else:
        try:
            with open(version_file_path, "r") as f:
                lines = f.readlines()
            for line in lines:
                if line.startswith('__version__'):
                    # از regex برای استخراج نسخه استفاده می‌کنیم
                    match = re.search(r'__version__\s*=\s*["\']v?(\d+\.\d+\.\d+)["\']', line)
                    if match:
                        current_version = "v" + match.group(1) # مطمئن می‌شیم v هم اولش هست
                        break
            else: # اگر خط __version__ پیدا نشد یا فرمت اشتباه بود
                current_version = "v1.00.00"
        except Exception as e:
            print(f"Error reading version_info.py: {e}")
            current_version = "v1.00.00" # پیش‌فرض در صورت خطا


    # حالا نسخه را به سه بخش اصلی، فرعی و پچ تقسیم می‌کنیم
    # current_version[1:] بخش "v" را حذف می‌کند.
    parts = [int(p) for p in current_version[1:].split(".")]
    
    # فرض می‌کنیم فرمت همیشه MAJOR.MINOR.PATCH هست، حتی اگر دو بخش بود (0 به عنوان PATCH در نظر گرفته میشه)
    if len(parts) == 2:
        major, minor = parts
        patch = 0
    elif len(parts) == 3:
        major, minor, patch = parts
    else:
        print(f"Warning: Unexpected version format: {current_version}. Resetting to v1.00.00")
        major, minor, patch = 1, 0, 0
        current_version = "v1.00.00" # ریسیت کردن به نسخه پیش‌فرض


    # منطق افزایش نسخه
    # می‌خواهیم PATCH را افزایش دهیم. اگر PATCH به 100 رسید، MINOR افزایش یابد و PATCH صفر شود.
    # اگر MINOR به 100 رسید، MAJOR افزایش یابد و MINOR و PATCH صفر شوند.
    patch += 1
    if patch >= 100:
        patch = 0
        minor += 1
        if minor >= 100:
            minor = 0
            major += 1

    new_version = f"v{major}.{minor:02d}.{patch:02d}" # فرمت خروجی با دو رقم برای minor و patch

    # نسخه جدید را در version_info.py ذخیره می‌کنیم
    with open(version_file_path, "w") as f:
        f.write(f'__version__ = "{new_version}"\n')

    print(f"Version incremented to: {new_version}")
    return new_version

def build_with_version(version):
    """
    برنامه را با PyInstaller بیلد می‌کند و فایل اجرایی را نامگذاری می‌کند.
    """
    icon_file = "icon.ico"
    main_script = "app.py" # فایل اصلی برنامه که باید بیلد شود

    # اجرای pyinstaller
    # برای ویندوز، --add-data فرمت "src;dest" دارد.
    # src: مسیر فایل یا فولدر در سیستم شما.
    # dest: مسیری که این فایل در پوشه موقت pyinstaller (sys._MEIPASS) قرار می‌گیرد.
    # ما می‌خواهیم که در ریشه همان پوشه موقت قرار بگیرند.

    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        f"--icon={icon_file}",
        f"--add-data={icon_file};.", # icon.ico را در ریشه بسته‌بندی می‌کند
        f"--add-data=trades.db;.", # trades.db را در ریشه بسته‌بندی می‌کند
        f"--add-data=version_info.py;.", # version_info.py را در ریشه بسته‌بندی می‌کند
        main_script
    ]

    print(f"Building {main_script} with version {version}...")
    subprocess.run(pyinstaller_cmd)

    # اطمینان از وجود دایرکتوری dist
    if not os.path.exists("dist"):
        os.makedirs("dist")

    # جابه‌جایی و نامگذاری فایل exe
    original_exe_name = f"dist/{os.path.splitext(main_script)[0]}.exe" # معمولا app.exe
    exe_name = f"dist/Trade_Journal_{version}.exe"
    
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
    new_version = read_and_increment_version() # ابتدا نسخه را آپدیت می‌کنیم
    build_with_version(new_version) # سپس با نسخه جدید بیلد می‌گیریم