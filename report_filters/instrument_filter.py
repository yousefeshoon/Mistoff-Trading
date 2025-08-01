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
        self.all_symbols_var = ctk.BooleanVar(value=False) # پیش فرض: هیچکدام انتخاب نشده - تغییر کرد

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


    def reload_symbols(self): # date_range_selection parameter removed
        """
        Reloads symbols based on all available symbols.
        This function is called by the main report window.
        """
        # Clear previous checkboxes, keeping the "همه" checkbox intact
        for widget in self.checkbox_container_frame.winfo_children():
            if widget != self.all_checkbox:
                widget.destroy()
        
        # مهم: قبل از لود کردن نمادهای جدید، وضعیت انتخاب‌های قبلی رو ذخیره کن
        previously_selected = self.get_selection() 
        
        self.symbols = db_manager.get_unique_symbols() # No date range parameters
        self.selected_symbols_vars = {}

        if not self.symbols:
            no_symbols_label = ctk.CTkLabel(self.checkbox_container_frame, text=process_persian_text_for_matplotlib("هیچ نمادی یافت نشد."), font=("Vazirmatn", 10), text_color="gray50")
            no_symbols_label.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
            self.all_checkbox.configure(state="disabled")
            self.all_symbols_var.set(False)
            # If no symbols are found, ensure the selection reflects an empty list
            if self.on_change_callback: # اگر نمادی نیست، خلاصه رو آپدیت کن
                self.on_change_callback()
            return

        self.all_checkbox.configure(state="normal")

        all_selected_after_reload = True
        # Re-create checkboxes for each symbol
        for i, symbol in enumerate(sorted(self.symbols)):
            # Check if this symbol was previously selected, otherwise default to False (not selected)
            # When resetting, previously_selected will be [], so all will be False
            is_checked = (previously_selected == "همه") or (isinstance(previously_selected, list) and symbol in previously_selected)
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
        # If previously_selected was "همه" AND all current symbols are checked, then "همه" should remain checked.
        # Otherwise, if even one symbol is not checked, or if previously_selected was a specific list/empty list,
        # then "همه" should be unchecked.
        if previously_selected == "همه" and all_selected_after_reload:
            self.all_symbols_var.set(True)
        else:
            self.all_symbols_var.set(False)


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
        # This function is used when loading a template or resetting.
        # It must ensure that self.symbols are up-to-date and checkboxes are created before setting.
        # This function is typically called after reload_symbols.
        
        if selected_list == "همه":
            self.all_symbols_var.set(True)
            for var in self.selected_symbols_vars.values():
                var.set(True)
        else:
            # Set 'All' checkbox to False by default when setting a specific list or empty list
            self.all_symbols_var.set(False) 
            for symbol, var in self.selected_symbols_vars.items():
                var.set(symbol in selected_list)
            
            # If all currently available symbols are checked after setting, then 'All' checkbox can be set to True.
            # This handles cases where a subset was saved, but now it represents all available.
            if selected_list and all(var.get() for var in self.selected_symbols_vars.values()):
                self.all_symbols_var.set(True)

        # No need to call on_change_callback here directly, as it will be called by ReportSelectionWindow.