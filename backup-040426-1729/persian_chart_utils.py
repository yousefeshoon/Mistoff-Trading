# persian_chart_utils.py

# import matplotlib.pyplot as plt # COMMENTED OUT - Remove Matplotlib import
# import matplotlib.font_manager as fm # COMMENTED OUT
import arabic_reshaper
from bidi import algorithm as bidi
import sys
import os
import tkinter as tk

# تابع برای پردازش متن فارسی
def process_persian_text_for_matplotlib(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = bidi.get_display(reshaped_text)
    return bidi_text

# تابع برای تنظیم متن Titlebar
def set_titlebar_text(window_obj, text):
    if not text:
        window_obj.title("")
        return

    processed_text = process_persian_text_for_matplotlib(text)
    window_obj.title(processed_text)

# --- تنظیمات فونت فارسی برای Matplotlib ---
# COMMENTED OUT THE ENTIRE MATPLOTLIB FONT CONFIGURATION BLOCK
# Since Matplotlib is completely disabled, this block is no longer needed
# and will prevent any RecursionError originating from Matplotlib's font system.
# FONT_NAME = None
# persian_fonts_candidates = [
#     "Vazirmatn", "IRANSans", "B Nazanin", "Nika", "Arial"
# ]

# _bundled_font_path = None
# if hasattr(sys, '_MEIPASS'):
#     _bundled_font_path = os.path.join(sys._MEIPASS, "assets", "fonts", "Vazirmatn-Regular.ttf")
#     if os.path.exists(_bundled_font_path):
#         try:
#             prop = fm.FontProperties(fname=_bundled_font_path)
#             fm.fontManager.addfont(filename=_bundled_font_path)
#             FONT_NAME = prop.get_name()
#             print(f"Matplotlib: فونت '{FONT_NAME}' از مسیر باندل شده یافت و اضافه شد: {_bundled_font_path}")
#         except Exception as e:
#             print(f"Matplotlib: خطا در اضافه کردن فونت باندل شده '{_bundled_font_path}': {e}")
#             FONT_NAME = None

# if not FONT_NAME:
#     for font_candidate in persian_fonts_candidates:
#         try:
#             font_prop = fm.FontProperties(family=font_candidate)
#             if fm.findfont(font_prop, fallback_to_default=False):
#                 FONT_NAME = font_candidate
#                 print(f"Matplotlib: فونت '{FONT_NAME}' از لیست فونت‌های سیستمی یافت شد.")
#                 break
#         except Exception as e:
#             print(f"Matplotlib: تلاش برای یافتن فونت '{font_candidate}' با خطا مواجه شد: {e}")
#             continue

# if FONT_NAME:
#     plt.rcParams['font.family'] = FONT_NAME
#     plt.rcParams['font.sans-serif'] = FONT_NAME
#     plt.rcParams['axes.unicode_minus'] = False
#     print(f"Matplotlib: فونت '{FONT_NAME}' برای نمایش فارسی تنظیم شد.")
# else:
#     print("Matplotlib: فونت فارسی مناسب یافت نشد. استفاده از فونت پیش‌فرض Matplotlib.")
#     plt.rcParams['font.family'] = 'sans-serif'
#     plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
#     plt.rcParams['axes.unicode_minus'] = False

# اطمینان از نصب arabic_reshaper و python-bidi
try:
    import arabic_reshaper
except ImportError:
    print("Warning: arabic_reshaper not found. Persian text rendering might be incorrect.")
    print("Please install it: pip install arabic-reshaper")
try:
    from bidi import algorithm as bidi
except ImportError:
    print("Warning: python-bidi not found. Persian text rendering might be incorrect.")
    print("Please install it: pip install python-bidi")