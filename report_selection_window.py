# report_selection_window.py

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
from PIL import ImageTk, Image 

# تابع کمکی برای پیدا کردن مسیر منابع (مثل عکس)
def get_resource_path(relative_path):
    """
    مسیر صحیح یک فایل را در محیط توسعه یا پس از کامپایل با PyInstaller برمی‌گرداند.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def create_report_card(parent_frame, image_path, title, description, button_text, command, is_coming_soon=False):
    """
    یک "کارت" گزارش با تصویر، عنوان، توضیحات و دکمه ایجاد می‌کند.
    """
    card_width = 280 # عرض ثابت برای هر کارت
    card_height = 300 # ارتفاع ثابت برای هر کارت (حدودی)
    card_frame = tk.Frame(parent_frame, bg="white", padx=20, pady=20, 
                          highlightbackground="white", highlightthickness=2,
                          width=card_width, height=card_height, bd=0, relief="flat") 
    card_frame.pack_propagate(False) 

    # بارگذاری تصویر با Pillow و تغییر اندازه به نسبت 16:9
    photo = None
    target_img_width = 240 # عرض هدف برای تصویر (16 * 15)
    target_img_height = 135 # ارتفاع هدف برای تصویر (9 * 15)

    if image_path and os.path.exists(image_path):
        try:
            original_image = Image.open(image_path)
            # تغییر اندازه به ابعاد 16:9
            resized_image = original_image.resize((target_img_width, target_img_height), Image.LANCZOS)
            # <<< تغییر اینجا: استفاده از ImageTk.PhotoImage و bg=card_frame.cget('bg')
            photo = ImageTk.PhotoImage(resized_image)
            
            image_label = tk.Label(card_frame, image=photo, bg=card_frame.cget('bg')) # پس‌زمینه لیبل رو از کارت می‌گیره
            image_label.image = photo # برای جلوگیری از Garbage Collection
            image_label.pack(pady=5, anchor='center') # تصویر رو وسط قرار میده برای زیبایی بیشتر
        except Exception as e: 
            print(f"Error loading or resizing image from {image_path}: {e}")
            image_label = tk.Label(card_frame, text="(تصویر یافت نشد / خطا در بارگذاری)", bg=card_frame.cget('bg'), fg="gray", font=("Segoe UI", 8))
            image_label.pack(pady=5, anchor='center') 
    else:
        image_label = tk.Label(card_frame, text="(تصویر یافت نشد)", bg=card_frame.cget('bg'), fg="gray", font=("Segoe UI", 8))
        image_label.pack(pady=5, anchor='center') 

    # عنوان (راست‌چین)
    title_label = tk.Label(card_frame, text=title, font=("Segoe UI", 12, "bold"), bg="white", fg="#1A73E8", anchor='e', justify='right')
    title_label.pack(pady=(5, 2), fill='x') 

    # توضیحات (راست‌چین)
    desc_label = tk.Label(card_frame, text=description, font=("Segoe UI", 9), bg="white", fg="#5F6368", wraplength=card_width - 40, justify='right') 
    desc_label.pack(pady=(0, 10), fill='x') 

    # دکمه (این بار از tk.Button استفاده می‌کنیم برای کنترل بهتر رنگ)
    action_button = tk.Button(card_frame, text=button_text, command=command,
                              bg="#4285F4", fg="white", 
                              font=("Segoe UI", 10, "bold"),
                              borderwidth=0, relief="flat", 
                              padx=10, pady=5, 
                              activebackground="#3367D6", 
                              activeforeground="white", 
                              cursor="hand2") 
    
    def on_enter(e):
        action_button.config(bg="#3367D6") 
    def on_leave(e):
        action_button.config(bg="#4285F4") 
    
    action_button.bind("<Enter>", on_enter)
    action_button.bind("<Leave>", on_leave)

    action_button.pack(pady=(0, 5), anchor='e') 

    # اضافه کردن حالت "به زودی"
    if is_coming_soon:
        overlay_label = tk.Label(card_frame, text="به زودی!", font=("Segoe UI", 16, "bold"), fg="gray", bg="white",
                                 compound="center", relief="solid", borderwidth=1)
        overlay_label.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.8) 
        
        action_button.config(bg="#E0E0E0", fg="gray", activebackground="#D0D0D0", activeforeground="gray")
        action_button.unbind("<Enter>") 
        action_button.unbind("<Leave>") 
        action_button.config(command=lambda: messagebox.showinfo("در دست ساخت", f"گزارش '{title}' در دست توسعه است. از صبر و همراهی شما سپاسگزاریم!"))

    return card_frame

def show_report_selection_window(parent_root):
    reports_win = tk.Toplevel(parent_root)
    reports_win.title("انتخاب گزارش‌ها")
    reports_win.transient(parent_root)
    reports_win.grab_set()
    reports_win.resizable(False, False)

    screen_width = reports_win.winfo_screenwidth()
    screen_height = reports_win.winfo_screenheight()

    base_width = 800
    win_height = 500

    win_width = int(base_width * 1.20)

    x = (screen_width / 2) - (win_width / 2)
    y = (screen_height / 2) - (win_height / 2)

    reports_win.geometry(f'{win_width}x{win_height}+{int(x)}+{int(y)}')

    main_frame = tk.Frame(reports_win, bg="white", padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)

    title_label = tk.Label(main_frame, text="انتخاب نوع گزارش", font=("Segoe UI", 18, "bold"), bg="white", fg="#333333")
    title_label.pack(pady=(0, 20))

    cards_frame = tk.Frame(main_frame, bg="white")
    cards_frame.pack(pady=10) 

    cards_frame.grid_columnconfigure(0, weight=1) 
    cards_frame.grid_columnconfigure(1, weight=1)
    cards_frame.grid_columnconfigure(2, weight=1)

    def open_comprehensive_report():
        messagebox.showinfo("گزارش جامع", "صفحه گزارش جامع تریدها به زودی اینجا بارگذاری می‌شود!")

    def open_error_analysis_report():
        messagebox.showinfo("تحلیل خطاها", "صفحه تحلیل خطاها و درس‌های آموخته به زودی اینجا بارگذاری می‌شود!")

    def open_performance_stats_report():
        messagebox.showinfo("آمار عملکرد", "صفحه گزارش آماری عملکرد به زودی اینجا بارگذاری می‌شود!")

    # تعریف کارت‌ها و قرار دادن آنها در grid
    # به ترتیب راست به چپ (اولین کارت سمت راست است)
    # ایندکس‌های ستون را برعکس می‌دهیم تا از راست به چپ چیده شوند
    card1 = create_report_card(
        cards_frame, 
        image_path=get_resource_path("assets/card1.png"), 
        title="بررسی روزهای هفته",
        description="اینجا میتونید آنالیز تکرار اشتباهات مختلف رو در روزهای هفته بررسی و گزارش بگیرید",
        button_text="بزن بریم",
        command=open_comprehensive_report
    )
    card1.grid(row=0, column=2, padx=15, pady=10) 

    card2 = create_report_card(
        cards_frame,
        image_path="", # اینجا مسیر واقعی عکس را بگذارید
        title="تحلیل خطاها",
        description="بررسی جامع خطاهای تریدینگ، شامل فراوانی، روندها و الگوهای اشتباهات شما.",
        button_text="بزن بریم",
        command=open_error_analysis_report,
        is_coming_soon=True 
    )
    card2.grid(row=0, column=1, padx=15, pady=10) 

    card3 = create_report_card(
        cards_frame,
        image_path="", # اینجا مسیر واقعی عکس را بگذارید
        title="آمار عملکرد",
        description="گزارش‌های آماری از سوددهی، وین ریت، میزان ریسک و سایر شاخص‌های عملکرد.",
        button_text="بزن بریم",
        command=open_performance_stats_report,
        is_coming_soon=True 
    )
    card3.grid(row=0, column=0, padx=15, pady=10) 

    reports_win.focus_set()
    reports_win.wait_window(reports_win)

# برای تست مستقل
if __name__ == "__main__":
    root_test = tk.Tk()
    root_test.withdraw() 
    show_report_selection_window(root_test)
    root_test.mainloop()