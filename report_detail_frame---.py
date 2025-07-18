# report_detail_frame.py

import customtkinter as ctk
import tkinter as tk
# import matplotlib.pyplot as plt  # COMMENTED OUT - Remove Matplotlib import
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg # COMMENTED OUT
from concurrent.futures import ThreadPoolExecutor
import time
from persian_chart_utils import process_persian_text_for_matplotlib
import db_manager
# import matplotlib.font_manager as fm # COMMENTED OUT

# یک Executor برای اجرای کارهای سنگین در پس‌زمینه
executor = ThreadPoolExecutor(max_workers=1)

class ReportDetailFrame(ctk.CTkFrame):
    def __init__(self, master, fg_color="transparent", **kwargs):
        super().__init__(master, fg_color=fg_color, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.loading_label = ctk.CTkLabel(self, text=process_persian_text_for_matplotlib("در حال تهیه گزارش..."),
                                          font=("Vazirmatn", 16, "bold"), text_color="gray50")

        # Comment out all Matplotlib related widget creation
        # self.chart_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=8)
        # self.fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        # self.fig.patch.set_facecolor('white')
        # self.ax.set_facecolor('white')
        # self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        # self.canvas_widget = self.canvas.get_tk_widget()
        # self.canvas_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Placeholder label when Matplotlib is disabled
        self.placeholder_label = ctk.CTkLabel(self, text=process_persian_text_for_matplotlib("نمودارها اینجا نمایش داده می‌شوند (فعلا غیرفعال برای رفع مشکل)."),
                                             font=("Vazirmatn", 14), text_color="gray", wraplength=400, justify="right")
        self.placeholder_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _display_loading(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.loading_label.grid(row=0, column=0, sticky="nsew")

    def _hide_loading(self):
        self.loading_label.grid_forget()

    def update_report(self, filters):
        self._display_loading()
        future = executor.submit(self._generate_report_data, filters)
        future.add_done_callback(lambda f: self.master.after(0, self._show_report_results, f.result()))

    def _generate_report_data(self, filters):
        print(f"Generating report with filters: {filters}")
        time.sleep(2) 

        start_date = filters.get("date_range", {}).get("start_date", "N/A")
        end_date = filters.get("date_range", {}).get("end_date", "N/A")
        symbols = filters.get("instruments", "همه")
        
        return {
            "filters_used": filters,
            "summary_text": f"گزارش برای بازه: {process_persian_text_for_matplotlib(start_date)} تا {process_persian_text_for_matplotlib(end_date)}. نمادها: {process_persian_text_for_matplotlib(str(symbols))}"
        }

    def _show_report_results(self, report_data):
        self._hide_loading()
        
        for widget in self.winfo_children():
            widget.destroy()

        # Display placeholder instead of chart_frame
        self.placeholder_label.configure(text=process_persian_text_for_matplotlib(f"گزارش با فیلترهای شما آماده است.\n\n{report_data['summary_text']}\n\nنمودارها اینجا نمایش داده می‌شوند (فعلا غیرفعال برای رفع مشکل)."))
        self.placeholder_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Comment out Matplotlib chart update
        # self.ax.clear()
        # self.ax.plot(report_data['chart_data']['x'], report_data['chart_data']['y'], marker='o')
        # self.ax.set_title(process_persian_text_for_matplotlib('نمودار عملکرد ماهانه'), fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))
        # self.ax.set_xlabel(process_persian_text_for_matplotlib('ماه'), fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))
        # self.ax.set_ylabel(process_persian_text_for_matplotlib('سود/ضرر'), fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))
        # self.ax.grid(True, linestyle='--', alpha=0.6)
        # self.canvas.draw()