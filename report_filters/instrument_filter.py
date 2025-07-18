# report_filters/instrument_filter.py

import customtkinter as ctk
import db_manager
import tkinter as tk
from persian_chart_utils import process_persian_text_for_matplotlib


class InstrumentFilterFrame(ctk.CTkFrame):
    def __init__(self, master, on_change_callback=None, fg_color="transparent", **kwargs):
        super().__init__(master, fg_color=fg_color, **kwargs)
        self.on_change_callback = on_change_callback
        self.symbols = []
        self.selected_symbols_vars = {}
        self.all_symbols_var = ctk.BooleanVar(value=False) # پیش فرض: هیچکدام انتخاب نشده

        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=process_persian_text_for_matplotlib("انتخاب نماد (نمادهای موجود در بازه زمانی انتخابی):"), font=("Vazirmatn", 12))
        self.label.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.checkbox_container_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.checkbox_container_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.checkbox_container_frame.grid_columnconfigure(0, weight=1)

        self.all_checkbox = ctk.CTkCheckBox(self.checkbox_container_frame,
                                            text=process_persian_text_for_matplotlib("همه نمادها"),
                                            variable=self.all_symbols_var,
                                            command=self._toggle_all_symbols,
                                            font=("Vazirmatn", 11, "bold"),
                                            fg_color=("blue", "blue"),
                                            checkbox_width=18, checkbox_height=18,
                                            border_color=("gray60", "gray40"),
                                            checkmark_color="white")
        self.all_checkbox.grid(row=0, column=0, sticky="e", padx=10, pady=5)


    def reload_symbols(self, date_range_selection):
        """
        Reloads symbols based on the provided date range.
        This function is called by the main report window when date filter changes.
        """
        start_date = date_range_selection["start_date"]
        end_date = date_range_selection["end_date"]

        # Clear previous checkboxes, keeping the "همه" checkbox intact
        for widget in self.checkbox_container_frame.winfo_children():
            if widget != self.all_checkbox:
                widget.destroy()
        
        # مهم: قبل از لود کردن نمادهای جدید، وضعیت انتخاب‌های قبلی رو ذخیره کن
        previously_selected = self.get_selection() 
        if previously_selected == "همه":
            previously_selected = list(self.selected_symbols_vars.keys()) # Convert "همه" to actual list of currently displayed symbols

        self.symbols = db_manager.get_unique_symbols(start_date=start_date, end_date=end_date)
        self.selected_symbols_vars = {}

        if not self.symbols:
            no_symbols_label = ctk.CTkLabel(self.checkbox_container_frame, text=process_persian_text_for_matplotlib("هیچ نمادی در بازه انتخابی یافت نشد."), font=("Vazirmatn", 10), text_color="gray50")
            no_symbols_label.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
            self.all_checkbox.configure(state="disabled")
            self.all_symbols_var.set(False)
            if self.on_change_callback: # اگر نمادی نیست، خلاصه رو آپدیت کن
                self.on_change_callback()
            return

        self.all_checkbox.configure(state="normal") # در صورت وجود نماد، چک‌باکس "همه" باید فعال باشه

        all_selected_after_reload = True # فرض کن همه انتخاب شدن، بعد اگر یکی نبود، false کن
        # Re-create checkboxes for each symbol
        for i, symbol in enumerate(sorted(self.symbols)):
            # اگر قبلا انتخاب شده بود، دوباره تیک بزن
            is_checked = (symbol in previously_selected) if isinstance(previously_selected, list) else False
            var = ctk.BooleanVar(value=is_checked) 
            self.selected_symbols_vars[symbol] = var
            checkbox = ctk.CTkCheckBox(self.checkbox_container_frame,
                                       text=process_persian_text_for_matplotlib(symbol),
                                       variable=var,
                                       command=lambda s=symbol: self._on_symbol_checkbox_change(s),
                                       font=("Vazirmatn", 11),
                                       checkbox_width=18, checkbox_height=18,
                                       border_color=("gray60", "gray40"),
                                       checkmark_color="white")
            checkbox.grid(row=i + 1, column=0, sticky="e", padx=10, pady=2)
            
            if not is_checked:
                all_selected_after_reload = False

        # "همه" باید بر اساس وضعیت واقعی چک‌باکس‌های تکی تنظیم بشه
        self.all_symbols_var.set(all_selected_after_reload)

        # Trigger summary update if callback exists
        # این فراخوانی توسط ReportSelectionWindow در _on_filter_changed مدیریت میشه

    def _toggle_all_symbols(self):
        is_all_selected = self.all_symbols_var.get()
        for symbol, var in self.selected_symbols_vars.items():
            var.set(is_all_selected)
        if self.on_change_callback:
            self.on_change_callback()

    def _on_symbol_checkbox_change(self, symbol):
        if not self.selected_symbols_vars[symbol].get():
            self.all_symbols_var.set(False)
        elif all(var.get() for var in self.selected_symbols_vars.values()):
            self.all_symbols_var.set(True)
        
        if self.on_change_callback:
            self.on_change_callback()

    def get_selection(self):
        if self.all_symbols_var.get():
            return "همه"
        else:
            selected = [s for s, var in self.selected_symbols_vars.items() if var.get()]
            return selected if selected else [] # اگر هیچکدام انتخاب نشده، لیست خالی برگردون

    def set_selection(self, selected_list):
        # این تابع هنگام بارگذاری قالب یا ریست کردن استفاده میشه
        # بنابراین باید چک‌باکس‌ها رو به درستی تنظیم کنه
        # ابتدا مطمئن شو که self.symbols بروز و چک‌باکس‌ها ساخته شده‌اند
        # این تابع به طور معمول بعد از reload_symbols صدا زده میشه
        
        if selected_list == "همه":
            self.all_symbols_var.set(True)
            for var in self.selected_symbols_vars.values():
                var.set(True)
        else:
            self.all_symbols_var.set(False) # چون 'همه' نیست
            for symbol, var in self.selected_symbols_vars.items():
                var.set(symbol in selected_list)
            
            # اگر selected_list خالی باشه، all_symbols_var باید False باشه
            if not selected_list:
                self.all_symbols_var.set(False)
            
            # اگر همه نمادهای موجود در selected_symbols_vars تیک خورده باشند، all_symbols_var را True کن
            if all(var.get() for var in self.selected_symbols_vars.values()) and self.selected_symbols_vars:
                self.all_symbols_var.set(True)

        # No need to call on_change_callback here directly.