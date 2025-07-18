# report_selection_window.py

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
from PIL import ImageTk, Image 
import hourly_analysis_report

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
    card_height = 320 # ارتفاع ثابت برای هر کارت (حدودی)
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

def show_report_selection_window(parent_root, open_toplevel_windows_list):
    reports_win = tk.Toplevel(parent_root)
    reports_win.title("گزارش جامع")
    reports_win.transient(parent_root)
    reports_win.grab_set()
    reports_win.resizable(False, False)


    # مهم: اضافه کردن reports_win به لیست پنجره‌های باز
    open_toplevel_windows_list.append(reports_win)

    screen_width = reports_win.winfo_screenwidth()
    screen_height = reports_win.winfo_screenheight()

    base_width = 850
    win_height = 720 # <<< ارتفاع پنجره رو افزایش دادیم تا دو ردیف کارت جا بشن

    win_width = int(base_width * 1.20)

    x = (screen_width / 2) - (win_width / 2)
    y = (screen_height / 2) - (win_height / 2)

    reports_win.geometry(f'{win_width}x{win_height}+{int(x)}+{int(y)}')

    main_frame = tk.Frame(reports_win, bg="white", padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)

    #title_label = tk.Label(main_frame, text="انتخاب نوع گزارش", font=("Segoe UI", 18, "bold"), bg="white", fg="#333333")
    #title_label.pack(pady=(0, 20))

    cards_frame = tk.Frame(main_frame, bg="white")
    cards_frame.pack(pady=10) 

    # استفاده از Grid برای چیدمان کارت‌ها در cards_frame
    cards_frame.grid_columnconfigure(0, weight=1) 
    cards_frame.grid_columnconfigure(1, weight=1)
    cards_frame.grid_columnconfigure(2, weight=1)
    cards_frame.grid_rowconfigure(0, weight=1) # <<< اضافه شده: پیکربندی ردیف اول
    cards_frame.grid_rowconfigure(1, weight=1) # <<< اضافه شده: پیکربندی ردیف دوم


    # توابع برای دکمه‌های گزارشات - نام‌گذاری جدید
    def open_weekly_error_analysis_report():
        messagebox.showinfo("بررسی روزهای هفته", "صفحه آنالیز روزهای هفته به زودی اینجا بارگذاری می‌شود!")
        # اینجا بعداً پنجره گزارش روزهای هفته را باز خواهیم کرد
        # from weekly_error_report import show_weekly_error_report_window
        # show_weekly_error_report_window(reports_win)

    def open_hourly_error_analysis_report(): # <<< این تابع تغییر می‌کند
        # حذف پنجره report_selection_window از لیست قبل از فراخوانی
        if reports_win in open_toplevel_windows_list:
            open_toplevel_windows_list.remove(reports_win) # <<< اضافه شده: حذف این پنجره از لیست
        
        # تابع جدید گزارش ساعتی را فراخوانی می‌کنیم و لیست پنجره‌های باز را پاس می‌دهیم
        hourly_analysis_report.show_hourly_analysis_report_window(parent_root, open_toplevel_windows_list) # <<< تغییر
        
        # بعد از برگشت از پنجره گزارش ساعتی، reports_win را دوباره به لیست اضافه می‌کنیم (چون restore شده)
        if reports_win not in open_toplevel_windows_list:
            open_toplevel_windows_list.append(reports_win) # <<< اضافه شده

        # بعد از بسته شدن پنجره hourly_analysis_report، این پنجره (reports_win) را به حالت عادی برگردانیم.
        # این کار توسط تابع restore_other_windows در hourly_analysis_report انجام می‌شود.
        # فقط باید اطمینان حاصل کنیم که این پنجره هم در لیست
        # open_toplevel_windows_list قرار داشته باشد.


    def open_trading_sessions_report():
        messagebox.showinfo("بررسی سشن‌های معاملاتی", "صفحه آنالیز سشن‌های معاملاتی به زودی اینجا بارگذاری می‌شود!")
        # اینجا بعداً پنجره گزارش سشن‌های معاملاتی را باز خواهیم کرد

    # توابع موقتی برای کارت‌های ردیف دوم
    def open_temp_report_4():
        messagebox.showinfo("گزارش موقت 4", "این گزارش در دست توسعه است!")

    def open_temp_report_5():
        messagebox.showinfo("گزارش موقت 5", "این گزارش در دست توسعه است!")

    def open_temp_report_6():
        messagebox.showinfo("گزارش موقت 6", "این گزارش در دست توسعه است!")


    # تعریف کارت‌ها و قرار دادن آنها در grid
    # ردیف اول (row=0)
    # به ترتیب راست به چپ (اولین کارت سمت راست است)
    card1 = create_report_card(
        cards_frame, 
        image_path=get_resource_path("assets/card1.png"), 
        title="بررسی روزهای هفته",
        description="آنالیز تکرار اشتباهات مختلف رو در روزهای هفته بررسی و گزارش بگیرید",
        button_text="برو بریم",
        command=open_weekly_error_analysis_report # <<< نام تابع تغییر کرد
    )
    card1.grid(row=0, column=2, padx=15, pady=10) 

    card2 = create_report_card(
        cards_frame,
        image_path=get_resource_path("assets/card2.png"),
        title="بررسی ساعات پر اشتباه",
        description="ساعات مختلف روز رو بر اساس تکرار اشتباهات مختلف بررسی کنید و بهتر تصمیم بگیرید",
        button_text="برو بریم",
        command=open_hourly_error_analysis_report, # <<< نام تابع تغییر کرد
        #is_coming_soon=True # این رو اگه نیازی به "به زودی" نداشتیم فعال می‌کنیم
    )
    card2.grid(row=0, column=1, padx=15, pady=10) 

    card3 = create_report_card(
        cards_frame,
        image_path=get_resource_path("assets/card3.png"), # اینجا مسیر واقعی عکس را بگذارید
        title="بررسی سشن‌های معاملاتی",
        description="آنالیز اشتباهات رو در سشن‌های مختلف بررسی کنید",
        button_text="برو بریم",
        command=open_trading_sessions_report, # <<< نام تابع تغییر کرد
        #is_coming_soon=True 
    )
    card3.grid(row=0, column=0, padx=15, pady=10) 

    # ردیف دوم (row=1) - کارت‌های موقتی
    card4 = create_report_card(
        cards_frame, 
        image_path=get_resource_path("assets/card4.png"), # مسیر عکس
        title="بررسی حجم معاملات",
        description="اینجا آنالیز تکرار اشتباهات در حجم‌های معاملاتی مختلف رو دارید",
        button_text="برو بریم",
        command=open_temp_report_4,
        #is_coming_soon=True
    )
    card4.grid(row=1, column=2, padx=15, pady=10)

    card5 = create_report_card(
        cards_frame, 
        image_path=get_resource_path("assets/card5.png"), # مسیر عکس
        title="بررسی نمادهای معاملاتی",
        description="تکرار اشتباهات رو در نمادهای مختلف معاملاتی آنالیز کنید",
        button_text="برو بریم",
        command=open_temp_report_5,
        #is_coming_soon=True
    )
    card5.grid(row=1, column=1, padx=15, pady=10)

    card6 = create_report_card(
        cards_frame, 
        image_path=get_resource_path("assets/card6.png"), # مسیر عکس
        title="گزارش کلی",
        description="!کی از یه گزارش جامع و سراسر نکته بدش میاد",
        button_text="برو بریم",
        command=open_temp_report_6,
        #is_coming_soon=True
    )
    card6.grid(row=1, column=0, padx=15, pady=10)

# مهم: وقتی پنجره reports_win بسته می‌شود، آن را از لیست حذف می‌کنیم.
    def on_reports_win_close():
        if reports_win in open_toplevel_windows_list:
            open_toplevel_windows_list.remove(reports_win)
        reports_win.destroy()

    reports_win.protocol("WM_DELETE_WINDOW", on_reports_win_close) # <<< اضافه شده: هندل کردن دکمه بستن

    reports_win.focus_set()
    reports_win.wait_window(reports_win)

# برای تست مستقل
if __name__ == "__main__":
    root_test = tk.Tk()
    root_test.withdraw() 
    show_report_selection_window(root_test)
    root_test.mainloop()