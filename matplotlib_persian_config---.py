# matplotlib_persian_config.py

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import arabic_reshaper
from bidi import algorithm as bidi
import sys

# تابع کمکی برای پردازش متن فارسی
def process_persian_text_for_matplotlib(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = bidi.get_display(reshaped_text)
    return bidi_text

# --- تنظیمات فونت فارسی برای Matplotlib ---
FONT_NAME = None
persian_fonts_candidates = [
    "Vazirmatn", "IRANSans", "B Nazanin", "Nika", "Arial" 
]

# اگر در حال اجرا با PyInstaller هستیم و فونت ها در _MEIPASS هستند
if hasattr(sys, '_MEIPASS'):
    # فرض می‌کنیم فونت Vazirmatn.ttf در پوشه assets/fonts داخل _MEIPASS قرار دارد
    # یا می توانید مسیر دقیق فونت را اینجا مشخص کنید.
    # مثلاً FONT_PATH = os.path.join(sys._MEIPASS, "assets", "fonts", "Vazirmatn-Regular.ttf")
    # سپس fm.fontManager.addfont(FONT_PATH) را صدا بزنید و FONT_NAME را تنظیم کنید.
    pass # در این پروژه فعلاً فرض بر نصب فونت سیستمی است

for font_candidate in persian_fonts_candidates:
    font_paths = fm.findfont(font_candidate)
    if font_paths:
        if isinstance(font_paths, list):
            if font_paths: 
                FONT_NAME = font_candidate
                print(f"Matplotlib: فونت '{FONT_NAME}' از لیست یافت شد: {font_paths[0]}")
                break
        else:
            FONT_NAME = font_candidate
            print(f"Matplotlib: فونت '{FONT_NAME}' یافت شد: {font_paths}")
            break

if FONT_NAME:
    plt.rcParams['font.family'] = FONT_NAME
    plt.rcParams['font.sans-serif'] = FONT_NAME
    plt.rcParams['axes.unicode_minus'] = False 
    print(f"Matplotlib: فونت '{FONT_NAME}' برای نمایش فارسی تنظیم شد.")
else:
    print("Matplotlib: فونت فارسی مناسب یافت نشد. استفاده از فونت پیش‌فرض Matplotlib.")
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial'] 
    plt.rcParams['axes.unicode_minus'] = False